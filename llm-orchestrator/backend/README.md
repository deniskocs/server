# LLM Orchestrator — backend

Python **FastAPI** service: сиды конфигов, таблица рантайма, **vLLM только через Docker** на хосте (`docker` + сокет + `HOST_*`), логи на каждом шаге действий.

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
- `GET /api/orchestrator/models` — строки таблицы (рантайм по конфигам) + `count`
- `GET /api/orchestrator/configs/{id}/file-text` — текст «.env» для модалки
- `PUT /api/orchestrator/configs/{id}/file-text` — тело `{ "text": "…" }` перезаписывает файл; ответ — как у таблицы; пока идёт action по этому конфигу — **409**
- `POST /api/orchestrator/models/actions` — body `{"action":"download"|"start"|"stop"|"delete_model"|"delete_config","configFile":"my-model.env"}` (файл в `CONFIGS_DIR`, допускается `my-model` без суффикса — сервер допишет `.env`). Неизвестный `configFile` — **404**. **`start`/`stop`** требуют настроенного Docker-рантайма (`VLLM_DOCKER=1`, `HOST_MODELS_PATH`, `HOST_LLM_CONFIGS_PATH`, клиент `docker`, сокет); иначе **500**. Для **`start`** в `.env` обязан быть **`PORT`**, иначе **400**. **Start** — `docker pull` + `docker run` (`vllm-orchestrated`); **Stop** — `docker stop vllm-orchestrated`. Файл `{stem}.env` на хосте в `HOST_LLM_CONFIGS_PATH` должен совпадать с оркестратором. Ошибки pull/run/не настроен Docker — **500**; нет ожидаемого `.env` на хосте — **400** (FileNotFoundError) при `start`.

Список конфигов: файлы `*.env` в `CONFIGS_DIR` (в Docker: `/configs`). При **пустой** папке при старте в неё копируются сиды из [`app/seed_data.py`](app/seed_data.py), чтобы не было пустой таблицы. Добавление через UI/POST пишет новый `.env` на диск.

Если задан `MODELS_DIR` (в Docker: `/models`), статусы **Not on disk** / **On disk** (и доступность start/delete model) сопоставляются с **реальным** наличием весов: в первую очередь папка `MODELS_DIR/<org>/<model>` (как при `download/download_model.sh` / `huggingface_hub.snapshot_download`), плюс варианты `models--Org--Name` (кэш HF) и папка по последнему сегменту. Артефакты: `config.json`, `*.safetensors` / `*.bin` и т.д.

**Download** в UI: при `MODELS_DIR` и `DEFAULT_MODEL_NAME` в `.env` вызывается `snapshot_download` (как в `download/download_model.py`), в **логи** — tqdm и `action_download` в application log. Без `MODELS_DIR` — **500** (нужен каталог весов).

**Delete** (веса): при `MODELS_DIR` + `DEFAULT_MODEL_NAME` — реальное удаление каталогов весов. Пока vLLM отвечает на этом PORT (liveness) — **delete** не выполняется (нужен Stop). Без `MODELS_DIR` — **500**.

**Состояние running в таблице** определяется **проверкой vLLM**: успешный `GET http://$VLLM_LIVENESS_HOST:$PORT/v1/models` с `Authorization: Bearer …` (ключ из `API_KEY` в `.env`, иначе как у контейнера vLLM / переменная **`VLLM_LIVENESS_API_KEY`**). По умолчанию `VLLM_LIVENESS_HOST=127.0.0.1` (оркестратор и vLLM на одной машине). В [деплое API](../../.github/workflows/deploy-orchestrator-backend.yaml) задаётся `host.docker.internal` + `host-gateway`, чтобы из контейнера API достучаться до порта vLLM на хосте.

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

Пути можно переопределить **inputs** в workflow. В контейнере API: **Docker socket**, **`HOST_MODELS_PATH`**, **`HOST_LLM_CONFIGS_PATH`**, **клиент** `docker` (в образе — бинарь из официального `docker:*-cli`, по умолчанию **`/usr/bin/docker`**, `DOCKER_PATH`), **имя** контейнера vLLM — **`vllm-orchestrated`**. Без полного набора `Start`/`stop` не смогут управлять vLLM (см. логи). `/api/health` возвращает `MODELS_DIR` / `CONFIGS_DIR`, если заданы.
