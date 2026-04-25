# API image for LLM server (see .github/workflows/deploy-orchestrator-backend.yaml)
# Official static CLI (multi-arch). apt install docker.io on slim often leaves no `docker`
# in PATH in CI/buildx → shell exit 127 on `docker --version`.
FROM docker:28-cli AS dockerclient

FROM python:3.12-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# nvidia-smi: for /api/orchestrator/host-stats. Run the container with GPU (e.g. --gpus all).
# Debian nvidia-smi is mainly published for amd64; arm64 dev builds skip it.
# Package names vary (trixie: nvidia-smi metapackage; older: nvidia-utils-550/535).
RUN set -eux; \
  apt-get update; \
  if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
    sed -i 's/Components: main/Components: main contrib non-free non-free-firmware/g' \
      /etc/apt/sources.list.d/debian.sources; \
  elif [ -f /etc/apt/sources.list ]; then \
    . /etc/os-release; \
    echo "deb http://deb.debian.org/debian ${VERSION_CODENAME} main contrib non-free non-free-firmware" \
      > /etc/apt/sources.list; \
  fi; \
  apt-get update; \
  ARCH=$(dpkg --print-architecture); \
  if [ "$ARCH" = "amd64" ]; then \
    apt-get install -y --no-install-recommends nvidia-smi \
      || apt-get install -y --no-install-recommends nvidia-utils-550 \
      || apt-get install -y --no-install-recommends nvidia-utils-535; \
    command -v nvidia-smi; \
  else \
    echo "Skipping nvidia-smi (arch=${ARCH} — use linux/amd64 image on the GPU host)."; \
  fi; \
  rm -rf /var/lib/apt/lists/*

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
