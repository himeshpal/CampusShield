# Wi-Fi access point management interface: SSH + HTTP admin page
FROM alpine:3.22
RUN apk add --no-cache dropbear busybox-extras \
 && mkdir -p /etc/dropbear /www \
 && echo '<html><head><title>AP-Block-A Admin</title></head><body><h1>Wireless AP Admin</h1><p>Default login: admin/admin</p></body></html>' > /www/index.html
CMD dropbear -R -E && exec httpd -f -p 80 -h /www
