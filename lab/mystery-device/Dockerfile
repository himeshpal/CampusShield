# A device nobody registered: open Redis (no auth) plus a web panel on 8080
FROM alpine:3.22
RUN apk add --no-cache redis python3 \
 && mkdir -p /www && echo '<html><title>Device Panel</title><body>ok</body></html>' > /www/index.html
CMD redis-server --protected-mode no --daemonize yes && exec python3 -m http.server 8080 --directory /www
