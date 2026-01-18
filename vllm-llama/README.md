# vLLM Llama Image для серверов

Docker образ с предустановленным vLLM 0.12.0 для запуска Llama 3.3 70B FP8 модели.

## Содержимое образа

- **Base image**: `deniskocs/core:server-base-0.1.0` (с PyTorch 2.9.0 и CUDA 12.9)
- **vLLM**: 0.12.0
- **torch-c-dlpack-ext**: для поддержки DLPack
- **Python**: 3.10 (из базового образа)

## Сборка образа

### Локальная сборка

Для локальной сборки образа:
```bash
cd server/vllm-llama
./deploy.sh
```

Скрипт соберет образ `deniskocs/core:vllm-llama-1.0.0`.

## Использование образа

Образ предназначен для запуска vLLM API сервера с поддержкой GPU для модели nvidia/Llama-3.3-70B-Instruct-FP8.

### Пример запуска контейнера

```bash
docker run -d -ti \
  --name vllm-llama-server \
  --restart unless-stopped \
  --gpus all \
  -p 8001:8000 \
  -v $(realpath ~/models):/models \
  -e API_KEY=localkey \
  -e MODEL_NAME=nvidia/Llama-3.3-70B-Instruct-FP8 \
  -e SERVED_MODEL_NAME=nvidia/Llama-3.3-70B-Instruct-FP8 \
  -e PORT=8000 \
  -e HOST=0.0.0.0 \
  deniskocs/core:vllm-llama-1.0.0
```

### Переменные окружения

- `MODEL_NAME` - имя модели (по умолчанию: `nvidia/Llama-3.3-70B-Instruct-FP8`)
- `SERVED_MODEL_NAME` - имя модели для API (должно совпадать с `MODEL_NAME`)
- `API_KEY` - ключ API для доступа к серверу
- `PORT` - порт для API сервера (по умолчанию: 8000)
- `HOST` - хост для API сервера (по умолчанию: 0.0.0.0)
- `CUDA_VISIBLE_DEVICES` - какие GPU использовать (по умолчанию: 0)

### Особенности модели

- Модель использует FP8 квантование (float8_e5m2), поэтому параметр `--quantization` не требуется
- Модель большая (70B параметров), рекомендуется использовать все доступные GPU (`--gpus all`)
- Используется порт 8001 для избежания конфликтов с основным vLLM сервером

### Монтирование моделей

Модели должны быть расположены в `~/models` на хосте и монтируются в `/models` внутри контейнера. Модель должна находиться по пути `~/models/nvidia/Llama-3.3-70B-Instruct-FP8` на хосте.
