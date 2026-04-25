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

Образ в CI собирает [`.github/workflows/deploy-when-push-to-main.yaml`](../../.github/workflows/deploy-when-push-to-main.yaml) (и smoke в [`llm-orchestrator-web-docker.yaml`](../../.github/workflows/llm-orchestrator-web-docker.yaml)). Локально, если нужно повторить:

```bash
cd web && docker build -t llm-orchestrator-web:local -f Dockerfile .
docker run --rm -p 8080:80 llm-orchestrator-web:local
```

→ [http://127.0.0.1:8080](http://127.0.0.1:8080)

**CI:** при изменениях в `llm-orchestrator/web/**` в GitHub Actions запускается [`.github/workflows/llm-orchestrator-web-docker.yaml`](../../.github/workflows/llm-orchestrator-web-docker.yaml): сборка образа и короткий smoke-тест HTTP.

## Деплой на Mac (как у router)

Один и тот же **ручной** workflow, что и для router: [`.github/workflows/deploy-when-push-to-main.yaml`](../../.github/workflows/deploy-when-push-to-main.yaml) · только **`workflow_dispatch`** (ни автопуш, ни `release:*` в npm).

**Actions** → **«Deploy web application to Mac»** → **Run workflow** — соберёт **router** и **llm-orchestrator-web**, `docker push` в Docker Hub, по SSH на Mac: сеть `llm_orchestrator`, контейнер `llm-orchestrator-web`, **`8088:80`**, образ **`deniskocs/llm-orchestrator-web:0.0.1`**.

Секреты: `DOCKER_HUB_USERNAME`, `DOCKER_HUB_ACCESS_TOKEN`, `SSH_PRIVATE_KEY_DEPLOY_TO_MAC_SERVER_BASE64`, `MAC_HOST`, `MAC_USER`. Смена тега/порта — правка workflow (как `router:0.0.1`). Apple Silicon: **`linux/arm64`**; иначе поменяй `platforms` в обоих шагах `build-push`.

См. общую спецификацию: [README в `llm-orchestrator`](../README.md).
