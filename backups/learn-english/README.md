# learn-english — backup MongoDB (`data-mongodb-0`)

Логический бэкап БД `raw-data` из пода `mongodb-0` (`mongodump` / `mongorestore`).  
Учётка берётся из secret `mongodb-credentials` в namespace `learn-english`.

## Требования

- `kubectl` с доступом к кластеру (`KUBECONFIG` / текущий context)
- под `mongodb-0` в статусе Running

## Backup

Из этой папки или из корня `server`:

```bash
./backups/learn-english/backup.sh
```

Создаёт каталог с датой/временем:

```text
backups/learn-english/YYYY-MM-DD_HHMMSS/
  dump.archive.gz   # архив mongodump
  meta.txt          # namespace, pod, node, размер и т.п.
```

## Restore

**Внимание:** restore делает `mongorestore --drop` — коллекции в `raw-data` будут перезаписаны.

```bash
# последний бэкап в этой папке
./backups/learn-english/restore.sh

# конкретный бэкап
./backups/learn-english/restore.sh 2026-08-01_105238

# или полный путь
./backups/learn-english/restore.sh ./2026-08-01_105238
```

Скрипт спросит подтверждение (`yes`).

## Переменные окружения (опционально)

| Переменная   | По умолчанию           |
|-------------|-------------------------|
| `NAMESPACE` | `learn-english`         |
| `POD`       | `mongodb-0`             |
| `CONTAINER` | `mongodb`               |
| `SECRET`    | `mongodb-credentials`   |
| `AUTH_DB`   | `raw-data`              |
| `DB_NAME`   | `raw-data`              |

## Заметки

- Это dump БД, не побайтовая копия PVC. Для переноса `local-path` на другую ноду этого обычно достаточно.
- Каталоги `YYYY-MM-DD_*` в git не коммитятся (см. корневой `.gitignore`).
