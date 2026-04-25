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

if [ ! -d "$MODEL_PATH" ]; then
    echo "❌ Error: Model directory not found at $MODEL_PATH" >&2
    echo "Expected weights under /models (mount host model dir) for DEFAULT_MODEL_NAME/MODEL_NAME=$MODEL_ID" >&2
    if [ -d "/models" ] && [ "$(ls -A /models 2>/dev/null)" ]; then
        echo "Available in /models:" >&2
        ls -la /models 2>&1
    else
        echo "Directory /models is empty or missing" >&2
    fi
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
