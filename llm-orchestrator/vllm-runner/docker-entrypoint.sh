#!/bin/bash
set -e

# vLLM из одних переменных окружения (без /llm-configs и файлов .env).
# Обязательно: API_KEY, PORT, путь к весам (DEFAULT_MODEL_NAME или MODEL_NAME = относительный путь под /models, как на HuggingFace).
# Остальное — опциональные VLLM_*, SERVED_MODEL_NAME, HOST, CUDA_VISIBLE_DEVICES.

# Активация виртуального окружения
. /app/venv/bin/activate

MODEL_ID="${DEFAULT_MODEL_NAME:-$MODEL_NAME}"
if [ -z "$MODEL_ID" ]; then
    echo "❌ Set DEFAULT_MODEL_NAME or MODEL_NAME (directory under /models, e.g. Qwen/Qwen2.5-0.5B-Instruct)" >&2
    exit 1
fi
if [ -z "${PORT:-}" ]; then
    echo "❌ Set PORT" >&2
    exit 1
fi
if [ -z "${API_KEY:-}" ]; then
    echo "❌ Set API_KEY" >&2
    exit 1
fi

HOST="${HOST:-0.0.0.0}"

MODEL_PATH="/models/${MODEL_ID}"

# OpenAI-имя в API: явно задайте SERVED_MODEL_NAME или по умолчанию последний сегмент пути модели
if [ -n "${SERVED_MODEL_NAME:-}" ]; then
    :
else
    SERVED_MODEL_NAME="${MODEL_ID##*/}"
fi

# Собираем аргументы vLLM из переменных окружения
VLLM_ARGS=""
if [ -n "${VLLM_QUANTIZATION:-}" ]; then
    VLLM_ARGS="$VLLM_ARGS --quantization $VLLM_QUANTIZATION"
fi
if [ -n "${VLLM_MAX_MODEL_LEN:-}" ]; then
    VLLM_ARGS="$VLLM_ARGS --max-model-len $VLLM_MAX_MODEL_LEN"
fi
if [ -n "${VLLM_DTYPE:-}" ]; then
    VLLM_ARGS="$VLLM_ARGS --dtype $VLLM_DTYPE"
fi
if [ -n "${VLLM_GPU_MEMORY_UTILIZATION:-}" ]; then
    VLLM_ARGS="$VLLM_ARGS --gpu-memory-utilization $VLLM_GPU_MEMORY_UTILIZATION"
fi
if [ -n "${VLLM_TENSOR_PARALLEL_SIZE:-}" ]; then
    VLLM_ARGS="$VLLM_ARGS --tensor-parallel-size $VLLM_TENSOR_PARALLEL_SIZE"
fi
if [ -n "${VLLM_REASONING_PARSER:-}" ]; then
    VLLM_ARGS="$VLLM_ARGS --reasoning-parser $VLLM_REASONING_PARSER"
fi
if [ "${VLLM_ENABLE_AUTO_TOOL_CHOICE:-}" = "true" ]; then
    VLLM_ARGS="$VLLM_ARGS --enable-auto-tool-choice"
fi
if [ -n "${VLLM_TOOL_CALL_PARSER:-}" ]; then
    VLLM_ARGS="$VLLM_ARGS --tool-call-parser $VLLM_TOOL_CALL_PARSER"
fi
if [ -n "${VLLM_MOE_BACKEND:-}" ]; then
    VLLM_ARGS="$VLLM_ARGS --moe-backend $VLLM_MOE_BACKEND"
fi
if [ -n "${VLLM_KV_CACHE_DTYPE:-}" ]; then
    VLLM_ARGS="$VLLM_ARGS --kv-cache-dtype $VLLM_KV_CACHE_DTYPE"
fi

model_ready() {
    [ -d "$MODEL_PATH" ] && [ -n "$(ls -A "$MODEL_PATH" 2>/dev/null)" ] \
        && { [ -f "$MODEL_PATH/config.json" ] || [ -f "$MODEL_PATH/config.yaml" ] || [ -n "$(find "$MODEL_PATH" -maxdepth 2 -name '*.safetensors' -print -quit 2>/dev/null)" ]; }
}

HF_AUTO_DOWNLOAD="${HF_AUTO_DOWNLOAD:-true}"

if ! model_ready; then
    if [ "$HF_AUTO_DOWNLOAD" != "true" ] && [ "$HF_AUTO_DOWNLOAD" != "1" ]; then
        echo "❌ Error: Model directory not found at $MODEL_PATH" >&2
        echo "Set HF_AUTO_DOWNLOAD=true to download from Hugging Face, or pre-populate /models/$MODEL_ID" >&2
        exit 1
    fi
    echo "⬇️  Model missing at $MODEL_PATH — downloading $MODEL_ID from Hugging Face..."
    mkdir -p "$MODEL_PATH"
    MODEL_ID="$MODEL_ID" MODEL_PATH="$MODEL_PATH" python3 - <<'PY'
import os
import sys
from huggingface_hub import snapshot_download

repo_id = os.environ["MODEL_ID"]
local_dir = os.environ["MODEL_PATH"]
token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN") or None

print(f"Downloading {repo_id} → {local_dir}", flush=True)
snapshot_download(
    repo_id=repo_id,
    local_dir=local_dir,
    token=token,
    local_dir_use_symlinks=False,
)
print("Download complete.", flush=True)
PY
fi

if ! model_ready; then
    echo "❌ Error: Model still not ready at $MODEL_PATH after download" >&2
    exit 1
fi

echo "✅ Model found at $MODEL_PATH"

echo "Starting vLLM API server..."
echo "Model: $MODEL_PATH"
echo "Served model name: $SERVED_MODEL_NAME"
echo "CUDA_VISIBLE_DEVICES: ${CUDA_VISIBLE_DEVICES:-}"
echo "Port: $PORT"
echo "Host: $HOST"

exec python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_PATH" \
  $VLLM_ARGS \
  --api-key "$API_KEY" \
  --served-model-name "$SERVED_MODEL_NAME" \
  --host "$HOST" \
  --port "$PORT"
