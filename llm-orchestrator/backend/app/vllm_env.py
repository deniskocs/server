"""Parse .env and helpers aligned with vllm/docker-entrypoint + deploy workflows."""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)

# Canonical vLLM runner image: same as .github/workflows/build-vllm-runner.yaml
# Optional override, e.g. for a custom registry: VLLM_DOCKER_IMAGE=…
VLLM_IMAGE = (os.environ.get("VLLM_DOCKER_IMAGE") or "").strip() or (
    "deniskocs/core:vllm-runner-1.0.0"
)

# Префикс имён: фактическое имя = ``vllm_container_name(stem, env_map)`` (стем + суффикс модели).
VLLM_CONTAINER_PREFIX = "vllm-orchestrated"
# Совместимость: старое единое имя до per-profile контейнеров.
VLLM_CONTAINER = VLLM_CONTAINER_PREFIX
DEFAULT_GATED_API_KEY = "localkey"  # -e в workflow; entrypoint: --api-key

_DOCKER_NAME_MAX = 250


def _model_slug_for_container(env_map: dict[str, str]) -> str:
    raw = (env_map.get("DEFAULT_MODEL_NAME") or env_map.get("MODEL_NAME") or "").strip()
    if raw:
        part = raw.split("/")[-1].strip()
        if part:
            return part
    s = (env_map.get("SERVED_MODEL_NAME") or "").strip()
    if s and "/" in s:
        tail = s.split("/")[-1].strip()
        if tail:
            return tail
    return s


def sanitize_docker_name_component(s: str, max_len: int) -> str:
    t = s.replace("/", "-")
    t = re.sub(r"[^a-zA-Z0-9_.-]+", "-", t)
    t = re.sub(r"-+", "-", t).strip("-_.")
    if not t:
        t = "model"
    return t[:max_len].rstrip("-. ")


def vllm_container_name(config_stem: str, env_map: dict[str, str]) -> str:
    """
    One container per `*.env` profile: ``vllm-orchestrated--<config-stem>--<model-tail>``,
    where model tail is the last segment of ``DEFAULT_MODEL_NAME`` / ``MODEL_NAME``,
    or ``SERVED_MODEL_NAME`` if the former are unset. Docker name length is capped.
    """
    stem_s = sanitize_docker_name_component(config_stem, 80)
    mod = _model_slug_for_container(env_map)
    if mod:
        mod_s = sanitize_docker_name_component(mod, 120)
        body = f"{stem_s}--{mod_s}"
    else:
        body = stem_s
    name = f"{VLLM_CONTAINER_PREFIX}--{body}"
    if len(name) > _DOCKER_NAME_MAX:
        keep = _DOCKER_NAME_MAX - len(f"{VLLM_CONTAINER_PREFIX}--") - 1
        body = (body[: max(4, keep)]).rstrip("-.")
        name = f"{VLLM_CONTAINER_PREFIX}--{body}"[:_DOCKER_NAME_MAX]
    return name


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
    """Mirror vllm/docker-entrypoint.sh VLLM_ARGS (for debug logs if needed)."""
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
