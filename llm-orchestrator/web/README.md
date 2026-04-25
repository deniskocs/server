# `web` — статика и Nginx

Здесь всё, что относится к **первому** контейнеру в деплое: **фронтенд** (HTML/CSS/TypeScript, сборка в `dist/`) и **конфиг Nginx** (раздача статики, `proxy_pass` к бэкенду, при необходимости TLS внутри образа — по решению).

## Структура

| Путь | Назначение |
|------|------------|
| `src/data/types.ts` | Типы конфигов (как в `llm-configs/*.yaml`). |
| `src/data/hardcoded.ts` | Захардкоженные снимки [`vllm/llm-configs/*.env`](../../vllm/llm-configs/) (как в доке), не root `llm-configs/`. |
| `src/data/repository.ts` | **Единственная точка** для UI: список конфигов, строки таблицы. Позже сюда же — `fetch`. |
| `src/main.ts` | Вход, отрисовка UI (vanilla TS). |
| `dist/` | Результат `npm run build` (в git не коммитится). |
| `Dockerfile` | Сборка: `npm run build` → `nginx:alpine`, раздача статики. |
| `nginx.default.conf` | Конфиг внутри образа: gzip, кэш для `/assets/`, `try_files` для SPA. |
| `.dockerignore` | Меньше контекст-слоя, без `node_modules`/`dist`. |

## Скрипты

Из каталога `web/`:

```bash
npm install
npm run dev      # Vite dev server (http://localhost:5173)
npm run build    # production bundle → dist/
npm run preview  # локальный просмотр dist
npm run typecheck
```

## Docker (production-статика)

Сборка в образе: TypeScript + Vite (минификация, `sourcemap: false` в `vite.config.ts`, без публичных source maps) → каталог `dist/` → **nginx** слушает **80**, отдаёт файлы.

Образ в CI собирает и выкатывает ручной workflow [**Deploy Orchestrator**](../../.github/workflows/deploy-orchestrator.yaml). Локально, если нужно повторить:

```bash
cd web && docker build -t llm-orchestrator-web:local -f Dockerfile .
docker run --rm -p 8080:80 llm-orchestrator-web:local
```

→ [http://127.0.0.1:8080](http://127.0.0.1:8080)

## Деплой на Mac

Отдельный ручной workflow (не смешан с router): [`.github/workflows/deploy-orchestrator.yaml`](../../.github/workflows/deploy-orchestrator.yaml) · имя в Actions: **«Deploy Orchestrator»** · только **`workflow_dispatch`**.

**Actions** → **Deploy Orchestrator** → **Run workflow** — `docker build` + `push` **`deniskocs/llm-orchestrator-web:0.0.1`**, по SSH: сеть `llm_orchestrator`, контейнер **`llm-orchestrator-web`**, **`8088:80`**.

Секреты: `DOCKER_HUB_USERNAME`, `DOCKER_HUB_ACCESS_TOKEN`, `SSH_PRIVATE_KEY_DEPLOY_TO_MAC_SERVER_BASE64`, `MAC_HOST`, `MAC_USER`. Тег/порт — в yaml. **linux/arm64** (Apple Silicon); иначе смени `platforms` в `build-push`.

См. общую спецификацию: [README в `llm-orchestrator`](../README.md).
