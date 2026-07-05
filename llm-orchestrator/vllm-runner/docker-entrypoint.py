#!/usr/bin/env python3
"""vLLM OpenAI API server entrypoint — config only via environment variables."""

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
    if (model_path / "config.json").is_file() or (model_path / "config.yaml").is_file():
        return True
    for path in model_path.rglob("*.safetensors"):
        if len(path.relative_to(model_path).parts) <= 2:
            return True
    return False


def _download_model(repo_id: str, model_path: Path, token: str) -> None:
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


def _vllm_optional_args() -> list[str]:
    args: list[str] = []
    flag_map = {
        "VLLM_QUANTIZATION": "--quantization",
        "VLLM_MAX_MODEL_LEN": "--max-model-len",
        "VLLM_DTYPE": "--dtype",
        "VLLM_GPU_MEMORY_UTILIZATION": "--gpu-memory-utilization",
        "VLLM_TENSOR_PARALLEL_SIZE": "--tensor-parallel-size",
        "VLLM_REASONING_PARSER": "--reasoning-parser",
        "VLLM_TOOL_CALL_PARSER": "--tool-call-parser",
        "VLLM_MOE_BACKEND": "--moe-backend",
        "VLLM_KV_CACHE_DTYPE": "--kv-cache-dtype",
        "VLLM_LIMIT_MM_PER_PROMPT": "--limit-mm-per-prompt",
    }
    for env_name, flag in flag_map.items():
        value = _env(env_name)
        if value:
            args.extend([flag, value])
    if _env("VLLM_ENABLE_AUTO_TOOL_CHOICE") == "true":
        args.append("--enable-auto-tool-choice")
    if _env("VLLM_ENFORCE_EAGER") == "true":
        args.append("--enforce-eager")
    if _env("VLLM_LANGUAGE_MODEL_ONLY") == "true":
        args.append("--language-model-only")
    return args


# Параметры окружения (docker -e / k8s env):
#
# Обязательные
#   DEFAULT_MODEL_NAME — ID репозитория Hugging Face и подкаталог под /models
#     (например RedHatAI/Qwen3.5-122B-A10B-NVFP4 → /models/RedHatAI/Qwen3.5-122B-A10B-NVFP4).
#   SERVED_MODEL_NAME — имя модели в /v1/models и в поле model запросов (должно совпадать у клиентов).
#   API_KEY — ключ для заголовка Authorization; vLLM отклоняет запросы без него.
#   HF_TOKEN — Hugging Face API token (Bitwarden → huggingface-secrets в k8s).
#
# Сервер
#   Порт API — 80 (LISTEN_PORT); host — дефолт vLLM (0.0.0.0).
#
# Hugging Face (скачивание весов при первом старте, всегда включено)
# Параметры vLLM (опционально; пробрасываются как CLI-флаги api_server)
#   VLLM_QUANTIZATION — метод квантизации (awq, fp8, …).
#   VLLM_MAX_MODEL_LEN — максимальная длина контекста в токенах.
#   VLLM_DTYPE — dtype весов (auto, bfloat16, float16, …).
#   VLLM_GPU_MEMORY_UTILIZATION — доля VRAM GPU под модель и KV-cache (0.0–1.0).
#   VLLM_TENSOR_PARALLEL_SIZE — число GPU для tensor parallel.
#   VLLM_KV_CACHE_DTYPE — dtype KV-cache (например fp8 для экономии VRAM).
#   VLLM_MOE_BACKEND — бэкенд MoE-слоёв (flashinfer_cutlass и т.п.).
#   VLLM_REASONING_PARSER — парсер reasoning-блоков (qwen3 для Qwen3).
#   VLLM_ENABLE_AUTO_TOOL_CHOICE — true: включить --enable-auto-tool-choice.
#   VLLM_TOOL_CALL_PARSER — парсер tool calls в ответах модели.
#   VLLM_ENFORCE_EAGER — true: без CUDA graphs (меньше VRAM на cold start).
#   VLLM_LIMIT_MM_PER_PROMPT — JSON, напр. {"image": 0, "video": 0} — без vision warmup.
#   VLLM_LANGUAGE_MODEL_ONLY — true: text-only (RedHat qwen35 NVFP4; без vision encoder).


def main() -> None:
    model_id = _require("DEFAULT_MODEL_NAME")
    served_model_name = _require("SERVED_MODEL_NAME")
    api_key = _require("API_KEY")
    hf_token = _require("HF_TOKEN")

    model_path = Path("/models") / model_id

    if not _model_ready(model_path):
        _download_model(model_id, model_path, hf_token)

    if not _model_ready(model_path):
        print(f"❌ Error: Model still not ready at {model_path} after download", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Model found at {model_path}")
    print("Starting vLLM API server...")
    print(f"Model: {model_path}")
    print(f"Served model name: {served_model_name}")

    cmd = [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        str(model_path),
        *_vllm_optional_args(),
        "--api-key",
        api_key,
        "--served-model-name",
        served_model_name,
        "--port",
        LISTEN_PORT,
    ]
    os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    main()
