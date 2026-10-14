# CampusShield

Campus cybersecurity audit & asset management platform — B.Tech CSE final-year major project.

Nmap discovery → persistent asset inventory → unregistered-device detection → explainable risk
scoring (scan findings + asset criticality + manual checklist) → change alerts via n8n →
Wazuh host monitoring → live dashboard and PDF audit report. Demoed against a self-contained
7-device lab network (walkthrough: [docs/demo-script.md](docs/demo-script.md)).

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 16 (App Router, TS), Tailwind 4, shadcn/ui, Recharts, TanStack Query |
| Backend | FastAPI, SQLAlchemy 2, Alembic, python-nmap, WeasyPrint |
| Data | PostgreSQL 17 (SQLite in unit tests) |
| Automation | n8n (scheduled scans, Telegram + email alerts), Mailpit (demo inbox) |
| SIEM | Wazuh 4.14 manager + one agent (on the lab PC), alerts forwarded to CampusShield |
| Lab | 7 Docker containers on an isolated `172.25.0.0/24` network |

## Running it

Prerequisites: Docker Desktop (WSL2), Node.js 20+.

```powershell
copy .env.example .env          # first time only, then change the secrets
.\scripts\stack.ps1 up          # Docker + db + backend + lab
.\scripts\stack.ps1 up -Automation   # ...plus n8n + Mailpit (alert delivery, scheduled scans)
.\scripts\stack.ps1 up -Automation -Siem   # ...plus the Wazuh manager (~1 GB RAM more)
cd frontend; npm install; npm run dev
```

| URL | What |
|---|---|
| http://localhost:3000 | CampusShield UI |
| http://127.0.0.1:8000/docs | API (Swagger) |
| http://127.0.0.1:5678 | n8n (only with `-Automation`; first visit asks you to create an n8n owner account) |
| http://127.0.0.1:8025 | Mailpit: the demo inbox that receives alert e-mails (only with `-Automation`) |

When you are done: `.\scripts\stack.ps1 down` (stops containers, shuts Docker/WSL to free RAM; data is kept).

### Accounts

Created on first start (change them in `.env` before a real deployment):

| Role | Email | Password | Can |
|---|---|---|---|
| Admin | admin@campusshield.local | Admin@123 | everything, incl. user management |
| Auditor | auditor@campusshield.local | Auditor@123 | read-only |

Five failed sign-ins for one email lock it for 15 minutes. Every sign-in and change is
written to the audit log (Settings → Audit log).

## Scanning

| Profile | Measured on the lab | nmap flags (plus `-n`, target, exclusions) |
|---|---|---|
| Quick sweep | ~2 s | `-sS -T4` on ~35 key campus ports |
| Standard audit | ~15 s | `-sS -sV --version-light -T4` on 1-1024 + campus extras |
| Deep inspection | ~2 min | standard + `-O` + safe NSE scripts (ftp-anon, redis-info, ssl-cert, ...) |

Explicit port lists are used because nmap's "top 1000" misses campus services such as
Redis (6379) and RTSP (8554). Only targets inside `AUTHORIZED_SUBNETS` are accepted; the
scanner's own address and `SCAN_EXCLUDE` are never scanned. One scan runs at a time,
with live progress (nmap runs on a pseudo-terminal so it reports its own percentages).

## Inventory and matching

After every scan each live host is tied to a persistent asset record:

1. **MAC address** match (survives DHCP; the asset's IP is updated)
2. **IP address** match, only when no MAC contradicts it
3. Same IP but a **different MAC** → `ip_conflict`: treated as a new device
4. No match → a new asset with status **unregistered** (never silently dropped)

Unregistered devices keep their history (first/last seen, every observation) until an
admin registers or retires them. Each asset has an expected port baseline; open ports
outside it are highlighted (input for risk scoring). With `DEMO_DATA=true` the six
legitimate lab devices are pre-registered, so the Raspberry Pi is the one unknown device.

## Risk scoring

```
score = min(100, (exposure + vulnerabilities + drift + controls + inventory) x multiplier)
```

| Component | Max | From |
|---|---|---|
| Network exposure | 40 | weight per reachable service (Telnet 15, RDP/SMB 12, FTP/DBs/Redis 10, plain HTTP 4, ...) |
| Known vulnerabilities | 40 | CVE matches on product+version (CVSS ≥9 → 30, ≥7 → 20, ≥4 → 10), end-of-life software, NSE findings |
| Unexpected open ports | 10 | 5 per port outside the asset's baseline |
| Missing controls | 24 | 4 per checklist control answered "missing" or not confirmed (6 controls) |
| Inventory status | 20 | unregistered device |

The multiplier comes from the asset's criticality (4-12 → 0.8x-1.5x). Bands: Low <25,
Medium 25-49, High 50-74, Critical ≥75. Every stored score keeps a full breakdown, shown
as "Why this score" on each asset. The whole model, including the 14-entry CVE
reference list (CVSS verified against NIST NVD), is defined in
`backend/app/services/risk/rules.py` and published in Settings → Risk model. Versions
and NSE findings are carried forward from earlier scans while a port stays open (the search stops at the
first scan that probed the port and found it closed), so any number of quick sweeps
does not "forget" a known CVE.

## Security checklist

Controls a network scan cannot verify (firewall, antivirus/EDR, disk encryption, MFA,
patch policy, default credentials) are recorded per registered asset as **In place**,
**Missing**, **Not applicable** or **Not confirmed**, with an optional evidence note and
who/when. Saving an answer rescores the asset immediately and is written to the audit
log. Unregistered devices have no owner and must be registered before they are assessed.

## Dashboard and audit report

The dashboard refreshes itself every 30 seconds (and when the tab regains focus), so a scan
or checklist answer recorded elsewhere shows up without reloading. Besides totals and the
risk distribution it shows the **campus risk trend** (average score after every scan and
checklist update) and an **audit status** card: latest scan, checklist completion, latest report.

**Reports** generates a PDF with WeasyPrint from the live data (about 2-3 s for the lab).
Any signed-in user can generate one; only admins can delete one, and both are audit-logged.
Each PDF is a point-in-time snapshot stored in the database with its SHA-256, so the history
can be compared over time. Contents:

1. Executive summary: headline numbers, findings written from the data, band distribution,
   risk drivers, campus trend
2. Priority recommendations: rule-based actions per finding (e.g. all CVEs of one Apache
   version become one upgrade), merged across devices, ordered by priority and risk points
3. Asset risk register, 4. vulnerabilities and misconfigurations, 5. unregistered devices,
   6. checklist coverage and recorded gaps
7. Per-device evidence: ports, score formula, every finding (optional: "Summary only" skips it)
8. Scope, risk model, limitations and a sign-off block

The cover shows `INSTITUTION_NAME` from `.env`; times are printed in `REPORT_TIMEZONE`
(default Asia/Kolkata). Templates: `backend/app/services/report/templates/`.

## Change alerts and n8n

Every completed scan is compared with what was known before it
(`backend/app/services/alerts/detect.py`). Each alert is a *difference*, so a condition is
reported once, and it resolves itself when the condition clears:

| Alert | Raised when | Severity | Resolves itself when |
|---|---|---|---|
| New device | an unknown device answers (or a different MAC answers on a registered IP) | high (critical for an IP conflict) | the device is registered or retired |
| Port opened | a port is open that the previous scan probed and found closed | by service weight (Telnet high, Redis medium, ...); info for a baseline port | the port is closed again |
| Port closed | a port the previous scan saw open is closed, and this scan probed it | info | (informational) |
| Not responding | a registered device seen by the last scan of its address is missing | medium (high at criticality 10+/12) | the device answers again |
| Risk rose | a score rises 10+ points or into a higher band | the new band | the score falls back |

Port changes are only claimed where *both* scans probed the port (a quick sweep covers ~35
ports, a standard audit 1-1024 plus campus services), so mixing profiles gives no false
alarms. Admins acknowledge or resolve alerts (with a note); everything is audit-logged.

**Delivery.** Alerts at or above a threshold (Settings → Notifications, default medium) are
POSTed to an n8n webhook with a shared-secret header. The n8n workflow
(`n8n/workflows/campusshield-alerts.json`) checks the secret, formats the message, sends it
by **email** and **Telegram**, and reports each channel's result back to the backend
(`POST /api/v1/automation/delivery`, service API key), which shows it on every alert.
A second workflow runs a **scheduled scan** (daily 07:00 by default) through
`POST /api/v1/automation/scans`. Both workflows and the SMTP credential are loaded from
the repository every time n8n starts (`n8n/start.sh`).

- **Email:** goes to the bundled Mailpit inbox (http://127.0.0.1:8025) unless `SMTP_*` in
  `.env` points at a real server (e.g. Gmail: `smtp.gmail.com`, port 465, secure, app password).
- **Telegram:** create a bot with @BotFather, send it a message, read your chat id from
  `https://api.telegram.org/bot<token>/getUpdates`, then set `TELEGRAM_BOT_TOKEN` and
  `TELEGRAM_CHAT_ID` in `.env` and restart n8n (`docker compose --profile automation up -d n8n`).
- **Test the whole path:** Settings → Notifications → *Send test alert*.

**Demo script** (needs the stack with `-Automation`):

```powershell
.\scripts\demo.ps1 open-port    # Telnet on the lab PC -> "port opened" + "risk rose"
.\scripts\demo.ps1 scan         # scan the way n8n does (-Profile quick|standard|deep)
.\scripts\demo.ps1 close-port   # next scan resolves both alerts
.\scripts\demo.ps1 unplug       # Wi-Fi AP off -> "did not respond"; plug brings it back
.\scripts\demo.ps1 reset        # undo every change
```

## Wazuh host monitoring (SIEM)

The doc's final module: Wazuh on **one monitored host**. The lab PC (`lab-pc-01`, .20)
runs a Wazuh agent (`lab/lab-pc/`) that reads its SSH log and watches file integrity in
real time (account files and the anonymous FTP share). The Wazuh **manager** (`wazuh/`,
172.25.0.4, compose profile `siem`) analyses the events with the standard ruleset plus
two CampusShield rules, and a custom integration (`wazuh/custom-campusshield`) POSTs every
alert of level 5+ to `POST /api/v1/automation/wazuh` (service API key).

CampusShield is the dashboard: no Wazuh indexer or dashboard is run, which keeps the
footprint to the manager (~0.5-1 GB RAM) on a 16 GB laptop. Each Wazuh alert becomes a
CampusShield alert of type *Host event (Wazuh)*:

- tied to the asset the agent registered with (by IP), and the attack's **source IP** is
  looked up in the inventory too, e.g. *"Source 172.25.0.66: CS-0007, an unregistered
  device"*: the scan's rogue device is now seen attacking the lab PC;
- severity from the rule level (5-6 low, 7-9 medium, 10-11 high, 12+ critical);
- repeats of the same rule on the same host within 15 minutes are merged with a counter
  (nine bad passwords = one alert, "9 events"), so the channels are not flooded;
- delivered by email / Telegram through the same n8n pipeline and threshold as scan alerts,
  and listed in the PDF report and on the asset's page.

```powershell
.\scripts\stack.ps1 up -Automation -Siem
# wait ~1 minute after start: the agent enrols and builds its file-integrity baseline
.\scripts\demo.ps1 brute-force   # rogue Pi guesses SSH passwords -> "Dropbear: brute force attempt" (high)
.\scripts\demo.ps1 add-user      # new account on the lab PC     -> "User accounts changed" (high)
.\scripts\demo.ps1 ftp-upload    # file on the anonymous share   -> "File uploaded to the anonymous FTP share"
.\scripts\demo.ps1 reset
```

The manager keeps no volume: on restart the agent enrols again, and the history stays in
CampusShield. Settings → Notifications shows the last event received from Wazuh.

## Tests

```powershell
# backend: unit + API tests (in-memory SQLite) and live lab checks
docker compose exec backend pytest
docker compose exec backend pytest -m "not lab"   # skip the live lab checks

# frontend: browser end-to-end tests against the running stack
cd frontend; npm run test:e2e
```

`tests/test_access_control.py` sweeps every API operation from the OpenAPI schema: each
needs a session (or the service key for `/automation/*`), and every write needs the admin
role except signing out and generating reports, so a new endpoint cannot ship unprotected.

Database schema changes go through Alembic:
`docker compose exec backend alembic revision --autogenerate -m "describe change"`,
applied automatically when the backend starts.

## Lab network (172.25.0.0/24, no internet access)

| IP | Device | Notable exposure | Registered |
|---|---|---|---|
| .10 | ERP portal (HP) | HTTP/HTTPS | yes |
| .11 | Dept website (HP) | Apache 2.4.49 — CVE-2021-41773 | yes |
| .12 | Database server (HP) | MySQL 5.7 on 3306 | yes |
| .20 | Lab desktop (Dell), Wazuh-monitored host | Anonymous FTP, SSH | yes |
| .30 | Wi-Fi AP (Ubiquiti) | SSH, HTTP admin | yes |
| .40 | CCTV camera (Hikvision) | Telnet, RTSP, HTTP | yes |
| .66 | Rogue device (Raspberry Pi) | Open Redis, web panel | **no** |

Infrastructure, never scanned (`SCAN_EXCLUDE`): .1 Docker gateway, .4 Wazuh manager.
The backend is the only container on both networks (`172.25.0.5`); it excludes itself from scans.
Scanning is restricted to `AUTHORIZED_SUBNETS` (scope guard).

## Repository layout

```
backend/    FastAPI app (app/api, core, models, schemas, services) + tests
frontend/   Next.js app
lab/        Dockerfiles for the simulated campus devices
n8n/        n8n workflows + start script (loaded on every n8n start)
wazuh/      Wazuh manager additions: init script, integration, local rules
scripts/    stack control and demo helpers
docs/       report material, test-case table, screenshots
```
