"""Start/stop the same vLLM image as .github/workflows/deploy-vllm.yaml (needs Docker CLI + socket on host)."""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
from pathlib import Path

from .vllm_env import DEFAULT_GATED_API_KEY, VLLM_CONTAINER, VLLM_IMAGE

logger = logging.getLogger(__name__)

# Клиент Docker внутри API-контейнера: по умолчанию типичный путь debian; переопределение: DOCKER_PATH
_DEFAULT_DOCKER = "/usr/bin/docker"


def docker_cli_path() -> str:
    return (os.environ.get("DOCKER_PATH") or _DEFAULT_DOCKER).strip() or _DEFAULT_DOCKER


def _docker_resolved() -> str | None:
    p = Path(docker_cli_path())
    if p.is_file() and os.access(p, os.X_OK):
        return str(p)
    w = shutil_which("docker")
    return w


def can_run_vllm_docker() -> bool:
    """True when host paths for -v and a usable docker client are available."""
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
    if _docker_resolved() is None:
        return False
    return True


def vllm_docker_unavailable_message() -> str:
    """Human-readable reason why Start/Stop cannot use the Docker runtime."""
    issues: list[str] = []
    vdo = (os.environ.get("VLLM_DOCKER", "1").strip() or "1")
    if vdo not in ("1", "true", "True", "yes"):
        issues.append(f"VLLM_DOCKER={vdo!r} (set 1 to enable)")
    if not (os.environ.get("HOST_MODELS_PATH") or "").strip():
        issues.append("HOST_MODELS_PATH is unset (host path for -v ...:/models)")
    if not (os.environ.get("HOST_LLM_CONFIGS_PATH") or "").strip():
        issues.append("HOST_LLM_CONFIGS_PATH is unset (host path for -v ...:/llm-configs)")
    if _docker_resolved() is None:
        issues.append(
            f"docker client not found (try {docker_cli_path()}, install docker.io in API image, mount /var/run/docker.sock)"
        )
    if not issues:
        return "unknown (can_run_vllm_docker is false)"
    return "; ".join(issues)


def require_vllm_docker() -> None:
    """
    Orchestrator always drives vLLM through Docker. Call before docker run / docker stop.
    """
    if can_run_vllm_docker():
        logger.info("vLLM docker runtime: OK, docker client=%s", _docker_cmd())
        return
    msg = vllm_docker_unavailable_message()
    logger.error("vLLM docker runtime: unavailable: %s", msg)
    raise RuntimeError(
        f"Cannot use Docker for vLLM: {msg}. "
        "Fix env and image (see deploy-orchestrator-backend: socket, docker.io, HOST_*)."
    )


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


def _docker_cmd() -> str:
    r = _docker_resolved()
    if r is None:
        return docker_cli_path()
    return r


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
    Pull image, remove old orchestrator vLLM container (see VLLM_CONTAINER in
    vllm_env), docker run with the same mounts as deploy-vllm.
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

    dc = _docker_cmd()
    logger.info(
        "vLLM run: removing any existing %s, pull %s, CONFIG_STEM=%r PORT=%s",
        VLLM_CONTAINER,
        VLLM_IMAGE,
        config_stem,
        port,
    )
    # Remove previous instance managed by the orchestrator (name != deploy-vllm vllm-server)
    subprocess.run(
        [dc, "rm", "-f", VLLM_CONTAINER],
        capture_output=True,
        text=True,
    )

    logger.info("vLLM run: docker pull %s", VLLM_IMAGE)
    pr = subprocess.run(
        [dc, "pull", VLLM_IMAGE],
        check=False,
        capture_output=True,
        text=True,
    )
    if pr.returncode != 0:
        raise RuntimeError(
            f"docker pull failed: {(pr.stderr or pr.stdout)[:2000]}"
        )

    run_cmd = [
        dc,
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
    logger.info("vLLM run: started container %s id=%s", VLLM_CONTAINER, cid)
    return (
        f"vLLM up: {VLLM_IMAGE} as {VLLM_CONTAINER} → {hl}:{port}, CONFIG_NAME={config_stem} ({cid})"
    )


def stop_vllm_container() -> str:
    dc = _docker_cmd()
    logger.info("vLLM stop: docker stop %s (cli=%s)", VLLM_CONTAINER, dc)
    st = subprocess.run(
        [dc, "stop", VLLM_CONTAINER],
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
