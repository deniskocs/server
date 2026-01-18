# vLLM Image для серверов

Docker образ с предустановленным vLLM 0.12.0 для запуска LLM моделей.

## Содержимое образа

- **Base image**: `deniskocs/core:server-base-0.1.0` (с PyTorch 2.9.0 и CUDA 12.9)
- **vLLM**: 0.12.0
- **torch-c-dlpack-ext**: для поддержки DLPack
- **Python**: 3.10 (из базового образа)

## Сборка образа

### Локальная сборка

Для локальной сборки образа:
```bash
cd server/vllm
./deploy.sh
```

Скрипт соберет образ `deniskocs/learn-english:vllm-1.0.0`.

## Использование образа

Образ предназначен для запуска vLLM API сервера с поддержкой GPU.

### Пример запуска контейнера

```bash
docker run -d -ti \
  --name vllm-server \
  --restart unless-stopped \
  --gpus "device=0" \
  -p 8000:8000 \
  -v $(realpath ~/models):/models \
  -e API_KEY=localkey \
  -e MODEL_NAME=ai-automation-finetuned-awq \
  -e SERVED_MODEL_NAME=ai-automation-finetuned-awq \
  -e PORT=8000 \
  -e HOST=0.0.0.0 \
  deniskocs/learn-english:vllm-1.0.0
```

### Переменные окружения

- `MODEL_NAME` - имя модели (по умолчанию: `ai-automation-finetuned-awq`)
- `SERVED_MODEL_NAME` - имя модели для API (должно совпадать с `MODEL_NAME`)
- `API_KEY` - ключ API для доступа к серверу
- `PORT` - порт для API сервера (по умолчанию: 8000)
- `HOST` - хост для API сервера (по умолчанию: 0.0.0.0)
- `CUDA_VISIBLE_DEVICES` - какие GPU использовать (по умолчанию: 0)

### Монтирование моделей

Модели должны быть расположены в `~/models` на хосте и монтируются в `/models` внутри контейнера. Модель должна находиться по пути `~/models/${MODEL_NAME}` на хосте.
