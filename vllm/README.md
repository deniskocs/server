# vLLM Image для серверов

Docker образ с предустановленным **vLLM 0.19.1** для запуска LLM моделей.

**Исходники образа (Dockerfile + entrypoint + встроенные `llm-configs`)** перенесены в проект оркестратора: [`llm-orchestrator/vllm-runner`](../llm-orchestrator/vllm-runner) — файл сборки **`Dockerfile.decarf`**. В этой папке `vllm/` даны **симлинки** `llm-configs` → `../llm-orchestrator/vllm-runner/llm-configs` и `docker-entrypoint.sh` (удобно для старых путей в доке).

`vllm/Dockerfile` в корне **удалён** — сборка только через `vllm-runner` или `./deploy.sh`.

## Содержимое образа

- **Base image**: `deniskocs/core:server-base-0.1.0` (Ubuntu + CUDA runtime + venv)
- **vLLM**: **0.19.1** (ставит **PyTorch 2.10** и **Transformers 5.x** с индекса `cu129`; нужно для **Qwen3.6** и актуальных чекпойнтов)
- **torch-c-dlpack-ext**: для поддержки DLPack
- **PyYAML**: для чтения конфигурационных файлов
- **Python**: 3.10 (из базового образа)

## Сборка образа

### Локальная сборка

Из корня репозитория `server` (нужен `scripts/config.sh` и Bitwarden-логин к Hub, как раньше):
```bash
cd vllm
./deploy.sh
```

Скрипт соберет образ `deniskocs/learn-english:vllm-1.0.0` из `llm-orchestrator/vllm-runner/Dockerfile.decarf` и загрузит его в Docker Hub. Альтернатива: `cd llm-orchestrator/vllm-runner && docker build -f Dockerfile.decarf …` (см. README в той папке).

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

- Образ vLLM **не** собирается в **`deploy-orchestrator-backend`**, только `llm-orchestrator-api`. Сборка раннера: GitHub **[`build-vllm-runner`](../.github/workflows/build-vllm-runner.yaml)** или **`./deploy.sh`** в `vllm/`.
- **Только** перезапуск контейнера vLLM на сервере — по-прежнему [`.github/workflows/deploy-vllm.yaml`](../.github/workflows/deploy-vllm.yaml) (`config_name` и `docker pull` того же тега).
