#!/bin/bash

set -e

# Загрузка общей конфигурации
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SERVER_ROOT/config.sh"

# Настройки SSH
KEY_NAME="server.rsa"
KEY_PATH="$HOME/.ssh/$KEY_NAME"
REMOTE_USER="denis"
REMOTE_HOST="10.0.0.46"
MODELS_DIR="~/models"

# Проверка аргументов
if [ -z "$1" ]; then
    echo -e "${RED}Usage: $0 <model_name>${NC}"
    echo "Example: $0 meta-llama/Llama-3.1-8B-Instruct"
    exit 1
fi

MODEL_NAME="$1"

echo -e "${GREEN}🚀 Starting model download${NC}"
echo -e "${YELLOW}Model: $MODEL_NAME${NC}"
echo -e "${YELLOW}Target server: $REMOTE_USER@$REMOTE_HOST${NC}"

# Проверка наличия SSH ключа
if [ ! -f "$KEY_PATH" ]; then
    echo -e "${YELLOW}SSH key not found. Creating new key...${NC}"
    ssh-keygen -t rsa -b 4096 -f "$KEY_PATH" -N "" -q
    
    echo -e "${YELLOW}Copying public key to server...${NC}"
    cat "${KEY_PATH}.pub" | ssh "$REMOTE_USER@$REMOTE_HOST" \
        'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && chmod 700 ~/.ssh'
    
    echo -e "${GREEN}✅ SSH key created and copied${NC}"
fi

# Получение токена HuggingFace из Bitwarden (если нужен)
HF_TOKEN_ITEM_NAME="HUGGINGFACE_TOKEN"
HF_TOKEN=$("$SERVER_ROOT/get-bitwarden-password.sh" "$HF_TOKEN_ITEM_NAME" 2>/dev/null || echo "")

# Копирование Python скрипта на сервер
echo -e "${YELLOW}📤 Copying download script to server...${NC}"
scp -i "$KEY_PATH" "$SCRIPT_DIR/download_model.py" "$REMOTE_USER@$REMOTE_HOST:/tmp/download_model.py"

# Запуск Python скрипта на сервере
echo -e "${YELLOW}🔽 Downloading model on server...${NC}"
ssh -i "$KEY_PATH" "$REMOTE_USER@$REMOTE_HOST" bash << EOF
set -e

# Путь к виртуальному окружению
VENV_DIR="~/venv-download"
VENV_PATH=\$(eval echo "\$VENV_DIR")

# Создание виртуального окружения, если его нет
if [ ! -d "\$VENV_PATH" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "\$VENV_PATH"
fi

# Активация виртуального окружения
source "\$VENV_PATH/bin/activate"

# Установка huggingface_hub, если не установлен
if ! python3 -c "import huggingface_hub" 2>/dev/null; then
    echo "Installing huggingface_hub..."
    pip install --upgrade pip
    pip install huggingface_hub
fi

# Запуск скрипта в виртуальном окружении
export HF_TOKEN="${HF_TOKEN}"
python3 /tmp/download_model.py "$MODEL_NAME" "$MODELS_DIR"

# Очистка
rm -f /tmp/download_model.py
EOF

echo -e "${GREEN}✅ Model download completed!${NC}"
echo -e "${GREEN}   Model: $MODEL_NAME${NC}"
echo -e "${GREEN}   Location: $MODELS_DIR${NC}"
