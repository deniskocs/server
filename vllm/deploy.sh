#!/bin/bash

set -e

# Загрузка общей конфигурации
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SERVER_ROOT/config.sh"

# Конфигурация образа
IMAGE_NAME="deniskocs/learn-english:vllm-1.0.0"

echo -e "${GREEN}🚀 Starting deployment of vLLM image${NC}"

# Получение токена из Bitwarden
DOCKER_HUB_ACCESS_TOKEN=$("$SERVER_ROOT/get-bitwarden-password.sh" "$BITWARDEN_ITEM_NAME") || exit 1

# Логин в Docker Hub
"$SERVER_ROOT/login-docker.sh" "$DOCKER_HUB_USERNAME" "$DOCKER_HUB_ACCESS_TOKEN" || exit 1

# Сборка образа
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to build Docker image${NC}"
    docker logout
    exit 1
fi

echo -e "${GREEN}✅ Image built successfully${NC}"

# Публикация образа
echo -e "${YELLOW}📤 Pushing image to Docker Hub...${NC}"
docker push "$IMAGE_NAME"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to push image to Docker Hub${NC}"
    docker logout
    exit 1
fi

echo -e "${GREEN}✅ Image pushed successfully${NC}"

# Логаут из Docker Hub
echo -e "${YELLOW}🚪 Logging out from Docker Hub...${NC}"
docker logout

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}   Image: $IMAGE_NAME${NC}"
