"""HTTP liveness for vLLM OpenAI server on PORT (same as --api-key in docker-entrypoint)."""

from __future__ import annotations

import os
import socket
import time
import urllib.error
import urllib.request
from typing import Any

from .vllm_env import DEFAULT_GATED_API_KEY

_DEFAULT_TIMEOUT = 0.45


def get_liveness_host() -> str:
    h = (os.environ.get("VLLM_LIVENESS_HOST") or "127.0.0.1").strip() or "127.0.0.1"
    return h


def parse_optional_port(env: dict[str, str]) -> int | None:
    raw = (env.get("PORT") or "").strip()
    if not raw:
        return None
    try:
        p = int(raw)
    except ValueError:
        return None
    if p < 1 or p > 65535:
        return None
    return p


def _api_key_for_probe(env: dict[str, str]) -> str:
    o = (os.environ.get("VLLM_LIVENESS_API_KEY") or "").strip()
    if o:
        return o
    v = (env.get("API_KEY") or "").strip()
    if v:
        return v
    return DEFAULT_GATED_API_KEY


def is_vllm_openai_reachable(
    env: dict[str, str],
    *,
    host: str | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> bool:
    """
    True if GET /v1/models returns 200 (vLLM entrypoints.openai.api_server with --api-key).
    """
    port = parse_optional_port(env)
    if port is None:
        return False
    h = (host or get_liveness_host()).strip() or "127.0.0.1"
    if not h:
        return False
    key = _api_key_for_probe(env)
    url = f"http://{h}:{port}/v1/models"
    req = urllib.request.Request(
        url, headers={"Authorization": f"Bearer {key}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, TimeoutError):
        return False
    except Exception:
        return False


def wait_until_vllm_reachable(
    env: dict[str, str],
    *,
    total_timeout: float = 90.0,
    interval: float = 0.5,
) -> bool:
    """Poll /v1/models until 200 or timeout (used after docker run)."""
    deadline = time.monotonic() + total_timeout
    while time.monotonic() < deadline:
        if is_vllm_openai_reachable(env, timeout=min(0.6, _DEFAULT_TIMEOUT + 0.2)):
            return True
        time.sleep(interval)
    return False


def is_port_open(host: str, port: int, timeout: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def is_vllm_serving_config_env(
    env_text: str, **kwargs: Any
) -> bool:
    from .vllm_env import parse_env_key_values

    return is_vllm_openai_reachable(parse_env_key_values(env_text), **kwargs)
