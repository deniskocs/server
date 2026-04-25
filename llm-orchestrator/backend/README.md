# LLM Orchestrator — backend

Python **FastAPI** service: сиды конфигов и in-memory «симуляция» рантайма (те же задержки и состояния, что раньше в браузере).

## Запуск

```bash
cd llm-orchestrator/backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8765 --reload
```

- API: `http://127.0.0.1:8765`
- `GET /api/health`
- `POST /api/orchestrator/configs` — тело: `{ "fileName": "name.env", "text": "…" }` (создаёт файл в `CONFIGS_DIR`, имя только `[a-zA-Z0-9._-].env`); при дубликате **409**
- `GET /api/orchestrator/table` — строки таблицы + `count`
- `GET /api/orchestrator/configs/{id}/file-text` — текст «.env» для модалки
- `POST /api/orchestrator/configs/{id}/actions` — body `{"action":"download"|"start"|"stop"|"delete_model"|"delete_config"}`

Список конфигов: файлы `*.env` в `CONFIGS_DIR` (в Docker: `/configs`). При **пустой** папке при старте в неё копируются сиды из [`app/seed_data.py`](app/seed_data.py), чтобы не было пустой таблицы. Добавление через UI/POST пишет новый `.env` на диск.

## Вместе с фронтом

1. Поднять бэкенд на **8765**.
2. В [`web`](../web/): `npm run dev` — Vite проксирует `/api` → `http://127.0.0.1:8765` (см. `web/vite.config.ts`).

## Docker-образ

```bash
docker build -t llm-orchestrator-api:local -f Dockerfile .
```

## Production (LLM-сервер)

Статика веба с пустым `VITE_API_BASE_URL` бьёт в **тот же origin** `/api/…` — Nginx (или host) **проксирует** на бэкенд, например `http://127.0.0.1:8765`.

**CI:** [`.github/workflows/deploy-orchestrator-backend.yaml`](../../.github/workflows/deploy-orchestrator-backend.yaml) — тот же SSH/ключи, что [деплой vLLM](../../.github/workflows/deploy-vllm.yaml) (`SSH_PRIVATE_KEY_BASE64_LOCAL_SERVER`, `home.chilik.net:2222`); образ `deniskocs/llm-orchestrator-api:0.0.1` (**linux/amd64**), тома:

| Хост (по умолчанию) | В контейнере | Смысл |
|---------------------|--------------|--------|
| `~/models` | `/models` | веса (как `~/models` у vLLM) |
| `~/llm-orchestrator-configs` | `/configs` | каталог `.env` конфигов (создаётся при деплое) |

Пути можно переопределить **inputs** в workflow. В процессе приложение пока **не** читает с диска — переменные `MODELS_DIR` / `CONFIGS_DIR` и монтирование заложены для следующей логики; `/api/health` возвращает их, если заданы.
