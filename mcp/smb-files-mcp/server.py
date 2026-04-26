"""MCP → HTTP клиент к сервису smb-files (POST /v1/list, /v1/file)."""

from __future__ import annotations

import base64
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

DEFAULT_BASE = "http://10.0.0.107:3010"
MAX_READ_BYTES = 2_000_000

_base = os.environ.get("SMB_FILES_BASE_URL", DEFAULT_BASE).rstrip("/")
mcp = FastMCP("smb-files-mcp")


def _client(timeout: float = 120.0) -> httpx.Client:
    return httpx.Client(base_url=_base, timeout=timeout)


@mcp.tool()
def smb_files_health() -> dict[str, Any]:
    """Проверка smb-files: GET /health."""
    with _client() as c:
        r = c.get("/health")
        r.raise_for_status()
        return r.json()


@mcp.tool()
def smb_files_list(path: str = "") -> dict[str, Any]:
    """Содержимое каталога на шаре относительно SMB_ROOT (POST /v1/list)."""
    with _client() as c:
        r = c.post("/v1/list", json={"path": path})
        r.raise_for_status()
        return r.json()


@mcp.tool()
def smb_files_read(path: str) -> dict[str, Any]:
    """
    Прочитать файл относительно SMB_ROOT. Ответ: base64, имя, путь.
    Объём ограничен (см. MAX_READ_BYTES), иначе сообщение об ошибке.
    """
    with _client() as c:
        r = c.post("/v1/file", json={"path": path})
        r.raise_for_status()
        data = r.content
        if len(data) > MAX_READ_BYTES:
            return {
                "error": f"file too large for MCP ({len(data)} bytes > {MAX_READ_BYTES}); use smb-files API or smaller file",
                "size": len(data),
            }
        name = ""
        cd = r.headers.get("content-disposition", "")
        if "filename*=" in cd:
            pass
        xp = r.headers.get("x-resolved-path", "")
        return {
            "path_header": xp,
            "size": len(data),
            "content_base64": base64.standard_b64encode(data).decode("ascii"),
        }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
