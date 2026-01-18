# Download Models Scripts

Скрипты для скачивания моделей с HuggingFace на локальный сервер.

## Требования

### На локальной машине:
- SSH ключ для подключения к серверу
- Bitwarden CLI настроен (для получения токена HuggingFace при необходимости)

### На сервере:
- Python 3
- Библиотека `huggingface_hub`: `pip install huggingface_hub`

## Использование

```bash
./download-model.sh <model_name>
```

Пример:
```bash
./download-model.sh meta-llama/Llama-3.1-8B-Instruct
```

## Как это работает

1. Скрипт проверяет наличие SSH ключа `~/.ssh/server.rsa`
2. Если ключа нет, создает его и копирует на сервер
3. Получает токен HuggingFace из Bitwarden (если нужен для приватных моделей)
4. Копирует Python скрипт на сервер
5. Запускает Python скрипт на сервере для скачивания модели
6. Модель сохраняется в `~/models/<model_name>` на сервере

## Настройка

### SSH подключение
По умолчанию используется:
- Пользователь: `denis`
- Хост: `10.0.0.46`
- Ключ: `~/.ssh/server.rsa`

Для изменения этих параметров отредактируйте переменные в `download-model.sh`.

### Bitwarden
Токен HuggingFace должен быть сохранен в Bitwarden с именем `HUGGINGFACE_TOKEN`.
Если модель публичная, токен не требуется.

## Установка зависимостей на сервере

Если библиотека `huggingface_hub` не установлена на сервере:

```bash
ssh denis@10.0.0.46 "pip3 install huggingface_hub"
```
