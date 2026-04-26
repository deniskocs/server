# smb-books-mcp

MCP по **stdio**: каталог и **текст книг (FB2 / .fb2.zip)** с SMB через `smbprotocol`, без сервисов **smb-books** и **smb-files** по HTTP. Поведение совпадает с `local-services/smb-books`, реализация — в этой папке.

## Конфигурация

Поле **`root`** — каталог библиотеки на шаре (аналог `BOOKS_LIBRARY_ROOT`).

```bash
cd smb-books-mcp
cp config.example.yaml config.yaml
```

Без файла можно задать **`SMB_HOST`**, **`SMB_USER`**, **`SMB_PASSWORD`**, **`SMB_SHARE`**, **`SMB_PORT`**, и обязательно **`SMB_ROOT`** или **`BOOKS_LIBRARY_ROOT`** (каталог библиотеки).

`config.yaml` не коммитится.

## Запуск

```bash
chmod +x run.sh   # один раз
./run.sh
```

### Cursor

```json
{
  "mcpServers": {
    "smb-books-mcp": {
      "command": "/absolute/path/to/server/mcp/smb-books-mcp/run.sh",
      "args": []
    }
  }
}
```

## Инструменты

| Tool | Назначение |
|------|------------|
| `smb_books_health` | Конфиг и SMB-сессия |
| `smb_books_list` | `{ path, items }` — path короткий относительно библиотеки |
| `smb_books_read` | Плоский текст; при превышении лимита символов — `truncated` + `preview` |

Опционально файл **`VERSION`** в этой папке для поля `version` в health.
