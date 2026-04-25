"""Parse .env and simulate deploy-vllm + vllm/docker-entrypoint.sh behaviour for Start."""

from __future__ import annotations

import logging
from pathlib import Path

# Как .github/workflows/deploy-vllm.yaml
VLLM_IMAGE = "deniskocs/learn-english:vllm-1.0.0"
VLLM_CONTAINER = "vllm-server"
DEFAULT_GATED_API_KEY = "localkey"  # -e в workflow; entrypoint: --api-key

logger = logging.getLogger(__name__)


def parse_env_key_values(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue
        k, v = s.split("=", 1)
        k, v = k.strip(), v.strip()
        if k:
            out[k] = v
    return out


def require_port_for_vllm_start(env: dict[str, str]) -> int:
    """Same expectation as docker-entrypoint (uses $PORT for api_server)."""
    raw = (env.get("PORT") or "").strip()
    if not raw:
        raise ValueError(
            "Set PORT=... in the .env (e.g. PORT=8000), as in deploy-vllm and docker-entrypoint.sh"
        )
    try:
        p = int(raw)
    except ValueError as e:
        raise ValueError("PORT must be an integer (e.g. PORT=8000)") from e
    if p < 1 or p > 65535:
        raise ValueError("PORT must be between 1 and 65535")
    return p


def build_vllm_args_preview(env: dict[str, str]) -> str:
    """Mirror vllm/docker-entrypoint.sh VLLM_ARGS for logs."""
    parts: list[str] = []
    if (env.get("VLLM_QUANTIZATION") or "").strip():
        parts.append(f"--quantization {env['VLLM_QUANTIZATION'].strip()}")
    if (env.get("VLLM_MAX_MODEL_LEN") or "").strip():
        parts.append(f"--max-model-len {env['VLLM_MAX_MODEL_LEN'].strip()}")
    if (env.get("VLLM_DTYPE") or "").strip():
        parts.append(f"--dtype {env['VLLM_DTYPE'].strip()}")
    if (env.get("VLLM_GPU_MEMORY_UTILIZATION") or "").strip():
        parts.append(
            f"--gpu-memory-utilization {env['VLLM_GPU_MEMORY_UTILIZATION'].strip()}"
        )
    if (env.get("VLLM_TENSOR_PARALLEL_SIZE") or "").strip():
        parts.append(
            f"--tensor-parallel-size {env['VLLM_TENSOR_PARALLEL_SIZE'].strip()}"
        )
    if (env.get("VLLM_REASONING_PARSER") or "").strip():
        parts.append(f"--reasoning-parser {env['VLLM_REASONING_PARSER'].strip()}")
    if (env.get("VLLM_ENABLE_AUTO_TOOL_CHOICE") or "").strip().lower() == "true":
        parts.append("--enable-auto-tool-choice")
    if (env.get("VLLM_TOOL_CALL_PARSER") or "").strip():
        parts.append(f"--tool-call-parser {env['VLLM_TOOL_CALL_PARSER'].strip()}")
    return " ".join(parts) if parts else "(no VLLM_* in .env beyond defaults)"


def log_simulated_deploy_vllm(
    config_file: str,
    env: dict[str, str],
    port: int,
    model_id: str | None,
) -> str:
    """
    What deploy-vllm / entrypoint would use; returns short lastRunMessage line.
    Full detail goes to logger INFO.
    """
    config_name = Path(config_file).stem
    host = (env.get("HOST") or "0.0.0.0").strip() or "0.0.0.0"
    default_m = (env.get("DEFAULT_MODEL_NAME") or "").strip()
    served = (env.get("SERVED_MODEL_NAME") or default_m or "").strip()
    model_path = f"/models/{default_m}" if default_m else "/models/<DEFAULT_MODEL_NAME>"

    vllm_args = build_vllm_args_preview(env)

    logger.info(
        "[sim deploy-vllm] CONFIG_NAME=%r (file %r) as in .github/workflows/deploy-vllm.yaml + docker-entrypoint.sh",
        config_name,
        config_file,
    )
    logger.info(
        (
            "[sim deploy-vllm] would: docker run --name %s -p %d:%d -v …/models:/models "
            "-e API_KEY=%s -e CONFIG_NAME=%s -e PORT=%d -e HOST=%s --gpus device=0 %s"
        ),
        VLLM_CONTAINER,
        port,
        port,
        DEFAULT_GATED_API_KEY,
        config_name,
        port,
        host,
        VLLM_IMAGE,
    )
    logger.info(
        "[sim deploy-vllm] entrypoint: . /llm-configs/%s.env → MODEL_NAME=%r → %s; SERVED_MODEL_NAME=%r",
        config_name,
        default_m,
        model_path,
        served,
    )
    logger.info("[sim deploy-vllm] vllm arg preview: %s", vllm_args)
    logger.info(
        "[sim deploy-vllm] openai server: --host %s --port %d --served-model-name %r (simulated, no real container start)",
        host,
        port,
        served,
    )

    return f"OK: sim vLLM on {host}:{port} (config {config_name}, model path {model_path})"
