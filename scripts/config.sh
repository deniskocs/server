#!/bin/bash
#
# Проверено вручную: 25 апреля 2026. Ознакомился, разобрался, как работает скрипт и команды; доверяю.
# (Если такой строчки нет в новой правке — считай, что «AI / не перепроверял».)

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/init-colors.sh"

# Конфигурация Docker Hub
DOCKER_HUB_USERNAME="deniskocs"

# Конфигурация Bitwarden
BITWARDEN_ITEM_NAME="DOCKER_HUB_ACCESS_TOKEN"
