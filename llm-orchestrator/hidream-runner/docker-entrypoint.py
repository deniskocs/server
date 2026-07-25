#!/usr/bin/env python3
"""HiDream image runner — HF download + uvicorn API on port 80."""

from __future__ import annotations

import os
import sys
from pathlib import Path

LISTEN_PORT = "80"


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name, default)
    return value if value else None


def _require(name: str) -> str:
    value = _env(name)
    if not value:
        print(f"❌ Set {name}", file=sys.stderr)
        sys.exit(1)
    return value


def _model_ready(model_path: Path) -> bool:
    if not model_path.is_dir() or not any(model_path.iterdir()):
        return False
    if (model_path / "config.json").is_file():
        return True
    for path in model_path.rglob("*.safetensors"):
        if len(path.relative_to(model_path).parts) <= 2:
            return True
    return False


def _download_model(repo_id: str, model_path: Path, token: str | None) -> None:
    from huggingface_hub import snapshot_download

    print(
        f"⬇️  Model missing at {model_path} — downloading {repo_id} from Hugging Face...",
        flush=True,
    )
    model_path.mkdir(parents=True, exist_ok=True)
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(model_path),
        token=token,
        local_dir_use_symlinks=False,
    )
    print("Download complete.", flush=True)


def main() -> None:
    model_id = _require("DEFAULT_MODEL_NAME")
    hf_token = _env("HF_TOKEN")

    model_path = Path("/models") / model_id
    os.environ["MODEL_PATH"] = str(model_path)

    if not _model_ready(model_path):
        _download_model(model_id, model_path, hf_token)

    if not _model_ready(model_path):
        print(f"❌ Model still not ready at {model_path} after download", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Model found at {model_path}")
    print("Starting HiDream API server (weights load on first import)...")

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "server:app",
        "--host",
        "0.0.0.0",
        "--port",
        LISTEN_PORT,
        "--app-dir",
        "/app/hidream-runner",
        "--timeout-keep-alive",
        "300",
    ]
    os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    main()
