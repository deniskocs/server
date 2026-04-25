# `web` — статика и Nginx

Здесь всё, что относится к **первому** контейнеру в деплое: **фронтенд** (HTML/CSS/TypeScript, сборка в `dist/`) и **конфиг Nginx** (только раздача SPA; **API** в production — через `VITE_API_BASE_URL`, в CI: `http://10.0.0.46:<port>`).

## Структура

| Путь | Назначение |
|------|------------|
| `src/data/types.ts` | Типы для UI. |
| `src/data/apiBase.ts` | Базовый URL API (`VITE_API_BASE_URL` или пусто → относительный `/api`). |
| `src/data/repository.ts` | HTTP к бэкенду: `GET /api/orchestrator/models`, `POST .../models/actions`, CRUD текста `*.env`. |
| `src/main.ts` | Вход, отрисовка UI (vanilla TS). |
| `dist/` | Результат `npm run build` (в git не коммитится). |
| `Dockerfile` | Сборка: `npm run build` → `nginx:alpine`, раздача статики. |
| `nginx.default.conf` | Конфиг внутри образа: gzip, кэш для `/assets/`, `try_files` для SPA. |
| `.dockerignore` | Меньше контекст-слоя, без `node_modules`/`dist`. |

## Скрипты

Из каталога `web/`:

```bash
npm install
# в другом терминале: бэкенд (см. ../backend/README.md)
npm run dev      # http://localhost:5173 — прокси /api → :8765
npm run build    # production bundle → dist/
npm run preview  # только статика; без прокси к API нужен VITE_API_BASE_URL
npm run typecheck
```

Опционально `.env`: `VITE_API_BASE_URL=` (пусто = тот же origin, путь `/api/...`). В **dev** по умолчанию Vite проксирует `/api` на `http://127.0.0.1:8765`.

## Docker (production-статика)

Сборка в образе: TypeScript + Vite (минификация, `sourcemap: false` в `vite.config.ts`, без публичных source maps) → каталог `dist/` → **nginx** слушает **80**, отдаёт файлы.

Образ в CI собирает и выкатывает ручной workflow [**Deploy Orchestrator**](../../.github/workflows/deploy-orchestrator.yaml). В CI в образ вшивается `VITE_API_BASE_URL=http://10.0.0.46:<api_port>` (IP в LAN зафиксирован, **порт** — input `api_port`, по умолчанию **8765**), чтобы UI ходил на бэкенд на LLM-сервере. Локальный повтор:

```bash
cd web && docker build -t llm-orchestrator-web:local -f Dockerfile \
  --build-arg VITE_API_BASE_URL=http://10.0.0.46:8765 .
docker run --rm -p 8080:80 llm-orchestrator-web:local
```

Без `build-arg` пустой base (как пустой `VITE_API_BASE_URL` в dev).

→ [http://127.0.0.1:8080](http://127.0.0.1:8080)

## Деплой на Mac

Отдельный ручной workflow (не смешан с router): [`.github/workflows/deploy-orchestrator.yaml`](../../.github/workflows/deploy-orchestrator.yaml) · имя в Actions: **«Deploy Orchestrator»** · только **`workflow_dispatch`**.

**Actions** → **Deploy Orchestrator** → **Run workflow** — укажи **api_port** (порт бэка на `10.0.0.46`, по умолчанию 8765) → `docker build` (с `VITE_API_BASE_URL` выше) + `push` **`deniskocs/llm-orchestrator-web:0.0.1`**, по SSH: сеть `llm_orchestrator`, контейнер **`llm-orchestrator-web`**, **`8088:80`**.

Секреты: `DOCKER_HUB_USERNAME`, `DOCKER_HUB_ACCESS_TOKEN`, `SSH_PRIVATE_KEY_DEPLOY_TO_MAC_SERVER_BASE64`, `MAC_HOST`, `MAC_USER`. Тег/порт — в yaml. **linux/arm64** (Apple Silicon); иначе смени `platforms` в `build-push`.

**Бэкенд** (API, конфиги, vLLM через Docker): каталог [`../backend`](../backend).

См. общую спецификацию: [README в `llm-orchestrator`](../README.md).
