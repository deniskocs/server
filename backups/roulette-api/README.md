# roulette-api — backup H2 (`roulette-api-data`)

Файловый бэкап PVC с H2 (`jdbc:h2:file:/data/roulette`) через `tar` временного pod’а на ноде PVC.

## Требования

- `kubectl` с доступом к кластеру
- PVC `roulette-api-data` Bound (есть annotation `volume.kubernetes.io/selected-node`)

## Backup

```bash
./backups/roulette-api/backup.sh
```

Скрипт:

1. scale `roulette-api` → 0  
2. копирует `/data` во временный pod  
3. пишет архив и поднимает Deployment обратно  

```text
backups/roulette-api/YYYY-MM-DD_HHMMSS/
  data.tar.gz
  meta.txt
```

## Restore

**Внимание:** заменяет все файлы в `/data` на PVC.

```bash
./backups/roulette-api/restore.sh
./backups/roulette-api/restore.sh 2026-08-01_114000
```

Скрипт спросит подтверждение (`yes`), на время restore остановит Deployment.

## Переменные окружения (опционально)

| Переменная   | По умолчанию        |
|-------------|---------------------|
| `NAMESPACE` | `roulette-api`      |
| `DEPLOYMENT`| `roulette-api`      |
| `PVC`       | `roulette-api-data` |
| `DATA_PATH` | `/data`             |
| `COPY_IMAGE`| `busybox:1.36`      |

## Заметки

- Это не SQL-dump, а снимок файлов H2 (`roulette.mv.db` и др.).
- Для переноса на другую ноду: backup → новый PVC на целевой ноде → restore.
- Каталоги `YYYY-MM-DD_*` в git не коммитятся.
