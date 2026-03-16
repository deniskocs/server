FROM ubuntu
RUN apt-get update
RUN apt-get install nginx -y
RUN apt-get install -y openssl
RUN apt-get install -y curl
RUN apt-get install -y ca-certificates
RUN apt-get install -y certbot

COPY ./nginx/nginx.conf /etc/nginx/conf.d/default.conf

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN mkdir -p /var/www/certbot /etc/nginx/ssl /etc/letsencrypt/live
RUN mkdir -p /var/www/certbot/.well-known/acme-challenge
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 80 443
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
