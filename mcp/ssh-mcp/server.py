"""MCP-сервер: ограниченные SSH-команды на заранее настроенных хостах."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import yaml
from mcp.server.fastmcp import FastMCP

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"
SSH_TIMEOUT = 900

ALLOWED_COMMANDS = [
    "uptime",
    "hostname",
    "whoami",
    "uname -a",
    "df -h",
    "free -m",
    "ps aux",
    "docker ps",
    "docker ps -a",
    "docker info",
    "docker version",
    "docker stats --no-stream",
    "docker compose ps",
    "docker compose ls",
    "nvidia-smi",
    "nvidia-smi -L",
    "nvidia-smi --query-gpu=index,name,memory.total,memory.free,memory.used --format=csv",
    "systemctl list-units --type=service --state=running",
]

ALLOWED_SET = frozenset(ALLOWED_COMMANDS)

# docker logs с именем/id контейнера; опции только --tail N и --timestamps, без --follow
_DOCKER_LOGS = re.compile(
    r"^docker logs(?:\s+--tail\s+\d{1,7}|\s+--timestamps)*\s+"
    r"(?:[a-zA-Z0-9][a-zA-Z0-9_.-]*|[a-f0-9]{12,64})$"
)

# docker restart <container> — только имя или id, без доп. флагов
_DOCKER_RESTART = re.compile(
    r"^docker restart\s+(?:[a-zA-Z0-9][a-zA-Z0-9_.-]*|[a-f0-9]{12,64})$"
)


def _command_allowed(command: str) -> bool:
    cmd = command.strip()
    if cmd in ALLOWED_SET:
        return True
    if _DOCKER_LOGS.fullmatch(cmd):
        return True
    if _DOCKER_RESTART.fullmatch(cmd):
        return True
    return False

SYSTEM_INFO_COMMANDS = [
    "hostname",
    "uptime",
    "whoami",
    "uname -a",
    "df -h",
    "free -m",
    "docker ps",
]

RUNNING_SERVICES_CMD = "systemctl list-units --type=service --state=running"

_config_cache: dict[str, Any] | None = None

mcp = FastMCP("ssh-mcp")


def load_config() -> dict[str, Any]:
    global _config_cache
    if _config_cache is not None:
        return _config_cache
    if not CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Нет файла конфигурации: {CONFIG_PATH}")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("config.yaml должен содержать корневой объект")
    servers = data.get("servers")
    if not isinstance(servers, dict) or not servers:
        raise ValueError("В config.yaml нужен непустой ключ servers")
    _config_cache = data
    return _config_cache


def _config_error_message(exc: BaseException) -> str:
    return f"Ошибка конфигурации: {exc}"


def _web_config_allow_all(cfg: dict[str, Any]) -> bool:
    wc = cfg.get("web_config")
    if isinstance(wc, dict) and wc.get("allow_all_commands") is True:
        return True
    return False


def _server_entry(server_id: str) -> dict[str, Any] | None:
    cfg = load_config()
    servers = cfg["servers"]
    entry = servers.get(server_id)
    if isinstance(entry, dict):
        return entry
    for e in servers.values():
        if isinstance(e, dict) and str(e.get("name", "")) == server_id:
            return e
    return None


def _ssh_argv(entry: dict[str, Any], remote_command: str) -> list[str]:
    host = entry["host"]
    port = int(entry["port"])
    user = entry["user"]
    key = str(entry["key_file"])
    return [
        "ssh",
        "-i",
        key,
        "-p",
        str(port),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=yes",
        f"{user}@{host}",
        remote_command,
    ]


def _run_ssh(entry: dict[str, Any], command: str) -> dict[str, Any]:
    argv = _ssh_argv(entry, command)
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=SSH_TIMEOUT,
        )
        return {
            "code": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
        }
    except subprocess.TimeoutExpired:
        return {
            "code": -1,
            "stdout": "",
            "stderr": f"Таймаут SSH ({SSH_TIMEOUT} с)",
        }
    except FileNotFoundError:
        return {
            "code": -1,
            "stdout": "",
            "stderr": "Исполняемый файл ssh не найден в PATH",
        }
    except Exception as exc:  # noqa: BLE001 — граница MCP tool
        return {
            "code": -1,
            "stdout": "",
            "stderr": f"{type(exc).__name__}: {exc}",
        }


@mcp.tool()
def list_servers() -> dict[str, Any]:
    """Список настроенных серверов (имя, описание, host)."""
    try:
        cfg = load_config()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return {"error": str(exc), "servers": []}
    out: list[dict[str, str]] = []
    for sid, entry in cfg["servers"].items():
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name", sid))
        desc = str(entry.get("description", ""))
        host = str(entry.get("host", ""))
        out.append({"name": name, "description": desc, "host": host})
    return {
        "servers": out,
        "run_command_mode": "allow_all" if _web_config_allow_all(cfg) else "whitelist",
    }


@mcp.tool()
def run_command(server: str, command: str) -> dict[str, Any]:
    """Выполнить команду на сервере: whitelist или любая строка, если web_config.allow_all_commands.
    В режиме whitelist дополнительно: docker logs …; docker restart CONTAINER.
    """
    try:
        cfg = load_config()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return {
            "server": server,
            "command": command,
            "code": -1,
            "stdout": "",
            "stderr": _config_error_message(exc),
        }
    entry = _server_entry(server)
    if entry is None:
        return {
            "server": server,
            "command": command,
            "code": -1,
            "stdout": "",
            "stderr": f"Неизвестный сервер: {server!r}",
        }
    if not command.strip():
        return {
            "server": server,
            "command": command,
            "code": -1,
            "stdout": "",
            "stderr": "Пустая команда",
        }
    allow_all = _web_config_allow_all(cfg)
    if not allow_all and not _command_allowed(command):
        return {
            "server": server,
            "command": command,
            "code": -1,
            "stdout": "",
            "stderr": "Команда не разрешена (нет в whitelist)",
        }
    r = _run_ssh(entry, command)
    return {
        "server": server,
        "command": command,
        "code": r["code"],
        "stdout": r["stdout"],
        "stderr": r["stderr"],
    }


@mcp.tool()
def system_info(server: str) -> dict[str, Any]:
    """Собрать hostname, uptime, whoami, uname, df, free, docker ps на сервере."""
    try:
        load_config()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return {
            "server": server,
            "error": _config_error_message(exc),
            "commands": {},
        }
    entry = _server_entry(server)
    if entry is None:
        return {"server": server, "error": f"Неизвестный сервер: {server!r}", "commands": {}}
    results: dict[str, Any] = {}
    for cmd in SYSTEM_INFO_COMMANDS:
        r = _run_ssh(entry, cmd)
        results[cmd] = {
            "code": r["code"],
            "stdout": r["stdout"],
            "stderr": r["stderr"],
        }
    return {"server": server, "commands": results}


@mcp.tool()
def running_services(server: str) -> dict[str, Any]:
    """Список активных unit-ов systemd (running services)."""
    try:
        load_config()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return {
            "server": server,
            "command": RUNNING_SERVICES_CMD,
            "code": -1,
            "stdout": "",
            "stderr": _config_error_message(exc),
        }
    entry = _server_entry(server)
    if entry is None:
        return {
            "server": server,
            "command": RUNNING_SERVICES_CMD,
            "code": -1,
            "stdout": "",
            "stderr": f"Неизвестный сервер: {server!r}",
        }
    r = _run_ssh(entry, RUNNING_SERVICES_CMD)
    return {
        "server": server,
        "command": RUNNING_SERVICES_CMD,
        "code": r["code"],
        "stdout": r["stdout"],
        "stderr": r["stderr"],
    }


def main() -> None:
    load_config()
    mcp.run()


if __name__ == "__main__":
    main()
