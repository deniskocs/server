FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04

WORKDIR /app

# Установка Python и системных зависимостей
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Создание виртуального окружения
RUN python3.10 -m venv venv

# Активация venv и установка PyTorch 2.9.0 с CUDA 12.9
RUN . venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "torch==2.9.0" "torchaudio==2.9.0" --index-url https://download.pytorch.org/whl/cu129 && \
    pip cache purge && \
    rm -rf ~/.cache/pip

# Технические переменные окружения для контейнера
ENV PYTORCH_ALLOC_CONF=expandable_segments:True
