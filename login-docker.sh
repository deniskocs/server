#!/bin/bash

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
