#!/bin/sh
# syslog to a file the Wazuh agent reads (dropbear logs its logins there)
rsyslogd
dropbear -R
# connects to the Wazuh manager (172.25.0.4) whenever the "siem" profile is running
/var/ossec/bin/wazuh-control start >/dev/null 2>&1 || echo "wazuh agent did not start"
exec tcpsvd -E 0.0.0.0 21 ftpd -A /var/ftp
