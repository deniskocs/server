#!/bin/bash

link_chilik_certs() {
    ln -sf /etc/letsencrypt/live/api.chilik.net/fullchain.pem /etc/nginx/ssl/api.chilik.net.crt
    ln -sf /etc/letsencrypt/live/api.chilik.net/privkey.pem /etc/nginx/ssl/api.chilik.net.key
    ln -sf /etc/letsencrypt/live/api.chilik.net/fullchain.pem /etc/nginx/ssl/api.chilik.net.bundle.crt
}

link_stage_certs() {
    ln -sf /etc/letsencrypt/live/stage.t-zone.org/fullchain.pem /etc/nginx/ssl/stage.t-zone.org.crt
    ln -sf /etc/letsencrypt/live/stage.t-zone.org/privkey.pem /etc/nginx/ssl/stage.t-zone.org.key
    ln -sf /etc/letsencrypt/live/stage.t-zone.org/fullchain.pem /etc/nginx/ssl/stage.t-zone.org.bundle.crt
}

check_cert_expiry() {
    local domain=$1
    local cert_path="/etc/letsencrypt/live/$domain/fullchain.pem"

    if [ ! -f "$cert_path" ]; then
        echo "No certificate found for $domain"
        return 1
    fi

    local expiry_date
    expiry_date=$(openssl x509 -enddate -noout -in "$cert_path" | cut -d= -f2)
    local expiry_ts
    expiry_ts=$(date -d "$expiry_date" +%s)
    local now_ts
    now_ts=$(date +%s)
    local remaining_days=$(( (expiry_ts - now_ts) / 86400 ))

    if [ $remaining_days -le 7 ]; then
        echo "Certificate for $domain expires in $remaining_days days — renewal required."
        return 1
    fi

    echo "Certificate for $domain is valid for $remaining_days more days."
    return 0
}

create_dummy_certs() {
    echo "Creating dummy certificates..."

    openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
        -keyout /etc/letsencrypt/live/api.chilik.net/privkey.pem \
        -out /etc/letsencrypt/live/api.chilik.net/fullchain.pem \
        -subj '/CN=api.chilik.net'

    openssl req -x509 -nodes -newkey rsa:4096 -days 1 \
        -keyout /etc/letsencrypt/live/stage.t-zone.org/privkey.pem \
        -out /etc/letsencrypt/live/stage.t-zone.org/fullchain.pem \
        -subj '/CN=stage.t-zone.org'

    link_chilik_certs
    link_stage_certs
}

get_real_certs() {
    echo "Getting real certificates for chilik.net..."

    rm -rf /etc/letsencrypt/live/api.chilik.net \
       /etc/letsencrypt/archive/api.chilik.net \
       /etc/letsencrypt/renewal/api.chilik.net.conf

    certbot certonly --webroot -w /var/www/certbot \
        --email deniskocs@gmail.com \
        -d api.chilik.net \
        -d learn-english.chilik.net \
        --rsa-key-size 4096 \
        --agree-tos \
        --force-renewal \
        --non-interactive

    link_chilik_certs

    echo "Getting real certificates for TZone staging..."

    rm -rf /etc/letsencrypt/live/stage.t-zone.org \
       /etc/letsencrypt/archive/stage.t-zone.org \
       /etc/letsencrypt/renewal/stage.t-zone.org.conf

    certbot certonly --webroot -w /var/www/certbot \
        --email deniskocs@gmail.com \
        -d stage.t-zone.org \
        -d auth.stage.t-zone.org \
        -d tenant.stage.t-zone.org \
        --cert-name stage.t-zone.org \
        --rsa-key-size 4096 \
        --agree-tos \
        --force-renewal \
        --non-interactive

    link_stage_certs
}

mkdir -p /etc/nginx/ssl \
         /etc/letsencrypt/live/api.chilik.net \
         /etc/letsencrypt/live/stage.t-zone.org

certs_ok=true
if ! check_cert_expiry api.chilik.net; then
    certs_ok=false
fi
if ! check_cert_expiry stage.t-zone.org; then
    certs_ok=false
fi

if [ "$certs_ok" = true ]; then
    echo "Certificates are valid. Skipping renewal."
    link_chilik_certs
    link_stage_certs
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
