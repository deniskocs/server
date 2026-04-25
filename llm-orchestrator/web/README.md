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

## Скрипты

Из каталога `web/`:

```bash
npm install
npm run dev      # Vite dev server (http://localhost:5173)
npm run build    # production bundle → dist/
npm run preview  # локальный просмотр dist
npm run typecheck
```

См. общую спецификацию: [README в `llm-orchestrator`](../README.md).
