#!/bin/bash
#
# Проверено вручную: 25 апреля 2026. Ознакомился, разобрался, как работает скрипт и команды; доверяю.
# (Если такой строчки нет в новой правке — считай, что «AI / не перепроверял».)
#
# Выполняет `docker login` в Docker Hub с паролем из stdin-совместимого ввода
# (токен или пароль передаётся вторым аргументом, не отображается в командной строке).
#
# Параметры:
#   $1  — логин Docker Hub (реестр по умолчанию)
#   $2  — пароль или access token
#

set -e

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/init-colors.sh"

# Проверка аргументов
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <username> <password>" >&2
    exit 1
fi

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed" >&2
    exit 1
fi

DOCKER_USERNAME="$1"
DOCKER_PASSWORD="$2"

# Логин в Docker Hub
echo -e "${YELLOW}🐳 Logging in to Docker Hub...${NC}"
set +e
LOGIN_OUTPUT=$(echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin 2>&1)
LOGIN_EXIT=$?
set -e

# Игнорируем ошибку credential helper - она не критична, логин может пройти успешно
if [ $LOGIN_EXIT -ne 0 ]; then
    if echo "$LOGIN_OUTPUT" | grep -q "Error saving credentials"; then
        # Ошибка только в сохранении credentials, логин прошел успешно
        echo -e "${GREEN}✅ Logged in to Docker Hub${NC}"
        exit 0
    else
        echo -e "${RED}❌ Failed to login to Docker Hub${NC}" >&2
        echo "$LOGIN_OUTPUT" >&2
        exit 1
    fi
fi

echo -e "${GREEN}✅ Logged in to Docker Hub${NC}"
exit 0
