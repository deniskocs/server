# tzone — backup PostgreSQL (`tenant-postgres-data`)

Логический бэкап БД `tenant` из пода `tenant-postgres` (`pg_dump` / `pg_restore`).  
Пароль берётся из secret `tenant-service-secrets` (ключ `db-password`).

## Требования

- `kubectl` с доступом к кластеру (`KUBECONFIG` / текущий context)
- под с label `app=tenant-postgres` в статусе Running

## Backup

```bash
./backups/tzone/backup.sh
```

Создаёт каталог с датой/временем:

```text
backups/tzone/YYYY-MM-DD_HHMMSS/
  dump.dump   # pg_dump -Fc (custom format)
  meta.txt
```

## Restore

**Внимание:** restore делает `pg_restore --clean --if-exists` — объекты в БД `tenant` будут пересозданы.

```bash
# последний бэкап в этой папке
./backups/tzone/restore.sh

# конкретный бэкап
./backups/tzone/restore.sh 2026-08-01_110700

# или полный путь
./backups/tzone/restore.sh ./2026-08-01_110700
```

Скрипт спросит подтверждение (`yes`).

## Переменные окружения (опционально)

| Переменная             | По умолчанию               |
|------------------------|----------------------------|
| `NAMESPACE`            | `tzone`                    |
| `APP_LABEL`            | `tenant-postgres`          |
| `POD`                  | (авто: первый под по label)|
| `CONTAINER`            | `postgres`                 |
| `SECRET`               | `tenant-service-secrets`   |
| `SECRET_PASSWORD_KEY`  | `db-password`              |
| `DB_USER`              | `tenant`                   |
| `DB_NAME`              | `tenant`                   |

## Заметки

- Это dump БД, не побайтовая копия PVC. Для переноса `local-path` на другую ноду этого обычно достаточно.
- PVC `validation-landing-data` сюда не входит (отдельное файловое хранилище).
- Каталоги `YYYY-MM-DD_*` в git не коммитятся (см. корневой `.gitignore`).
