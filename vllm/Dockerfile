# Используем базовый образ с предустановленным PyTorch 2.9.0 (CUDA 12.9)
FROM deniskocs/core:server-base-0.1.0

WORKDIR /app

# PyTorch уже установлен в базовом образе в venv
# Устанавливаем vLLM 0.12.0 и torch-c-dlpack-ext
RUN . venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "vllm==0.12.0" && \
    pip install --no-cache-dir torch-c-dlpack-ext && \
    pip cache purge && \
    rm -rf ~/.cache/pip

# Копирование entrypoint скрипта
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Создание директории для storage
RUN mkdir -p /app/storage

# Технические переменные окружения для контейнера
ENV CUDA_VISIBLE_DEVICES=0
ENV PYTORCH_ALLOC_CONF=expandable_segments:True
ENV HOST=0.0.0.0

EXPOSE 8000

# Запуск через entrypoint скрипт
ENTRYPOINT ["/docker-entrypoint.sh"]
