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


def _download_model(repo_id: str, model_path: Path) -> None:
    from huggingface_hub import snapshot_download

    token = _env("HF_TOKEN") or _env("HUGGING_FACE_HUB_TOKEN")
    print(f"Downloading {repo_id} → {model_path}", flush=True)
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
    }
    for env_name, flag in flag_map.items():
        value = _env(env_name)
        if value:
            args.extend([flag, value])
    if _env("VLLM_ENABLE_AUTO_TOOL_CHOICE") == "true":
        args.append("--enable-auto-tool-choice")
    return args


# Параметры окружения (docker -e / k8s env):
#
# Обязательные
#   DEFAULT_MODEL_NAME — ID репозитория Hugging Face и подкаталог под /models
#     (например RedHatAI/Qwen3.5-122B-A10B-NVFP4 → /models/RedHatAI/Qwen3.5-122B-A10B-NVFP4).
#   API_KEY — ключ для заголовка Authorization; vLLM отклоняет запросы без него.
#
# Сервер и модель
#   HOST — адрес bind (по умолчанию 0.0.0.0).
#   Порт API — всегда 80 (константа LISTEN_PORT).
#   SERVED_MODEL_NAME — имя модели в /v1/models и в поле model запросов; если не задано —
#     последний сегмент пути (Qwen3.5-122B-A10B-NVFP4).
#   CUDA_VISIBLE_DEVICES — какие GPU видит процесс (задаётся в Dockerfile/k8s, не vLLM-флаг).
#
# Hugging Face (скачивание весов при первом старте)
#   HF_AUTO_DOWNLOAD — true/1 (по умолчанию): скачать snapshot, если каталог пустой или без весов.
#   HF_TOKEN | HUGGING_FACE_HUB_TOKEN — токен HF для gated/private репозиториев.
#
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


def main() -> None:
    model_id = _require("DEFAULT_MODEL_NAME")
    api_key = _require("API_KEY")
    host = _env("HOST", "0.0.0.0")
    served_model_name = _env("SERVED_MODEL_NAME") or model_id.rsplit("/", 1)[-1]

    model_path = Path("/models") / model_id
    auto_download = _env("HF_AUTO_DOWNLOAD", "true")

    if not _model_ready(model_path):
        if auto_download not in ("true", "1"):
            print(f"❌ Error: Model directory not found at {model_path}", file=sys.stderr)
            print(
                f"Set HF_AUTO_DOWNLOAD=true to download from Hugging Face, "
                f"or pre-populate /models/{model_id}",
                file=sys.stderr,
            )
            sys.exit(1)
        print(
            f"⬇️  Model missing at {model_path} — downloading {model_id} from Hugging Face...",
            flush=True,
        )
        model_path.mkdir(parents=True, exist_ok=True)
        _download_model(model_id, model_path)

    if not _model_ready(model_path):
        print(f"❌ Error: Model still not ready at {model_path} after download", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Model found at {model_path}")
    print("Starting vLLM API server...")
    print(f"Model: {model_path}")
    print(f"Served model name: {served_model_name}")
    print(f"CUDA_VISIBLE_DEVICES: {_env('CUDA_VISIBLE_DEVICES', '')}")
    print(f"Port: {LISTEN_PORT}")
    print(f"Host: {host}")

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
        "--host",
        host,
        "--port",
        LISTEN_PORT,
    ]
    os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    main()
