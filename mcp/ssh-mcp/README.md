# ssh-mcp

Минимальный MCP-сервер на Python: выполнение **только заранее разрешённых** SSH-команд на хостах из `config.yaml`. Реализовано через системный клиент `ssh` и [FastMCP](https://github.com/modelcontextprotocol/python-sdk) (`mcp`).

## Запуск (рекомендуется)

Скрипт `run.sh` сам создаёт `.venv` при необходимости и ставит зависимости из `requirements.txt`, если виртуальное окружение новое или файл зависимостей изменился:

```bash
cd ssh-mcp
chmod +x run.sh   # один раз
./run.sh
```

Ручная установка (если нужна без скрипта):

```bash
cd ssh-mcp
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Настройка SSH

1. Отредактируйте `config.yaml`: `host`, `port`, `user`, пути `key_file` к **приватному** ключу.
2. На машине, где запускается MCP, должен быть доступен `ssh` в `PATH`.
3. Ключ должен подходить для входа на удалённый хост; для `StrictHostKeyChecking=yes` хост должен быть в `known_hosts` (один раз подключиться вручную или добавить ключ хоста).
4. `BatchMode=yes`: без интерактивного ввода пароля — только ключ (или другой неинтерактивный метод, настроенный в `ssh_config` не используется для ключей из `-i` напрямую, но ключ обязателен в конфиге).

## Запуск сервера

```bash
cd ssh-mcp
./run.sh
```

Либо с активированным venv: `python server.py`.

По умолчанию используется stdio-транспорт MCP (типично для встраивания в Cursor / другие MCP-клиенты).

### Пример конфигурации в Cursor

В настройках MCP удобнее указать скрипт (venv и зависимости поднимутся сами):

```json
{
  "mcpServers": {
    "ssh-mcp": {
      "command": "/absolute/path/to/ssh-mcp/run.sh",
      "args": []
    }
  }
}
```

Альтернатива — напрямую интерпретатор из venv (после ручной установки):

```json
{
  "mcpServers": {
    "ssh-mcp": {
      "command": "/absolute/path/to/ssh-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/ssh-mcp/server.py"]
    }
  }
}
```

## Доступные tools

| Tool | Назначение |
|------|------------|
| `list_servers` | Список серверов из `config.yaml` |
| `run_command` | Одна команда строго из whitelist |
| `system_info` | Набор диагностических команд (hostname, uptime, …) |
| `running_services` | `systemctl list-units --type=service --state=running` |

Произвольные команды выполнить нельзя: `run_command` принимает только строки из встроенного списка в `server.py`.

## Пример сценария

1. Вызвать `list_servers` — убедиться, что `prod1` / `prod2` видны.
2. Вызвать `run_command` с `server="prod1"`, `command="uptime"`.
3. Вызвать `system_info` для сводки или `running_services` для systemd.
