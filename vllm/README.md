# vLLM Image для серверов

Docker образ с предустановленным **vLLM 0.19.1** для запуска LLM моделей. Конфиги — `.env` в `vllm/llm-configs/`.

## Содержимое образа

- **Base image**: `deniskocs/core:server-base-0.1.0` (Ubuntu + CUDA runtime + venv)
- **vLLM**: **0.19.1** (ставит **PyTorch 2.10** и **Transformers 5.x** с индекса `cu129`; нужно для **Qwen3.6** и актуальных чекпойнтов)
- **torch-c-dlpack-ext**: для поддержки DLPack
- **PyYAML**: для чтения конфигурационных файлов
- **Python**: 3.10 (из базового образа)

## Сборка образа

### Локальная сборка

Для локальной сборки образа:
```bash
cd server/vllm
./deploy.sh
```

Скрипт соберет образ `deniskocs/learn-english:vllm-1.0.0` и загрузит его в Docker Hub.

## Конфигурация моделей

Конфигурации моделей хранятся в `vllm/llm-configs/` в формате переменных окружения (`.env` файлы). Каждый конфиг определяет параметры модели:
- Имя модели по умолчанию
- Параметры vLLM (quantization, dtype, gpu_memory_utilization и т.д.)

### Доступные конфигурации

- **vllm.env** - конфигурация для AWQ модели (`ai-automation-finetuned-awq`)
- **vllm-llama.env** - конфигурация для Llama FP8 модели (`nvidia/Llama-3.3-70B-Instruct-FP8`)

## Использование образа

Образ предназначен для запуска vLLM API сервера с поддержкой GPU. Один образ работает с разными моделями через параметр `CONFIG_NAME`.

### Пример запуска контейнера с AWQ моделью

```bash
docker run -d -ti \
  --name vllm-server \
  --restart unless-stopped \
  --gpus "device=0" \
  -p 8000:8000 \
  -v $(realpath ~/models):/models \
  -e API_KEY=localkey \
  -e CONFIG_NAME=vllm \
  -e MODEL_NAME=ai-automation-finetuned-awq \
  -e PORT=8000 \
  -e HOST=0.0.0.0 \
  deniskocs/learn-english:vllm-1.0.0
```

### Пример запуска контейнера с Llama моделью

```bash
docker run -d -ti \
  --name vllm-server \
  --restart unless-stopped \
  --gpus "device=0" \
  -p 8000:8000 \
  -v $(realpath ~/models):/models \
  -e API_KEY=localkey \
  -e CONFIG_NAME=vllm-llama \
  -e MODEL_NAME=nvidia/Llama-3.3-70B-Instruct-FP8 \
  -e PORT=8000 \
  -e HOST=0.0.0.0 \
  deniskocs/learn-english:vllm-1.0.0
```

### Переменные окружения

- `CONFIG_NAME` - имя конфигурационного файла без расширения (по умолчанию: `vllm`)
  - Должен соответствовать файлу в `/llm-configs/${CONFIG_NAME}.env`
- `MODEL_NAME` - имя модели (переопределяет значение из конфига)
  - Модель должна находиться в `~/models/${MODEL_NAME}` на хосте
- `API_KEY` - ключ API для доступа к серверу (обязательно)
- `PORT` - порт для API сервера (по умолчанию: 8000)
- `HOST` - хост для API сервера (по умолчанию: 0.0.0.0)
- `CUDA_VISIBLE_DEVICES` - какие GPU использовать (по умолчанию: 0)

### Монтирование моделей

Модели должны быть расположены в `~/models` на хосте и монтируются в `/models` внутри контейнера. Модель должна находиться по пути `~/models/${MODEL_NAME}` на хосте.

Например, для модели `ai-automation-finetuned-awq` путь на хосте должен быть:
```
~/models/ai-automation-finetuned-awq/
```

## Добавление новой модели

Для добавления новой модели:

1. Создайте новый `.env` конфиг в `vllm/llm-configs/` (например, `my-model.env`)
2. Определите параметры модели в конфиге:
   ```bash
   DEFAULT_MODEL_NAME=my-model-name
   SERVED_MODEL_NAME=my-model-name
   
   # Параметры vLLM
   VLLM_QUANTIZATION=awq_marlin  # или оставьте пустым
   VLLM_MAX_MODEL_LEN=8192
   VLLM_DTYPE=float16  # или оставьте пустым
   VLLM_GPU_MEMORY_UTILIZATION=0.5
   VLLM_ENABLE_AUTO_TOOL_CHOICE=true
   VLLM_TOOL_CALL_PARSER=llama3_json
   ```
3. Запустите контейнер с `CONFIG_NAME=my-model`

## Деплой через GitHub Actions

Деплой выполняется через GitHub Actions workflow `deploy-vllm.yaml`, который позволяет выбрать тип модели (AWQ или Llama) через параметр `model_type`.
