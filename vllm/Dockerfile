# Используем базовый образ с предустановленным PyTorch 2.9.0 (CUDA 12.9)
FROM deniskocs/core:server-base-0.1.0

# Базовый образ поднимает venv; torch 2.9 из base будет заменён при установке vLLM.
# vLLM 0.19.x: PyTorch 2.10 + Transformers 5.x (нужно для Qwen3.6 / qwen3_5_moe и др.).
# Индекс cu129 — рекомендация vLLM для CUDA 12.9 wheels.
RUN . /app/venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "vllm==0.19.1" --extra-index-url https://download.pytorch.org/whl/cu129 && \
    pip install --no-cache-dir torch-c-dlpack-ext && \
    pip cache purge && \
    rm -rf ~/.cache/pip

# Копирование конфигов
COPY vllm/llm-configs/ /llm-configs/

# Копирование entrypoint скрипта
COPY vllm/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Технические переменные окружения для контейнера
ENV CUDA_VISIBLE_DEVICES=0
ENV PYTORCH_ALLOC_CONF=expandable_segments:True
ENV HOST=0.0.0.0

EXPOSE 8000

# Запуск через entrypoint скрипт
ENTRYPOINT ["/bin/bash", "/docker-entrypoint.sh"]
