# API image for LLM server (see .github/workflows/deploy-orchestrator-backend.yaml)
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Docker *client* only — runtime mounts /var/run/docker.sock; engine stays on the host.
RUN apt-get update && apt-get install -y --no-install-recommends docker.io \
    && rm -rf /var/lib/apt/lists/* \
    && docker --version

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Mount at runtime: /models (weights, same as vLLM), /configs (llm-configs .env)
ENV MODELS_DIR=/models \
    CONFIGS_DIR=/configs

EXPOSE 8765
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8765"]
