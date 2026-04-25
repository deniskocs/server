"""Read/write `*.env` under CONFIGS_DIR (or local dev folder)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Callable

_ENV_NAME_RE = re.compile(r"^[\w.-]+\.env$")


def get_configs_path() -> Path:
    raw = os.environ.get("CONFIGS_DIR", "").strip()
    if raw:
        return Path(os.path.expanduser(raw)).resolve()
    return (Path.cwd() / "local-llm-configs").resolve()


def ensure_dir() -> None:
    get_configs_path().mkdir(parents=True, exist_ok=True)


def validate_env_filename(name: str) -> str:
    n = (name or "").strip()
    if not n:
        raise ValueError("File name is required")
    if ".." in n or "/" in n or "\\" in n:
        raise ValueError("Invalid file name")
    if not _ENV_NAME_RE.match(n):
        raise ValueError("Use a name like my-model.env (letters, digits, ._-)")
    return n


def list_env_filenames() -> list[str]:
    ensure_dir()
    p = get_configs_path()
    return sorted(f.name for f in p.iterdir() if f.is_file() and f.suffix == ".env")


def read_env_text(name: str) -> str:
    n = validate_env_filename(name)
    path = get_configs_path() / n
    if not path.is_file():
        raise FileNotFoundError(n)
    return path.read_text(encoding="utf-8")


def write_env_text(name: str, text: str) -> None:
    ensure_dir()
    n = validate_env_filename(name)
    (get_configs_path() / n).write_text(text, encoding="utf-8")


def delete_env_file(name: str) -> bool:
    try:
        n = validate_env_filename(name)
    except ValueError:
        return False
    path = get_configs_path() / n
    if not path.is_file():
        return False
    path.unlink()
    return True


def file_exists(name: str) -> bool:
    try:
        n = validate_env_filename(name)
    except ValueError:
        return False
    return (get_configs_path() / n).is_file()


def parse_served_model_name(text: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.upper().startswith("SERVED_MODEL_NAME="):
            v = s.split("=", 1)[1].strip()
            return v or "—"
    return "—"


def display_name_for_file(file_name: str, text: str) -> str:
    sm = parse_served_model_name(text)
    if sm != "—":
        return sm
    return Path(file_name).stem or file_name


def ensure_seeded_from_hardcoded(
    docs: list[dict[str, Any]], format_text: Callable[[dict[str, Any]], str]
) -> None:
    """If CONFIGS_DIR has no `*.env` files, write seed from structured docs (dev/empty server)."""
    ensure_dir()
    p = get_configs_path()
    if any(p.glob("*.env")):
        return
    for doc in docs:
        (p / doc["fileName"]).write_text(format_text(doc), encoding="utf-8")
