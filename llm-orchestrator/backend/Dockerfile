# API image for LLM server (see .github/workflows/deploy-orchestrator-backend.yaml)
# Official static CLI (multi-arch). apt install docker.io on slim often leaves no `docker`
# in PATH in CI/buildx → shell exit 127 on `docker --version`.
FROM docker:28-cli AS dockerclient

FROM python:3.12-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Docker *client* only — runtime mounts /var/run/docker.sock; engine stays on the host.
COPY --from=dockerclient /usr/local/bin/docker /usr/bin/docker
RUN docker --version

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Mount at runtime: /models (weights, same as vLLM), /configs (llm-configs .env)
ENV MODELS_DIR=/models \
    CONFIGS_DIR=/configs

EXPOSE 8765
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765"]
