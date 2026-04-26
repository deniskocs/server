from __future__ import annotations

import threading

import smbclient
from smbclient import scandir

from paths import resolve_under_root, to_unc
from settings import SmbConfig

# smbclient/smbprotocol: глобальный пул соединений не потокобезопасен.
_smb_lock = threading.Lock()
_smb_ready = False


def register(cfg: SmbConfig) -> None:
    smbclient.register_session(
        cfg.host,
        username=cfg.user,
        password=cfg.password,
        port=cfg.port,
    )


def ensure_smb(cfg: SmbConfig) -> None:
    global _smb_ready
    if _smb_ready:
        return
    register(cfg)
    _smb_ready = True


def list_directory(cfg: SmbConfig, subpath: str) -> tuple[str, list[tuple[str, str]]]:
    """
    Возвращает (относительный_путь_от_шары, [(имя, 'file'|'directory'), ...]).
    """
    with _smb_lock:
        ensure_smb(cfg)
        rel = resolve_under_root(cfg.root, subpath)
        unc = to_unc(cfg.host, cfg.share, rel)
        items: list[tuple[str, str]] = []
        for entry in scandir(unc):
            kind = "directory" if entry.is_dir() else "file"
            items.append((entry.name, kind))
    items.sort(key=lambda x: (x[1] != "directory", x[0].casefold()))
    return rel, items


def read_file(cfg: SmbConfig, subpath: str) -> tuple[str, bytes]:
    with _smb_lock:
        ensure_smb(cfg)
        rel = resolve_under_root(cfg.root, subpath)
        unc = to_unc(cfg.host, cfg.share, rel)
        with smbclient.open_file(unc, mode="rb") as f:
            data = f.read()
    return rel, data
