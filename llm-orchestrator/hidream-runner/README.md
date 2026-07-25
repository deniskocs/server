# HiDream runner

Docker-образ **HiDream-O1-Image-Dev-2604** (T2I) с OpenAI-совместимым API.

**Endpoints:** `POST /v1/images/generations`, `GET /health`, `GET /ready`. Auth не используется.

**Env:** `DEFAULT_MODEL_NAME`, `SERVED_MODEL_NAME`, опционально `HF_TOKEN`, `HIDREAM_DEFAULT_SIZE` (default `1024x1024`), `HIDREAM_DEFAULT_SEED`, `HIDREAM_DTYPE` (`bfloat16`).

**Модель на диске:** `/models/<DEFAULT_MODEL_NAME>` (hostPath `/home/denis/models` в k8s).

- **Тег:** `deniskocs/core:hidream-runner-1.0.0`
- **Локальный доступ (k8s):** `http://10.0.0.3:8031/v1/images/generations`

```bash
cd llm-orchestrator/hidream-runner
docker build -t deniskocs/core:hidream-runner-1.0.0 --platform linux/amd64 .
```

```bash
curl -s http://10.0.0.3:8031/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A red biplane over green fields","size":"1024x1024","seed":42}' \
  | jq -r '.data[0].b64_json' | base64 -d > out.png
```

CI: [`.github/workflows/build-hidream-runner.yaml`](../../.github/workflows/build-hidream-runner.yaml)
