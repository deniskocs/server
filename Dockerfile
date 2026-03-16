FROM ubuntu
RUN apt-get update
RUN apt-get install nginx -y
RUN apt-get install -y openssl
RUN apt-get install -y curl
RUN apt-get install -y ca-certificates
RUN apt-get install -y certbot

COPY *.html /var/www/html
COPY *.js /var/www/html
COPY images /var/www/html/images
COPY css /var/www/html/css
COPY dictionary /var/www/html/dictionary
COPY components /var/www/html/components
COPY analyzer /var/www/html/analyzer
COPY ./nginx/nginx.conf /etc/nginx/conf.d/default.conf

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN mkdir -p /var/www/certbot /etc/nginx/ssl /etc/letsencrypt/live
RUN mkdir -p /var/www/certbot/.well-known/acme-challenge
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 80 443
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
