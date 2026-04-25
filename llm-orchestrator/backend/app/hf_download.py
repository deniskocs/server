"""Download HF snapshot into MODELS_DIR (same layout as `download/download_model.py`)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from huggingface_hub import snapshot_download
from tqdm import tqdm

from .model_disk import local_snapshot_path

logger = logging.getLogger("llm_orchestrator.download")


class _LogPercentTqdm(tqdm):
    """For HF tqdm integration: log % to server logs; throttle to avoid noise."""

    def __init__(self, *a: object, min_pct_step: float = 4.0, **kw: object) -> None:
        super().__init__(*a, mininterval=0.4, **kw)  # type: ignore[misc]
        self._min_pct = min_pct_step
        self._last_pct: float = -1.0

    def update(self, n: int = 1) -> bool | None:  # type: ignore[override]
        r = super().update(n)
        total = int(self.total) if self.total is not None else 0
        n_done = int(self.n)
        if total > 0:
            pct = 100.0 * n_done / total
            if (
                n_done >= total
                or self._last_pct < 0
                or pct - self._last_pct >= self._min_pct
            ):
                desc = (self.desc or "")[:80]
                logger.info(
                    "huggingface download: %5.1f%%  (%d/%d)  %s",
                    pct,
                    n_done,
                    total,
                    desc,
                )
                self._last_pct = pct
        return r


def download_snapshot_for_config(model_id: str, models_root: Path) -> Path:
    """
    Block until snapshot is available under `models_root/<org>/<name>/…`.
    Uses HF_TOKEN if set. Logs progress in percent via tqdm hook.
    """
    target = local_snapshot_path(models_root, model_id)
    target.mkdir(parents=True, exist_ok=True)

    raw = os.environ.get("HF_TOKEN")
    hf_token = (raw.strip() if raw else None) or None

    logger.info("starting snapshot_download repo_id=%s -> %s", model_id, target)
    snapshot_download(
        repo_id=model_id,
        local_dir=str(target),
        token=hf_token,
        tqdm_class=_LogPercentTqdm,
    )
    logger.info("snapshot_download finished: %s", model_id)
    return target
