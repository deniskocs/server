"""Загрузка настроек SMB из config.yaml или переменных SMB_* (как у Docker smb-files)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

_cached: SmbConfig | None = None


@dataclass(frozen=True)
class SmbConfig:
    host: str
    user: str
    password: str
    share: str = "public"
    root: str = ""
    port: int = 445


def _from_mapping(data: dict[str, Any]) -> SmbConfig:
    host = str(data.get("host", "")).strip()
    user = str(data.get("user", "")).strip()
    password = str(data.get("password", ""))
    if not host or not user:
        raise ValueError("В конфиге нужны непустые host и user")
    share = str(data.get("share", "public")).strip() or "public"
    root = str(data.get("root", "")).strip()
    port_raw = data.get("port", 445)
    try:
        port = int(port_raw)
    except (TypeError, ValueError) as e:
        raise ValueError("port должен быть целым числом") from e
    if not (1 <= port <= 65535):
        raise ValueError("port вне диапазона 1–65535")
    return SmbConfig(
        host=host,
        user=user,
        password=password,
        share=share,
        root=root,
        port=port,
    )


def load_smb_config() -> SmbConfig:
    global _cached
    if _cached is not None:
        return _cached

    if CONFIG_PATH.is_file():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if not isinstance(raw, dict):
            raise ValueError("config.yaml должен содержать корневой объект (mapping)")
        _cached = _from_mapping(raw)
        return _cached

    if os.environ.get("SMB_HOST") and os.environ.get("SMB_USER"):
        _cached = SmbConfig(
            host=os.environ["SMB_HOST"].strip(),
            user=os.environ["SMB_USER"].strip(),
            password=os.environ.get("SMB_PASSWORD", ""),
            share=(os.environ.get("SMB_SHARE") or "public").strip() or "public",
            root=(os.environ.get("SMB_ROOT") or "").strip(),
            port=int(os.environ.get("SMB_PORT") or "445"),
        )
        return _cached

    raise FileNotFoundError(
        f"Нет {CONFIG_PATH}. Скопируйте config.example.yaml → config.yaml "
        "или задайте SMB_HOST, SMB_USER (и при необходимости SMB_PASSWORD, SMB_SHARE, SMB_ROOT)."
    )
