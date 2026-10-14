# CampusShield: demo walkthrough (about 12 minutes)

A tested order for presenting the project. Every step works on the bundled lab network;
nothing touches a real network.

## Before the audience arrives (5 minutes)

```powershell
cd D:\CampusShield
.\scripts\stack.ps1 up -Automation -Siem   # Docker, backend, lab, n8n, Mailpit, Wazuh
.\scripts\demo.ps1 reset                   # lab in its normal state
cd frontend; npm run dev                   # http://localhost:3000
```

- Wait about a minute after start-up (the Wazuh agent enrols and builds its baseline).
- Open three browser tabs: CampusShield (http://localhost:3000, signed in as admin),
  Mailpit (http://127.0.0.1:8025), and the Telegram chat if a bot is configured.
- Optional, to start from an empty history: run one standard scan now so the dashboard,
  trend and report have data.

## 1. The problem and the inventory (2 min)

1. **Dashboard**: total assets, the unregistered device, critical risk, open alerts; the risk
   distribution and "what drives the risk"; the campus trend. Point out the *Live* badge.
2. **Assets**: six registered lab devices plus **CS-0007, the unknown Raspberry Pi**.
   Open it: discovered automatically, open Redis and a web panel, no owner.

## 2. Discovery and explainable risk (3 min)

1. **Network scans → New scan → Standard audit**. Show the scope guard (only
   172.25.0.0/24) and the exact nmap command; watch the live progress (~15 s).
2. Open the scan: hosts matched by MAC, the rogue flagged, risk per host.
3. Open **CS-0002 Department Website**: "Why this score" shows Apache 2.4.49 with
   CVE-2021-41773 (CVSS 9.8), every point and the formula. Settings → Risk model shows the
   whole rule set.
4. **Checklist**: mark *Host firewall enabled* as **In place** for the website; the toast
   shows the score dropping immediately (controls a scan cannot see).

## 3. Change detection and alerts through n8n (3 min)

```powershell
.\scripts\demo.ps1 open-port     # Telnet switched on at the lab PC
.\scripts\demo.ps1 scan          # the same API n8n's daily schedule uses
```

1. The scan finishes with "2 new alerts": **Port 23/tcp (telnet) opened** (high) and
   **Risk rose 44.8 → 60.8 (Medium to High)**. The sidebar shows the open-alert count.
2. **Mailpit**: the alert e-mail sent by n8n (and the Telegram message, if configured).
   Each alert shows which channels delivered it.
3. Acknowledge one alert. Then:

```powershell
.\scripts\demo.ps1 close-port
.\scripts\demo.ps1 scan
```

4. Both alerts resolve themselves ("Port closed again in scan #…", "Risk back to 44.8").

## 4. Wazuh: the rogue device attacks (2 min)

```powershell
.\scripts\demo.ps1 brute-force   # the rogue Pi guesses SSH passwords on the lab PC
```

1. Within seconds: **"Dropbear: brute force attempt on CS-0004 Lab 3 Workstation 01"**
   (high), from the Wazuh agent on the lab PC. The source is resolved to **CS-0007, an
   unregistered device**: the network scan and the host monitoring describe the same
   threat. Click *from 172.25.0.66* to jump to the rogue device.
2. Optional: `.\scripts\demo.ps1 add-user` → **"User accounts changed"** (file integrity).

## 5. The audit report (1 min)

1. **Reports → Generate report** (full). Open the PDF: cover, executive summary written
   from the data, prioritised recommendations (e.g. one "upgrade Apache" action for six
   CVEs), registers, open alerts and Wazuh events, per-device evidence, methodology and a
   sign-off block.

## Afterwards

```powershell
.\scripts\demo.ps1 reset
.\scripts\stack.ps1 down    # stops everything and frees the RAM
```

## Likely questions

- **Why not just use Nessus / OpenVAS?** They produce scan reports; CampusShield keeps a
  persistent inventory, flags unregistered devices, combines scan findings with manual
  controls and asset criticality in an explainable score, and alerts on *changes*.
- **How is the score explainable?** Every point has a rule and evidence (Settings → Risk
  model, "Why this score"); the same numbers appear in the PDF.
- **False positives from banner versions?** Stated as a limitation in the model and the
  report (vendor backports); findings name the scan that identified the version.
- **Why is Wazuh only on one host?** The doc scopes the SIEM module to a single monitored
  host; the integration (agent → manager → CampusShield) is the same for more agents.
- **Is scanning safe?** Only authorised subnets are accepted, the scanner and
  infrastructure are excluded, NSE scripts are read-only, and the lab network has no route
  to the internet.
