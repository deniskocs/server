"""Start/stop the same vLLM image as .github/workflows/deploy-vllm.yaml (needs Docker CLI + socket on host)."""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
from pathlib import Path

from .vllm_env import DEFAULT_GATED_API_KEY, VLLM_CONTAINER, VLLM_IMAGE

logger = logging.getLogger(__name__)


def can_run_vllm_docker() -> bool:
    """True when host paths for -v and docker binary are available."""
    if (os.environ.get("VLLM_DOCKER", "1").strip() or "1") not in (
        "1",
        "true",
        "True",
        "yes",
    ):
        return False
    m = (os.environ.get("HOST_MODELS_PATH") or "").strip()
    c = (os.environ.get("HOST_LLM_CONFIGS_PATH") or "").strip()
    if not m or not c:
        return False
    if not shutil_which("docker"):
        return False
    return True


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


def _resolve_existing_dir(p: str) -> Path:
    path = Path(p).expanduser().resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"not a directory: {path}")
    return path


def run_vllm_container(
    config_stem: str,
    port: int,
    host_listen: str,
) -> str:
    """
    Like deploy-vllm: pull image, remove old vllm-server, docker run with the same
    mounts pattern (models + llm-configs at /llm-configs in image).
    """
    m_root = (os.environ.get("HOST_MODELS_PATH") or "").strip()
    c_root = (os.environ.get("HOST_LLM_CONFIGS_PATH") or "").strip()
    if not m_root or not c_root:
        raise RuntimeError("HOST_MODELS_PATH and HOST_LLM_CONFIGS_PATH are required")
    mpath = _resolve_existing_dir(m_root)
    cpath = _resolve_existing_dir(c_root)
    cfg = cpath / f"{config_stem}.env"
    if not cfg.is_file():
        raise FileNotFoundError(
            f"Expected .env for CONFIG_NAME on host: {cfg} (mount HOST_LLM_CONFIGS_PATH = orchestrator's configs directory)"
        )

    hl = (host_listen or "0.0.0.0").strip() or "0.0.0.0"

    # Remove previous (same as deploy-vllm)
    subprocess.run(
        ["docker", "rm", "-f", VLLM_CONTAINER],
        capture_output=True,
        text=True,
    )

    logger.info("docker pull %s", VLLM_IMAGE)
    pr = subprocess.run(
        ["docker", "pull", VLLM_IMAGE],
        check=False,
        capture_output=True,
        text=True,
    )
    if pr.returncode != 0:
        raise RuntimeError(
            f"docker pull failed: {(pr.stderr or pr.stdout)[:2000]}"
        )

    run_cmd = [
        "docker",
        "run",
        "-d",
        "-ti",
        "--name",
        VLLM_CONTAINER,
        "--restart",
        "unless-stopped",
        "--gpus",
        "device=0",
        "-p",
        f"{port}:{port}",
        "-v",
        f"{mpath}:/models",
        "-v",
        f"{cpath}:/llm-configs",
        "-e",
        f"API_KEY={DEFAULT_GATED_API_KEY}",
        "-e",
        f"CONFIG_NAME={config_stem}",
        "-e",
        f"PORT={port}",
        "-e",
        f"HOST={hl}",
        VLLM_IMAGE,
    ]
    logger.info("docker run: %s", " ".join(shlex.quote(x) for x in run_cmd))
    rr = subprocess.run(run_cmd, capture_output=True, text=True)
    if rr.returncode != 0:
        err = (rr.stderr or rr.stdout or "").strip()[:2000]
        raise RuntimeError(f"docker run failed: {err}")

    cid = (rr.stdout or "").strip()[:12] or "?"
    return (
        f"vLLM up: {VLLM_IMAGE} as {VLLM_CONTAINER} → {hl}:{port}, CONFIG_NAME={config_stem} ({cid})"
    )


def stop_vllm_container() -> str:
    st = subprocess.run(
        ["docker", "stop", VLLM_CONTAINER],
        capture_output=True,
        text=True,
    )
    if st.returncode != 0:
        err = (st.stderr or st.stdout or "").strip()
        if "No such container" in err or "is not running" in err:
            return "vLLM container not running (already stopped)"
        raise RuntimeError(
            f"docker stop failed: {(st.stderr or st.stdout)[:2000]}"
        )
    return f"Stopped {VLLM_CONTAINER}"
