#!/usr/bin/with-contenv sh
# CampusShield additions to the Wazuh manager, applied on every start (runs after the
# image's own cont-init scripts). The manager keeps no volume: agents re-enrol after a
# restart and the alert history lives in CampusShield.
set -e
CONF=/var/ossec/etc/ossec.conf

# 1. No Wazuh indexer/dashboard here (CampusShield is the dashboard): drop Filebeat and
#    the modules that only feed the indexer (vulnerability feeds are also large downloads).
rm -rf /etc/services.d/filebeat
sed -i '/<vulnerability-detection>/,/<\/vulnerability-detection>/ s|<enabled>yes</enabled>|<enabled>no</enabled>|' "$CONF"
sed -i '/<indexer>/,/<\/indexer>/ s|<enabled>yes</enabled>|<enabled>no</enabled>|' "$CONF"
# The manager is infrastructure, not a monitored campus device: no self-assessment
# (its CIS / rootcheck / file-integrity results would otherwise show up as campus alerts).
sed -i '/<sca>/,/<\/sca>/ s|<enabled>yes</enabled>|<enabled>no</enabled>|' "$CONF"
sed -i '/<rootcheck>/,/<\/rootcheck>/ s|<disabled>no</disabled>|<disabled>yes</disabled>|' "$CONF"
sed -i '/<syscheck>/,/<\/syscheck>/ s|<disabled>no</disabled>|<disabled>yes</disabled>|' "$CONF"

# 2. Enrolment: register agents with their real IP (so alerts map to CampusShield assets)
#    and let a re-created lab container take over its old name straight away.
sed -i 's|<use_source_ip>no</use_source_ip>|<use_source_ip>yes</use_source_ip>|' "$CONF"
if ! grep -q "<force>" "$CONF"; then
  sed -i 's|<purge>yes</purge>|<purge>yes</purge>\
    <force>\
      <enabled>yes</enabled>\
      <key_mismatch>yes</key_mismatch>\
      <disconnected_time enabled="no">0</disconnected_time>\
      <after_registration_time>0</after_registration_time>\
    </force>|' "$CONF"
fi

# 3. CampusShield rules (clear titles for account changes and FTP uploads).
install -o wazuh -g wazuh -m 660 /campusshield/local_rules.xml /var/ossec/etc/rules/local_rules.xml

# 4. Forward alerts (level >= 5) to CampusShield.
install -o root -g wazuh -m 750 /campusshield/custom-campusshield /var/ossec/integrations/custom-campusshield
if ! grep -q "custom-campusshield" "$CONF"; then
  cat >> "$CONF" <<EOF

<ossec_config>
  <integration>
    <name>custom-campusshield</name>
    <hook_url>${CAMPUSSHIELD_API}/api/v1/automation/wazuh</hook_url>
    <api_key>${SERVICE_API_KEY}</api_key>
    <level>5</level>
    <alert_format>json</alert_format>
  </integration>
</ossec_config>
EOF
fi
# The image starts the manager before this script runs: restart it to load the changes.
/var/ossec/bin/wazuh-control restart > /dev/null
echo "CampusShield: integration and enrolment settings applied"
