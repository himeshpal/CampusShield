#!/bin/sh
# n8n entrypoint for CampusShield: load the workflows and the SMTP credential from this
# repository on every start (the repo is the source of truth), then run n8n.
# Secrets come from the environment (.env), never from the exported JSON files.
set -e

node -e '
const e = process.env;
const smtp = {
  id: "csSmtpCredential",
  name: "CampusShield SMTP",
  type: "smtp",
  data: {
    host: e.SMTP_HOST || "mailpit",
    port: Number(e.SMTP_PORT || 1025),
    secure: e.SMTP_SECURE === "true",
    user: e.SMTP_USER || "",
    password: e.SMTP_PASSWORD || "",
  },
};
require("fs").writeFileSync("/tmp/campusshield-credentials.json", JSON.stringify([smtp]));
'
n8n import:credentials --input=/tmp/campusshield-credentials.json
rm -f /tmp/campusshield-credentials.json
n8n import:workflow --separate --input=/campusshield/workflows
# importing deactivates; publishing makes the trigger (webhook, schedule) live again
for id in csAlertsWorkflow csScheduledScans; do
  n8n publish:workflow --id="$id"
done

exec n8n start
