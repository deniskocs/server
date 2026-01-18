#!/bin/bash
set -e

# Активация виртуального окружения
. /app/venv/bin/activate

# Определение конфига (по умолчанию vllm)
CONFIG_NAME="${CONFIG_NAME:-vllm}"
CONFIG_FILE="/llm-configs/${CONFIG_NAME}.env"

# Загрузка конфигурации
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Config file not found at $CONFIG_FILE"
    exit 1
fi

# Сохраняем значение SERVED_MODEL_NAME из переменной окружения (если задано)
# чтобы не потерять его при загрузке конфига
ENV_SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-}"

# Загружаем переменные из конфига
. "$CONFIG_FILE"

# Имя модели берется из переменной окружения MODEL_NAME, если не задано - используется значение из конфига
MODEL_NAME="${MODEL_NAME:-$DEFAULT_MODEL_NAME}"
MODEL_PATH="/models/${MODEL_NAME}"

# SERVED_MODEL_NAME: приоритет у переменной окружения, затем значение из конфига, затем DEFAULT_MODEL_NAME
# Если переменная окружения была задана, используем её, иначе используем значение из конфига или DEFAULT_MODEL_NAME
if [ -n "$ENV_SERVED_MODEL_NAME" ]; then
    SERVED_MODEL_NAME="$ENV_SERVED_MODEL_NAME"
else
    # Используем значение из конфига (если есть) или DEFAULT_MODEL_NAME
    SERVED_MODEL_NAME="${SERVED_MODEL_NAME:-$DEFAULT_MODEL_NAME}"
fi

# Собираем аргументы vLLM из переменных конфига
VLLM_ARGS=""
if [ -n "$VLLM_QUANTIZATION" ]; then
    VLLM_ARGS="$VLLM_ARGS --quantization $VLLM_QUANTIZATION"
fi
if [ -n "$VLLM_MAX_MODEL_LEN" ]; then
    VLLM_ARGS="$VLLM_ARGS --max-model-len $VLLM_MAX_MODEL_LEN"
fi
if [ -n "$VLLM_DTYPE" ]; then
    VLLM_ARGS="$VLLM_ARGS --dtype $VLLM_DTYPE"
fi
if [ -n "$VLLM_GPU_MEMORY_UTILIZATION" ]; then
    VLLM_ARGS="$VLLM_ARGS --gpu-memory-utilization $VLLM_GPU_MEMORY_UTILIZATION"
fi
if [ "$VLLM_ENABLE_AUTO_TOOL_CHOICE" = "true" ]; then
    VLLM_ARGS="$VLLM_ARGS --enable-auto-tool-choice"
fi
if [ -n "$VLLM_TOOL_CALL_PARSER" ]; then
    VLLM_ARGS="$VLLM_ARGS --tool-call-parser $VLLM_TOOL_CALL_PARSER"
fi

# Проверка наличия модели в смонтированной директории /models
# Модели монтируются из ~/models на хосте и должны быть уже скачаны
if [ ! -d "$MODEL_PATH" ]; then
    echo "❌ Error: Model directory not found at $MODEL_PATH"
    echo "Model should be located in ~/models/${MODEL_NAME} on the host"
    
    # Показываем доступные модели в /models
    if [ -d "/models" ] && [ "$(ls -A /models 2>/dev/null)" ]; then
        echo "Available models in /models:"
        ls -la /models
    else
        echo "Directory /models is empty or does not exist"
    fi
    
    exit 1
fi

echo "✅ Model found at $MODEL_PATH"

echo "Starting vLLM API server..."
echo "Config: $CONFIG_NAME"
echo "Model: $MODEL_PATH"
echo "Served model name: $SERVED_MODEL_NAME"
echo "CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES"
echo "Port: $PORT"
echo "Host: $HOST"

# Запуск vLLM API сервера с параметрами из конфига
exec python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_PATH" \
  $VLLM_ARGS \
  --api-key "$API_KEY" \
  --served-model-name "$SERVED_MODEL_NAME" \
  --host "$HOST" \
  --port "$PORT"
