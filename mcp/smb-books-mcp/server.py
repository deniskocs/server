"""MCP по stdio: список и текст книг (FB2) с SMB — логика как smb-books HTTP, без HTTP."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from fb2_plain import bytes_to_plain_text
from library_paths import strip_library_prefix
from settings import load_smb_config
from smb_fs import ensure_smb, list_directory, read_file

MAX_BOOK_CHARS = 400_000
mcp = FastMCP("smb-books-mcp")


def _version() -> str:
    v = Path(__file__).resolve().parent / "VERSION"
    if v.is_file():
        return v.read_text(encoding="utf-8").strip()
    return "0.0.0-dev"


def _smb_error(exc: BaseException) -> dict[str, Any]:
    msg = str(exc)
    if "Failed to connect" in msg or "Connection refused" in msg:
        return {"error": "smb_unreachable", "detail": msg}
    return {"error": type(exc).__name__, "detail": msg}


@mcp.tool()
def smb_books_health() -> dict[str, Any]:
    """Проверка: конфиг и сессия к SMB."""
    try:
        cfg = load_smb_config()
        ensure_smb(cfg)
        return {"status": "ok", "version": _version()}
    except FileNotFoundError as e:
        return {"status": "error", "detail": str(e)}
    except ValueError as e:
        return {"status": "error", "detail": str(e)}
    except Exception as e:
        return {"status": "error", **_smb_error(e)}


@mcp.tool()
def smb_books_list(path: str = "") -> dict[str, Any]:
    """Список внутри библиотеки (path относительно root из конфига); в ответе path — короткий."""
    try:
        cfg = load_smb_config()
        rel, raw = list_directory(cfg, path)
    except ValueError as e:
        return _smb_error(e)
    except OSError as e:
        return {"error": "not_found", "detail": str(e)}
    except Exception as e:
        return _smb_error(e)
    path_short = strip_library_prefix(rel.replace("\\", "/"), cfg.root)
    items = [{"name": n, "type": t} for n, t in raw]
    return {"path": path_short, "items": items}


@mcp.tool()
def smb_books_read(path: str) -> dict[str, Any]:
    """Текст книги .fb2 / .fb2.zip относительно корня библиотеки (как GET /v1/book)."""
    try:
        cfg = load_smb_config()
        _, data = read_file(cfg, path)
    except ValueError as e:
        return _smb_error(e)
    except OSError as e:
        return {"error": "not_found", "detail": str(e)}
    except MemoryError:
        return {"error": "file_too_large", "detail": "file too large to read into memory"}
    except Exception as e:
        return _smb_error(e)
    try:
        text = bytes_to_plain_text(data, path)
    except RuntimeError as e:
        return {"error": "fb2_parse", "detail": str(e)}
    if len(text) > MAX_BOOK_CHARS:
        return {
            "truncated": True,
            "chars": len(text),
            "preview": text[:MAX_BOOK_CHARS],
        }
    return {"truncated": False, "text": text}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
