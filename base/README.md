# Base Image для серверов

Базовый Docker образ с предустановленным PyTorch 2.9.0 (CUDA 12.9).

## Содержимое образа

- **Base image**: `nvidia/cuda:12.8.0-runtime-ubuntu22.04`
- **Python**: 3.10
- **Виртуальное окружение**: `venv` (создано и активировано)
- **PyTorch**: 2.9.0 с CUDA 12.9 (cu129) - требуется для vLLM 0.12.0

## Сборка и публикация образа

### Основной способ: GitHub Actions

Workflow **[Build and push base image](../.github/workflows/build-base-image.yaml)** (в списке Actions то же имя):

- **workflow_dispatch** — ручной **Run workflow**
- **push** в `main`, если менялись **`base/**`** или сам workflow

Секреты: `DOCKER_HUB_USERNAME`, `DOCKER_HUB_ACCESS_TOKEN`. Тег: **`deniskocs/core:server-base-0.1.0`**, платформа **linux/amd64**.

### Локально: скрипт `deploy.sh` (Bitwarden + Docker Hub)

Альтернатива без CI: из корня `server` — `cd base && ./deploy.sh`. Использует `../scripts/config.sh`, токен через `get-bitwarden-password.sh`, логин `login-docker.sh`.

### Только локальная сборка (без публикации)

```bash
cd base
docker build --platform linux/amd64 -t deniskocs/core:server-base-0.1.0 .
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
