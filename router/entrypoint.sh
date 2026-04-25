#!/bin/bash

check_cert_expiry() {
    local domain=$1
    local cert_path="/etc/letsencrypt/live/$domain/fullchain.pem"

    # Если файла нет — нужно запрашивать
    if [ ! -f "$cert_path" ]; then
        echo "No certificate found for $domain"
        return 1
    fi

    # Извлекаем дату истечения
    local expiry_date
    expiry_date=$(openssl x509 -enddate -noout -in "$cert_path" | cut -d= -f2)
    local expiry_ts
    expiry_ts=$(date -d "$expiry_date" +%s)
    local now_ts
    now_ts=$(date +%s)
    local remaining_days=$(( (expiry_ts - now_ts) / 86400 ))

    # Если осталось меньше 7 дней — обновляем
    if [ $remaining_days -le 7 ]; then
        echo "Certificate for $domain expires in $remaining_days days — renewal required."
        return 1
    fi

    echo "Certificate for $domain is valid for $remaining_days more days."
    return 0
}

# Функция для создания временных сертификатов
create_dummy_certs() {
    echo "Creating dummy certificates..."
    
    # Создаем временные сертификаты для каждого домена
    openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
        -keyout /etc/letsencrypt/live/api.chilik.net/privkey.pem \
        -out /etc/letsencrypt/live/api.chilik.net/fullchain.pem \
        -subj '/CN=api.chilik.net'
    
    openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
        -keyout /etc/letsencrypt/live/learn-english.chilik.net/privkey.pem \
        -out /etc/letsencrypt/live/learn-english.chilik.net/fullchain.pem \
        -subj '/CN=learn-english.chilik.net'
    
    # Создаем символические ссылки для nginx
    ln -sf /etc/letsencrypt/live/api.chilik.net/fullchain.pem /etc/nginx/ssl/api.chilik.net.crt
    ln -sf /etc/letsencrypt/live/api.chilik.net/privkey.pem /etc/nginx/ssl/api.chilik.net.key
    ln -sf /etc/letsencrypt/live/api.chilik.net/fullchain.pem /etc/nginx/ssl/api.chilik.net.bundle.crt
    
    ln -sf /etc/letsencrypt/live/learn-english.chilik.net/fullchain.pem /etc/nginx/ssl/learn-english.chilik.net.crt
    ln -sf /etc/letsencrypt/live/learn-english.chilik.net/privkey.pem /etc/nginx/ssl/learn-english.chilik.net.key
    ln -sf /etc/letsencrypt/live/learn-english.chilik.net/fullchain.pem /etc/nginx/ssl/learn-english.chilik.net.bundle.crt
}

# Функция для получения реальных сертификатов
get_real_certs() {
    rm -rf /etc/letsencrypt/live/api.chilik.net \
       /etc/letsencrypt/archive/api.chilik.net \
       /etc/letsencrypt/renewal/api.chilik.net.conf \
       /etc/letsencrypt/live/learn-english.chilik.net \
       /etc/letsencrypt/archive/learn-english.chilik.net \
       /etc/letsencrypt/renewal/learn-english.chilik.net.conf

    echo "Getting real certificates..."
    
    # Получаем сертификаты
    certbot certonly --webroot -w /var/www/certbot \
        --email deniskocs@gmail.com \
        -d api.chilik.net \
        -d learn-english.chilik.net \
        --rsa-key-size 4096 \
        --agree-tos \
        --force-renewal \
        --non-interactive
    
    # Обновляем символические ссылки
    ln -sf /etc/letsencrypt/live/api.chilik.net/fullchain.pem /etc/nginx/ssl/api.chilik.net.crt
    ln -sf /etc/letsencrypt/live/api.chilik.net/privkey.pem /etc/nginx/ssl/api.chilik.net.key
    ln -sf /etc/letsencrypt/live/api.chilik.net/fullchain.pem /etc/nginx/ssl/api.chilik.net.bundle.crt
}

mkdir -p /etc/nginx/ssl \
         /etc/letsencrypt/live/api.chilik.net \
         /etc/letsencrypt/live/learn-english.chilik.net

# Проверяем сертификаты
if check_cert_expiry api.chilik.net; then
    echo "Certificates are valid. Skipping renewal."

    ln -sf /etc/letsencrypt/live/api.chilik.net/fullchain.pem /etc/nginx/ssl/api.chilik.net.crt
    ln -sf /etc/letsencrypt/live/api.chilik.net/privkey.pem /etc/nginx/ssl/api.chilik.net.key
    ln -sf /etc/letsencrypt/live/api.chilik.net/fullchain.pem /etc/nginx/ssl/api.chilik.net.bundle.crt
    
    nginx -g "daemon off;"
else
    echo "Certificates missing or expiring soon — proceeding with renewal."
    create_dummy_certs
    nginx -g "daemon off;" &
    NGINX_PID=$!
    sleep 10
    get_real_certs
    nginx -s reload
    wait $NGINX_PID
    exit 0
fi
