# vLLM runner (Decaf)

Docker-образ с **vLLM** OpenAI API и `docker-entrypoint.sh`. Запуск — **только через `-e`**: `DEFAULT_MODEL_NAME` или `MODEL_NAME`, `PORT`, `API_KEY`, `SERVED_MODEL_NAME`, `VLLM_*`, `HOST`.

- **Файл сборки:** `Dockerfile.decarf` (контекст — **эта папка**).
- **Тег в Hub / k8s:** `deniskocs/core:vllm-runner-1.0.0` (см. `image:` в `infra/k8s/llms/models/*.yaml`).

Локальная сборка:

```bash
cd llm-orchestrator/vllm-runner
docker build -f Dockerfile.decarf -t deniskocs/core:vllm-runner-1.0.0 --platform linux/amd64 .
```

CI: [`.github/workflows/build-vllm-runner.yaml`](../../.github/workflows/build-vllm-runner.yaml)
