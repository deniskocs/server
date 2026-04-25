# Base Image для серверов

Базовый Docker образ с предустановленным PyTorch 2.9.0 (CUDA 12.9).

## Содержимое образа

- **Base image**: `nvidia/cuda:12.8.0-runtime-ubuntu22.04`
- **Python**: 3.10
- **Виртуальное окружение**: `venv` (создано и активировано)
- **PyTorch**: 2.9.0 с CUDA 12.9 (cu129) - требуется для vLLM 0.12.0

## Сборка и публикация образа

### Текущий способ: скрипт `deploy.sh`

Сборка и пуш в Docker Hub делаются скриптом в этой папке (из корня репозитория `server` удобно так):

```bash
cd base
./deploy.sh
```

Скрипт читает общую конфигурацию (`../config.sh`), токен Docker Hub берёт через `../get-bitwarden-password.sh` и `../login-docker.sh`. Тег образа: `deniskocs/core:server-base-0.1.0`.

### Только локальная сборка (без публикации)

```bash
cd base
docker build --platform linux/amd64 -t deniskocs/core:server-base-0.1.0 .
```

### GitHub Actions (TODO)

Отдельного workflow для сборки и пуша `base` в этом репозитории **пока нет**. Когда появится (например, с именем вроде «Build and Push Base Image»), инструкцию можно будет дополнить путём к `.github/workflows/...` и шагом ручного запуска.

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
