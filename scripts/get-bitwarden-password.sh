#!/bin/bash

set -e

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/init-colors.sh"

# Функция очистки при выходе
cleanup() {
    if [ -n "$BW_SESSION" ]; then
        bw logout > /dev/null 2>&1 || true
        unset BW_SESSION
    fi
}

# Устанавливаем trap для очистки при выходе
trap cleanup EXIT

# Проверка аргумента
if [ -z "$1" ]; then
    echo "Usage: $0 <item_name>"
    exit 1
fi

ITEM_NAME="$1"

# Очистка сессии Bitwarden в начале
cleanup

# Логин в Bitwarden
# Используем /dev/tty для интерактивного ввода, даже когда скрипт запущен из другого скрипта
TEMP_OUTPUT=$(mktemp)
# Перенаправляем stdin на /dev/tty, stdout в файл, stderr на терминал для видимости промптов
bw login < /dev/tty > "$TEMP_OUTPUT" 2>/dev/tty
LOGIN_EXIT=$?
if [ $LOGIN_EXIT -ne 0 ]; then
    echo "Login failed" >&2
    rm -f "$TEMP_OUTPUT"
    exit 1
fi
BW_SESSION=$(grep -oE 'BW_SESSION="[^"]+"' "$TEMP_OUTPUT" | sed 's/BW_SESSION="\(.*\)"/\1/' | head -n1)
rm -f "$TEMP_OUTPUT"
[ -n "$BW_SESSION" ] && [[ ${#BW_SESSION} -ge 20 ]] || { echo "Failed to get session" >&2; exit 1; }
export BW_SESSION

# Пытаемся найти item по имени и получаем токен
ITEM_ID=$(bw list items --search "$ITEM_NAME" --raw 2>/dev/null | jq -r '.[0].id' 2>/dev/null || echo "")
PASSWORD=$(bw get password "$ITEM_ID" 2>/dev/null || bw get item "$ITEM_ID" --raw 2>/dev/null | jq -r '.login.password' 2>/dev/null)

# Проверка, что пароль получен
if [ -z "$PASSWORD" ]; then
    echo -e "${RED}❌ Failed to get token from Bitwarden${NC}" >&2
    exit 1
fi

# Выводим пароль
echo "$PASSWORD"
