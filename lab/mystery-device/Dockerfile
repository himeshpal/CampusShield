# A device nobody registered: open Redis (no auth) plus a web panel on 8080.
# It carries an SSH client: scripts/demo.ps1 brute-force uses it to guess passwords on the
# lab PC, which the Wazuh agent there detects.
FROM alpine:3.22
RUN apk add --no-cache redis python3 dropbear-dbclient \
 && mkdir -p /www && echo '<html><title>Device Panel</title><body>ok</body></html>' > /www/index.html
CMD redis-server --protected-mode no --daemonize yes && exec python3 -m http.server 8080 --directory /www
