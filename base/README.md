# Base Image для серверов

Базовый Docker образ с предустановленным PyTorch 2.9.0 (CUDA 12.9).

## Содержимое образа

- **Base image**: `nvidia/cuda:12.8.0-runtime-ubuntu22.04`
- **Python**: 3.10
- **Виртуальное окружение**: `venv` (создано и активировано)
- **PyTorch**: 2.9.0 с CUDA 12.9 (cu129) - требуется для vLLM 0.12.0

## Сборка и публикация образа

### Через GitHub Actions

Используйте workflow "Build and Push Base Image" в разделе Actions GitHub:
1. Перейдите в раздел Actions
2. Выберите workflow "Build and Push Base Image"
3. Нажмите "Run workflow"
4. Workflow соберет и опубликует образ `deniskocs/core:server-base-0.1.0`

### Локальная сборка (без публикации)

Для локальной сборки образа без публикации:
```bash
cd backend/base
docker build -t deniskocs/core:server-base-0.1.0 .
```

## Использование базового образа

В других Dockerfile можно использовать этот образ как базовый:

```dockerfile
FROM deniskocs/core:server-base-0.1.0

# Виртуальное окружение уже создано и готово к использованию
# Активация: source venv/bin/activate

WORKDIR /app
# ... ваш код ...
```

## Зачем нужен базовый образ

- Ускоряет сборку финальных образов (PyTorch установлен)
- Обеспечивает единообразие версий зависимостей
- Экономит время при разработке и деплое
