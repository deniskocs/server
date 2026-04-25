# vLLM runner (Decaf)

Docker-образ с **vLLM** OpenAI API, дефолтными `llm-configs/*.env` внутри образа и `docker-entrypoint.sh`.

- **Файл сборки:** `Dockerfile.decarf` (контекст — **эта папка**).
- **Тег в Hub / оркестраторе:** `deniskocs/learn-english:vllm-1.0.0` (см. `backend/app/vllm_env.py` и workflow деплоя).

Локальная сборка:

```bash
cd llm-orchestrator/vllm-runner
docker build -f Dockerfile.decarf -t deniskocs/learn-english:vllm-1.0.0 --platform linux/amd64 .
```

CI: образ собирается и пушится **перед** LLM Orchestrator API в `.github/workflows/deploy-orchestrator-backend.yaml`.

Старый путь `vllm/Dockerfile` в корне репозитория удалён; исходники раннера живут здесь, под проектом оркестратора.
