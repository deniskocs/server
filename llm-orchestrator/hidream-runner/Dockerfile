# HiDream-O1-Image-Dev-2604 T2I API (OpenAI /v1/images/generations + /health).
#
# Base: PyTorch / CUDA (deniskocs/core:server-base-0.1.0).
FROM deniskocs/core:server-base-0.1.0

ARG HIDREAM_REPO=https://github.com/HiDream-ai/HiDream-O1-Image.git
ARG HIDREAM_REF=dev

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/hidream
RUN git clone --depth 1 --branch "${HIDREAM_REF}" "${HIDREAM_REPO}" .

WORKDIR /app/hidream-runner
COPY server.py docker-entrypoint.py patch_pipeline.py ./
RUN chmod +x docker-entrypoint.py patch_pipeline.py && \
    /app/venv/bin/python3 /app/hidream-runner/patch_pipeline.py

ENV PYTHONPATH=/app/hidream
# FA_VERSION != 2|3 → optional flash_attn import (HiDream falls back when use_flash_attn=False).
ENV FA_VERSION=auto

RUN . /app/venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        "transformers==4.57.1" \
        diffusers \
        accelerate \
        einops \
        scipy \
        tqdm \
        pillow \
        torchvision \
        --extra-index-url https://download.pytorch.org/whl/cu129 && \
    pip install --no-cache-dir \
        "fastapi>=0.115.0" \
        "uvicorn[standard]>=0.32.0" \
        huggingface_hub && \
    pip cache purge && \
    rm -rf ~/.cache/pip

EXPOSE 80

ENTRYPOINT ["/app/venv/bin/python3", "/app/hidream-runner/docker-entrypoint.py"]
