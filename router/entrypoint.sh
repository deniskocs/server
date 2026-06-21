#!/bin/bash

link_chilik_certs() {
    ln -sf /etc/letsencrypt/live/api.chilik.net/fullchain.pem /etc/nginx/ssl/api.chilik.net.crt
    ln -sf /etc/letsencrypt/live/api.chilik.net/privkey.pem /etc/nginx/ssl/api.chilik.net.key
    ln -sf /etc/letsencrypt/live/api.chilik.net/fullchain.pem /etc/nginx/ssl/api.chilik.net.bundle.crt
    ln -sf /etc/letsencrypt/live/api.chilik.net/fullchain.pem /etc/nginx/ssl/argo.chilik.net.crt
    ln -sf /etc/letsencrypt/live/api.chilik.net/privkey.pem /etc/nginx/ssl/argo.chilik.net.key
    ln -sf /etc/letsencrypt/live/api.chilik.net/fullchain.pem /etc/nginx/ssl/argo.chilik.net.bundle.crt
}

CHILIK_CERT_DOMAINS=(
    api.chilik.net
    learn-english.chilik.net
    argo.chilik.net
)

check_chilik_cert_sans() {
    local cert_path="/etc/letsencrypt/live/api.chilik.net/fullchain.pem"
    local domain
    local sans

    if [ ! -f "$cert_path" ]; then
        echo "No chilik.net certificate found"
        return 1
    fi

    sans=$(openssl x509 -in "$cert_path" -noout -text)
    for domain in "${CHILIK_CERT_DOMAINS[@]}"; do
        if ! printf '%s' "$sans" | grep -Fq "DNS:${domain}"; then
            echo "chilik.net certificate missing SAN: $domain"
            return 1
        fi
    done

    echo "chilik.net certificate covers all required SANs."
    return 0
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

    link_chilik_certs
}

get_real_certs() {
    echo "Getting real certificates for chilik.net..."

    rm -rf /etc/letsencrypt/live/api.chilik.net \
       /etc/letsencrypt/archive/api.chilik.net \
       /etc/letsencrypt/renewal/api.chilik.net.conf

    chilik_certbot_args=(certonly --webroot -w /var/www/certbot \
        --email deniskocs@gmail.com \
        --cert-name api.chilik.net \
        --rsa-key-size 4096 \
        --agree-tos \
        --force-renewal \
        --non-interactive)
    for domain in "${CHILIK_CERT_DOMAINS[@]}"; do
        chilik_certbot_args+=(-d "$domain")
    done
    certbot "${chilik_certbot_args[@]}"

    link_chilik_certs
}

mkdir -p /etc/nginx/ssl \
         /etc/letsencrypt/live/api.chilik.net

# TZone staging (*.stage.t-zone.org): TLS в k3s (cert-manager + Traefik).
# Router: stream :443 → 10.0.0.2:443 для SNI *.t-zone.org / stage.t-zone.org.

certs_ok=true
if ! check_cert_expiry api.chilik.net; then
    certs_ok=false
fi
if ! check_chilik_cert_sans; then
    certs_ok=false
fi

if [ "$certs_ok" = true ]; then
    echo "Certificates are valid. Skipping renewal."
    link_chilik_certs
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
