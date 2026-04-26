"""Короткий path в ответе list: убрать префикс каталога библиотеки на шаре."""


from __future__ import annotations


def _norm_root(root: str) -> str:
    return root.strip().replace("\\", "/").strip("/")


def strip_library_prefix(full_path: str, library_root: str) -> str:
    """Полный path на шаре → короткий path относительно библиотеки."""
    root = _norm_root(library_root)
    fp = full_path.replace("\\", "/").strip("/")
    r = root.strip("/")
    if not fp or fp == r:
        return ""
    prefix = r + "/"
    if fp.startswith(prefix):
        return fp[len(prefix) :]
    return fp
