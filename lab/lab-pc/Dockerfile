# Computer-lab desktop: anonymous FTP + SSH. Telnet is installed but off -
# scripts/demo.ps1 open-port switches it on to trigger a "port opened" alert.
# (busybox ftpd under tcpsvd - vsftpd's standalone mode exits on nmap version probes)
# It is also the Wazuh-monitored host: the agent watches the SSH log and file integrity
# and reports to the manager (compose profile "siem"); without it, the agent just waits.
FROM alpine:3.22
ARG WAZUH_AGENT=4.8.2-r1
RUN apk add --no-cache dropbear busybox-extras rsyslog \
 && wget -qO /etc/apk/keys/alpine-devel@wazuh.com-633d7457.rsa.pub \
      "https://packages.wazuh.com/key/alpine-devel%40wazuh.com-633d7457.rsa.pub" \
 && echo "https://packages.wazuh.com/4.x/alpine/v3.12/main" >> /etc/apk/repositories \
 && apk add --no-cache "wazuh-agent=${WAZUH_AGENT}" \
 && mkdir -p /etc/dropbear /var/ftp/pub \
 && echo "lab notes" > /var/ftp/pub/readme.txt
COPY ossec.conf /var/ossec/etc/ossec.conf
COPY rsyslog.conf /etc/rsyslog.conf
COPY start.sh /start.sh
CMD ["/bin/sh", "/start.sh"]
