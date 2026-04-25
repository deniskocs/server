#!/bin/bash

set -e

# Загрузка общей конфигурации
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SERVER_ROOT/config.sh"

# Конфигурация образа
IMAGE_NAME="deniskocs/learn-english:vllm-1.0.0"

echo -e "${GREEN}🚀 Starting deployment of vLLM image${NC}"

# Что реально пойдёт в образ (защита от «запушил старый кэш / не тот файл»)
if [ -f "$SCRIPT_DIR/Dockerfile" ]; then
    echo -e "${YELLOW}📋 vLLM pin from Dockerfile:${NC}"
    grep -E '^\s*pip install.*vllm' "$SCRIPT_DIR/Dockerfile" || true
fi

# Получение токена из Bitwarden
DOCKER_HUB_ACCESS_TOKEN=$("$SERVER_ROOT/get-bitwarden-password.sh" "$BITWARDEN_ITEM_NAME") || exit 1

# Логин в Docker Hub
"$SERVER_ROOT/login-docker.sh" "$DOCKER_HUB_USERNAME" "$DOCKER_HUB_ACCESS_TOKEN" || exit 1

# Сборка образа
# VLLM_DOCKER_NO_CACHE=1 — без кэша слоёв (если Hub всё ещё со старым vLLM после правок Dockerfile)
BUILD_ARGS=(--platform linux/amd64 -f "$SCRIPT_DIR/Dockerfile" -t "$IMAGE_NAME")
if [ "${VLLM_DOCKER_NO_CACHE:-}" = "1" ]; then
    echo -e "${YELLOW}🔨 Building (no cache — VLLM_DOCKER_NO_CACHE=1)...${NC}"
    BUILD_ARGS+=(--no-cache)
else
    echo -e "${YELLOW}🔨 Building Docker image...${NC}"
fi
# Используем build context из корня server для доступа к vllm/llm-configs
docker build "${BUILD_ARGS[@]}" "$SERVER_ROOT"

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
