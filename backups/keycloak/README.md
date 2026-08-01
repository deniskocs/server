# keycloak — backup PostgreSQL (`data-keycloak-postgresql-0`)

Логический бэкап БД `keycloak` из пода `keycloak-postgresql-0` (`pg_dump` / `pg_restore`).  
Пароль берётся из secret `keycloak-secrets` (ключ `password`).

## Требования

- `kubectl` с доступом к кластеру
- под `keycloak-postgresql-0` в статусе Running

## Backup

```bash
./backups/keycloak/backup.sh
```

```text
backups/keycloak/YYYY-MM-DD_HHMMSS/
  dump.dump   # pg_dump -Fc
  meta.txt
```

## Restore

**Внимание:** `pg_restore --clean --if-exists` пересоздаёт объекты в БД `keycloak`.

```bash
./backups/keycloak/restore.sh
./backups/keycloak/restore.sh 2026-08-01_111500
```

Скрипт спросит подтверждение (`yes`).

Перед restore лучше остановить Keycloak (`kubectl -n keycloak scale sts/keycloak --replicas=0`), после — вернуть `replicas=1`.

## Переменные окружения (опционально)

| Переменная            | По умолчанию                |
|-----------------------|-----------------------------|
| `NAMESPACE`           | `keycloak`                  |
| `POD`                 | `keycloak-postgresql-0`     |
| `CONTAINER`           | `postgresql`                |
| `SECRET`              | `keycloak-secrets`          |
| `SECRET_PASSWORD_KEY` | `password`                  |
| `DB_USER`             | `keycloak`                  |
| `DB_NAME`             | `keycloak`                  |

## Заметки

- GitOps pin ноды: `infra/k8s/keycloak/keycloak-values.yaml`
- Каталоги `YYYY-MM-DD_*` в git не коммитятся
