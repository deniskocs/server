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
- `PUT /api/orchestrator/configs/{id}/file-text` — тело `{ "text": "…" }` перезаписывает файл; ответ — как у таблицы; пока идёт action по этому конфигу — **409**
- `POST /api/orchestrator/configs/{id}/actions` — body `{"action":"download"|"start"|"stop"|"delete_model"|"delete_config"}`; для **`start`** в `.env` обязан быть **`PORT`** (и желательно `HOST`), иначе **400** — как у `vllm/docker-entrypoint.sh` (порт api_server). Если **не** включён реальный Docker (см. ниже), **Start/Stop** симулируют `deploy-vllm` + entrypoint: в **лог** пишутся `CONFIG_NAME`, `docker run` с `CONFIG_NAME`/`PORT`/`HOST` и т.д. С **`VLLM_DOCKER=1`**, `HOST_MODELS_PATH`, `HOST_LLM_CONFIGS_PATH` и `docker` на хосте (см. деплой), **Start** делает `docker pull` + `docker run` образа [как в `deploy-vllm`](../../.github/workflows/deploy-vllm.yaml) (`vllm-server`, тома `models` + `llm-configs`), **Stop** — `docker stop vllm-server`. На диске хоста рядом с `HOST_LLM_CONFIGS_PATH` должен лежать тот же `{имя-файла без .env}.env`, что в оркестраторе: entrypoint vLLM читает `/llm-configs/${CONFIG_NAME}.env`. Ошибки pull/run — **500**, отсутствие файла на хосте — **400**.

Список конфигов: файлы `*.env` в `CONFIGS_DIR` (в Docker: `/configs`). При **пустой** папке при старте в неё копируются сиды из [`app/seed_data.py`](app/seed_data.py), чтобы не было пустой таблицы. Добавление через UI/POST пишет новый `.env` на диск.

Если задан `MODELS_DIR` (в Docker: `/models`), статусы **Not on disk** / **On disk** (и доступность start/delete model) сопоставляются с **реальным** наличием весов: в первую очередь папка `MODELS_DIR/<org>/<model>` (как при `download/download_model.sh` / `huggingface_hub.snapshot_download`), плюс варианты `models--Org--Name` (кэш HF) и папка по последнему сегменту. Артефакты: `config.json`, `*.safetensors` / `*.bin` и т.д.

**Download** в UI: при `MODELS_DIR` и `DEFAULT_MODEL_NAME` в `.env` вызывается `snapshot_download` (как в `download/download_model.py`), в **логи** uvicorn/контейнера пишутся строки `huggingface download: 12.0%  (3/25) …` (шаг ~4% по прогрессу tqdm). Нужен сетевой доступ и при необходимости **`HF_TOKEN`** (gated-модели). Без `MODELS_DIR` остаётся короткая симуляция; в сообщении об этом сказано.

**Delete** (иконка корзины у весов): при `MODELS_DIR` + `DEFAULT_MODEL_NAME` с диска рекурсивно удаляются известные каталоги: `MODELS_DIR/org/…/model` (как у snapshot), `models--org--name` (кэш HF) и папка по последнему сегменту имени, если существовали. В лог пишется `removed model weight directory: …`. Без `MODELS_DIR` — по-прежнему только симуляция.

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

Пути можно переопределить **inputs** в workflow. В контейнере API также монтируется **Docker socket** и задаются **`HOST_MODELS_PATH`** / **`HOST_LLM_CONFIGS_PATH`** (абсолютные пути на **хосте** для `docker run -v` изнутри API), чтобы **Start** поднимал vLLM в отдельном контейнере. **Клиент Docker** внутри API: по умолчанию **`/usr/bin/docker`** (через `apt install docker.io` в `Dockerfile`); переопределение — **`DOCKER_PATH`**. **Имя контейнера vLLM** от оркестратора — **`vllm-orchestrated`**, в отличие от ручного [deploy-vllm](../../.github/workflows/deploy-vllm.yaml) (`vllm-server`), чтобы не дублировать одно и то же имя. Локально без socket и этих переменных остаётся только симуляция. `/api/health` возвращает `MODELS_DIR` / `CONFIGS_DIR`, если заданы.
