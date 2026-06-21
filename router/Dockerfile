FROM ubuntu
RUN apt-get update && apt-get install -y \
    nginx \
    libnginx-mod-stream \
    openssl \
    curl \
    ca-certificates \
    certbot \
    && rm -rf /var/lib/apt/lists/*

RUN rm -f /etc/nginx/sites-enabled/default

COPY ./nginx/nginx.conf /etc/nginx/nginx.conf

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN mkdir -p /var/www/certbot /etc/nginx/ssl /etc/letsencrypt/live
RUN mkdir -p /var/www/certbot/.well-known/acme-challenge
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 80 443 8443
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
