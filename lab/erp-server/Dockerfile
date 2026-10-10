# College ERP portal (nginx, HTTP + self-signed HTTPS)
FROM nginx:1.30-alpine
RUN apk add --no-cache openssl \
 && openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
      -keyout /etc/nginx/erp.key -out /etc/nginx/erp.crt -subj "/CN=erp.campus.local"
COPY default.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
