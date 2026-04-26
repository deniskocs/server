"""MCP по stdio: список и чтение файлов на SMB (логика как у smb-files HTTP-сервиса, без HTTP)."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

from settings import load_smb_config
from smb_fs import ensure_smb, list_directory, read_file

MAX_READ_BYTES = 2_000_000
mcp = FastMCP("smb-files-mcp")


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
def smb_files_health() -> dict[str, Any]:
    """Проверка: конфиг читается, к SMB-хосту удаётся открыть сессию."""
    try:
        cfg = load_smb_config()
        ensure_smb(cfg)
        return {"status": "ok", "version": _version()}
    except FileNotFoundError as e:
        return {"status": "error", "detail": str(e)}
    except Exception as e:
        return {"status": "error", **_smb_error(e)}


@mcp.tool()
def smb_files_list(path: str = "") -> dict[str, Any]:
    """Содержимое каталога на шаре относительно root из конфига (как POST /v1/list)."""
    try:
        cfg = load_smb_config()
        rel, raw = list_directory(cfg, path)
    except ValueError as e:
        return _smb_error(e)
    except OSError as e:
        return {"error": "not_found", "detail": str(e)}
    except Exception as e:
        return _smb_error(e)
    items = [{"name": n, "type": t} for n, t in raw]
    return {"path": rel.replace("\\", "/"), "items": items}


@mcp.tool()
def smb_files_read(path: str) -> dict[str, Any]:
    """
    Прочитать файл относительно root из конфига. Ответ: base64, размер, путь (как /v1/file).
    Объём ограничен MAX_READ_BYTES.
    """
    try:
        cfg = load_smb_config()
        rel, data = read_file(cfg, path)
    except ValueError as e:
        return _smb_error(e)
    except OSError as e:
        return {"error": "not_found", "detail": str(e)}
    except MemoryError:
        return {"error": "file_too_large", "detail": "file too large to read into memory"}
    except Exception as e:
        return {
            "error": "smb_read_failed",
            "detail": f"{type(e).__name__}: {e}",
        }
    if len(data) > MAX_READ_BYTES:
        return {
            "error": f"file too large for MCP ({len(data)} bytes > {MAX_READ_BYTES})",
            "size": len(data),
        }
    rel_url = rel.replace("\\", "/")
    path_header = quote(rel_url, safe="/")
    return {
        "path_header": path_header,
        "size": len(data),
        "content_base64": base64.standard_b64encode(data).decode("ascii"),
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
