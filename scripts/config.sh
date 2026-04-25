#!/bin/bash

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/init-colors.sh"

# Конфигурация Docker Hub
DOCKER_HUB_USERNAME="deniskocs"

# Конфигурация Bitwarden
BITWARDEN_ITEM_NAME="DOCKER_HUB_ACCESS_TOKEN"
