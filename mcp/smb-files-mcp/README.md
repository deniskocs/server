# smb-files-mcp

MCP-сервер по **stdio** (Cursor и др.): **прямой доступ к SMB** через `smbprotocol` / `smbclient`, без отдельного HTTP-сервиса `smb-files`. Логика путей и листинга совпадает с сервисом `local-services/smb-files`, но вся реализация живёт в этой папке.

## Конфигурация

```bash
cd smb-files-mcp
cp config.example.yaml config.yaml
```

В `config.yaml` укажите `host`, `user`, `password`, при необходимости `share`, `root`, `port`. Файл **не коммитится**.

Альтернатива без файла — переменные окружения (как в Docker): `SMB_HOST`, `SMB_USER`, `SMB_PASSWORD`, опционально `SMB_SHARE`, `SMB_ROOT`, `SMB_PORT`.

## Запуск

```bash
chmod +x run.sh   # один раз
./run.sh
```

### Cursor

```json
{
  "mcpServers": {
    "smb-files-mcp": {
      "command": "/absolute/path/to/server/mcp/smb-files-mcp/run.sh",
      "args": []
    }
  }
}
```

## Инструменты

| Tool | Назначение |
|------|------------|
| `smb_files_health` | Конфиг и сессия к SMB-хосту |
| `smb_files_list` | Каталог относительно `root` → `{ path, items: [{name, type}] }` |
| `smb_files_read` | Файл → `{ path_header, size, content_base64 }` (лимит размера в коде) |

Опционально положите файл `VERSION` в эту папку — его покажет `smb_files_health`; иначе версия `0.0.0-dev`.
