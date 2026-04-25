"""Download HF snapshot into MODELS_DIR (same layout as `download/download_model.py`)."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Callable, Optional

from huggingface_hub import snapshot_download
from tqdm import tqdm

from .model_disk import local_snapshot_path

logger = logging.getLogger("llm_orchestrator.download")

_OnProgress = Callable[[Optional[float]], None]


class _LogPercentTqdm(tqdm):
    """HF tqdm: optional progress callback; optional debug logs."""

    def __init__(
        self,
        *a: object,
        on_progress: Optional[_OnProgress] = None,
        min_pct_step: float = 2.0,
        log_each_step: bool = False,
        **kw: object,
    ) -> None:
        self._on_progress = on_progress
        self._min_pct = min_pct_step
        self._last_pct: float = -1.0
        self._log_each_step = log_each_step
        kw.setdefault("mininterval", 0.2)
        super().__init__(*a, **kw)  # type: ignore[misc]
        self._last_indeterminate: float = 0.0

    def update(self, n: int = 1) -> bool | None:  # type: ignore[override]
        r = super().update(n)
        self._emit_progress()
        return r

    def refresh(self, *a: object, **kw: object) -> bool | None:  # type: ignore[override]
        r = super().refresh(*a, **kw)  # type: ignore[misc]
        self._emit_progress()
        return r

    def _emit_progress(self) -> None:
        op = self._on_progress
        if not op:
            return
        total = int(self.total) if self.total is not None else 0
        n_done = int(self.n)
        if total > 0:
            pct = 100.0 * n_done / total
            if (
                n_done >= total
                or self._last_pct < 0
                or pct - self._last_pct >= self._min_pct
            ):
                op(round(pct, 1))
                self._last_pct = pct
            if self._log_each_step:
                desc = (self.desc or "")[:80]
                logger.debug(
                    "huggingface download: %5.1f%%  (%d/%d)  %s",
                    pct,
                    n_done,
                    total,
                    desc,
                )
        else:
            now = time.monotonic()
            if now - self._last_indeterminate >= 0.4:
                op(None)
                self._last_indeterminate = now


def download_snapshot_for_config(
    model_id: str,
    models_root: Path,
    on_progress: Optional[_OnProgress] = None,
) -> Path:
    """
    Block until snapshot is available under `models_root/<org>/<name>/…`.
    Uses HF_TOKEN if set. Optional ``on_progress`` receives 0–100, or None if size unknown yet.
    """
    target = local_snapshot_path(models_root, model_id)
    target.mkdir(parents=True, exist_ok=True)

    raw = os.environ.get("HF_TOKEN")
    hf_token = (raw.strip() if raw else None) or None

    tqdm_class: type[_LogPercentTqdm] = _LogPercentTqdm
    if on_progress is not None:
        pr = on_progress

        class _TqdmForConfig(_LogPercentTqdm):
            def __init__(self, *a: object, **kw: object) -> None:
                super().__init__(*a, on_progress=pr, **kw)

        tqdm_class = _TqdmForConfig

    logger.info("starting snapshot_download repo_id=%s -> %s", model_id, target)
    snapshot_download(
        repo_id=model_id,
        local_dir=str(target),
        token=hf_token,
        tqdm_class=tqdm_class,
    )
    if on_progress:
        on_progress(100.0)
    logger.info("snapshot_download finished: %s", model_id)
    return target
