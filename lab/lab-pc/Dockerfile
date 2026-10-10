# Computer-lab desktop: anonymous FTP + SSH. Telnet is installed but off -
# scripts/demo.ps1 open-port switches it on to trigger a "port opened" alert.
# (busybox ftpd under tcpsvd - vsftpd's standalone mode exits on nmap version probes)
FROM alpine:3.22
RUN apk add --no-cache dropbear busybox-extras \
 && mkdir -p /etc/dropbear /var/ftp/pub \
 && echo "lab notes" > /var/ftp/pub/readme.txt
CMD dropbear -R -E && exec tcpsvd -E 0.0.0.0 21 ftpd -A /var/ftp
