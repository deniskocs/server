# HiDream-O1-Image-Dev-2604 T2I API (OpenAI /v1/images/generations + /health).
#
# Base: PyTorch / CUDA (deniskocs/core:server-base-0.1.0).
FROM deniskocs/core:server-base-0.1.0

ARG HIDREAM_REPO=https://github.com/HiDream-ai/HiDream-O1-Image.git
ARG HIDREAM_REF=dev
# 0 = keep upstream use_flash_attn + install flash-attn (RTX 6000 Pro). 1 = Titan fallback.
ARG HIDREAM_DISABLE_FLASH_ATTN=0

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/hidream
RUN git clone --depth 1 --branch "${HIDREAM_REF}" "${HIDREAM_REPO}" .

WORKDIR /app/hidream-runner
COPY server.py docker-entrypoint.py patch_pipeline.py ./
ENV HIDREAM_DISABLE_FLASH_ATTN=${HIDREAM_DISABLE_FLASH_ATTN}
RUN chmod +x docker-entrypoint.py patch_pipeline.py && \
    /app/venv/bin/python3 /app/hidream-runner/patch_pipeline.py

ENV PYTHONPATH=/app/hidream
ENV FA_VERSION=2

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

# flash-attn (FA2) for RTX 6000 Pro / sm_120 — needs nvcc like vllm-runner JIT deps.
RUN if [ "$HIDREAM_DISABLE_FLASH_ATTN" = "0" ]; then \
      apt-get update && apt-get install -y --no-install-recommends --allow-change-held-packages \
        libcublas-12-8 \
        cuda-nvcc-12-8 \
        ninja-build \
        g++ \
      && apt-get clean && rm -rf /var/lib/apt/lists/* \
      && . /app/venv/bin/activate \
      && MAX_JOBS=4 pip install --no-cache-dir flash-attn --no-build-isolation \
      && pip cache purge && rm -rf ~/.cache/pip; \
    fi

EXPOSE 80

ENTRYPOINT ["/app/venv/bin/python3", "/app/hidream-runner/docker-entrypoint.py"]
