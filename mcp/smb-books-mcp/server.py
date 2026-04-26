"""MCP → HTTP клиент к сервису smb-books (POST /v1/list, GET /v1/book)."""

from __future__ import annotations

import os
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

DEFAULT_BASE = "http://10.0.0.107:3011"
MAX_BOOK_CHARS = 400_000

_base = os.environ.get("SMB_BOOKS_BASE_URL", DEFAULT_BASE).rstrip("/")
mcp = FastMCP("smb-books-mcp")


def _client(timeout: float = 120.0) -> httpx.Client:
    return httpx.Client(base_url=_base, timeout=timeout)


@mcp.tool()
def smb_books_health() -> dict[str, Any]:
    """Проверка smb-books: GET /health."""
    with _client() as c:
        r = c.get("/health")
        r.raise_for_status()
        return r.json()


@mcp.tool()
def smb_books_list(path: str = "") -> dict[str, Any]:
    """Список внутри библиотеки книг (POST /v1/list)."""
    with _client() as c:
        r = c.post("/v1/list", json={"path": path})
        r.raise_for_status()
        return r.json()


@mcp.tool()
def smb_books_read(path: str) -> dict[str, Any]:
    """Текст книги .fb2 / .fb2.zip относительно корня библиотеки (GET /v1/book)."""
    with _client() as c:
        r = c.get("/v1/book", params={"path": path})
        r.raise_for_status()
        text = r.text
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
