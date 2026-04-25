"""Detect whether default model weights exist under MODELS_DIR (HuggingFace Hub layout)."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def get_models_path() -> Path | None:
    """Root where HF-style `models--*` dirs live. None = disk checks and download are disabled."""
    raw = os.environ.get("MODELS_DIR", "").strip()
    if not raw:
        return None
    return Path(os.path.expanduser(raw)).resolve()


def parse_default_model_name(text: str) -> str | None:
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.upper().startswith("DEFAULT_MODEL_NAME="):
            v = s.split("=", 1)[1].strip()
            return v or None
    return None


def hf_hub_dir_name(model_id: str) -> str:
    """`org/name` -> `models--org--name` (HuggingFace hub cache directory name)."""
    return f"models--{model_id.replace('/', '--')}"


def local_snapshot_path(models_root: Path, model_id: str) -> Path:
    """Path used by `download/download_model.py` / `snapshot_download(local_dir=…)`: `MODELS_DIR/org/model`."""
    return models_root.joinpath(*model_id.split("/"))


def _dir_has_model_artifacts(d: Path) -> bool:
    try:
        if not d.is_dir():
            return False
        snaps = d / "snapshots"
        if snaps.is_dir():
            for child in snaps.iterdir():
                if not child.is_dir():
                    continue
                if (child / "config.json").is_file():
                    return True
                for p in child.rglob("*"):
                    if p.is_file() and p.suffix in (".safetensors", ".bin"):
                        return True
        for p in d.rglob("*"):
            if p.is_file() and p.suffix in (".safetensors", ".bin"):
                return True
        if (d / "config.json").is_file():
            return True
    except OSError:
        return False
    return False


def model_weights_appear_on_disk(models_root: Path, model_id: str) -> bool:
    if not model_id or not models_root.is_dir():
        return False
    # Same tree as our snapshot_download and download/download_model.py
    if _dir_has_model_artifacts(local_snapshot_path(models_root, model_id)):
        return True
    hub = models_root / hf_hub_dir_name(model_id)
    if _dir_has_model_artifacts(hub):
        return True
    last = model_id.split("/")[-1]
    if last:
        direct = models_root / last
        if _dir_has_model_artifacts(direct):
            return True
    return False


def _is_under_root(path: Path, root: Path) -> bool:
    try:
        rp = path.resolve()
        rr = root.resolve()
    except OSError:
        return False
    if rp == rr:
        return False
    return rp.is_relative_to(rr)  # py3.9+


def delete_model_weight_dirs(models_root: Path, model_id: str) -> list[str]:
    """
    Recursively remove directories that we treat as "this model's weights" under
    `models_root` (snapshot layout, HF hub cache name, and last-segment fallback).
    Safe: only paths inside `models_root` are passed to rmtree.
    """
    if not model_id or not models_root.is_dir():
        return []
    root = models_root
    seen: set[Path] = set()
    candidates: list[Path] = [
        local_snapshot_path(root, model_id),
        root / hf_hub_dir_name(model_id),
    ]
    last = model_id.split("/")[-1]
    if last:
        candidates.append(root / last)

    removed: list[str] = []
    for p in candidates:
        try:
            resolved = p.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if not _is_under_root(p, root):
            logger.warning("skip delete outside MODELS_DIR: %s", p)
            continue
        if not p.is_dir():
            continue
        try:
            shutil.rmtree(p)
        except OSError as e:
            logger.error("rmtree failed %s: %s", p, e)
            raise
        removed.append(str(p))
        logger.info("removed model weights directory: %s", p)
    return removed
