# vLLM runner (Decaf)

Docker-образ с **vLLM** OpenAI API и `docker-entrypoint.py`. Запуск — **только через `-e`**: `DEFAULT_MODEL_NAME`, `API_KEY`, `SERVED_MODEL_NAME`, `VLLM_*`, `HOST`. API слушает порт **80**.

**Модель на диске:** `/models/<DEFAULT_MODEL_NAME>` (hostPath `/home/denis/models` в k8s). Если каталог пустой или нет весов — entrypoint **скачивает** репозиторий с Hugging Face (`HF_AUTO_DOWNLOAD=true` по умолчанию). Для gated-моделей задай `HF_TOKEN` или `HUGGING_FACE_HUB_TOKEN`.

- **Файл сборки:** `Dockerfile.decarf` (контекст — **эта папка**).
- **Тег в Hub / k8s:** `deniskocs/core:vllm-runner-1.0.0` (см. `image:` в `infra/k8s/llms/models/*.yaml`).

Локальная сборка:

```bash
cd llm-orchestrator/vllm-runner
docker build -f Dockerfile.decarf -t deniskocs/core:vllm-runner-1.0.0 --platform linux/amd64 .
```

CI: [`.github/workflows/build-vllm-runner.yaml`](../../.github/workflows/build-vllm-runner.yaml)
