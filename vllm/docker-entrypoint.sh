#!/bin/bash
set -e

# Активация виртуального окружения
source venv/bin/activate

# Значения по умолчанию
# Имя модели берется из переменной окружения MODEL_NAME, если не задано - используется значение по умолчанию
MODEL_NAME="${MODEL_NAME:-ai-automation-finetuned-awq}"
MODEL_PATH="/models/${MODEL_NAME}"

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
echo "Model: $MODEL_PATH"
echo "Served model name: $SERVED_MODEL_NAME"
echo "CUDA_VISIBLE_DEVICES: $CUDA_VISIBLE_DEVICES"
echo "Port: $PORT"
echo "Host: $HOST"

# Запуск vLLM API сервера
exec python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_PATH" \
  --quantization awq_marlin \
  --max-model-len 8192 \
  --dtype float16 \
  --gpu-memory-utilization 0.25 \
  --enable-auto-tool-choice \
  --tool-call-parser llama3_json \
  --api-key "$API_KEY" \
  --served-model-name "$SERVED_MODEL_NAME" \
  --host "$HOST" \
  --port "$PORT"
