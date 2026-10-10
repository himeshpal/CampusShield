# CampusShield

Campus cybersecurity audit & asset management platform — B.Tech CSE final-year major project.

Nmap discovery → persistent asset inventory → unregistered-device detection → explainable risk
scoring (scan findings + asset criticality + manual checklist) → change alerts via n8n → live
dashboard and PDF audit report. Demoed against a self-contained 7-device lab network.

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 16 (App Router, TS), Tailwind 4, shadcn/ui, Recharts, TanStack Query |
| Backend | FastAPI, SQLAlchemy 2, Alembic, python-nmap, WeasyPrint |
| Data | PostgreSQL 17 (SQLite in unit tests) |
| Automation | n8n (scheduled scans, Telegram + email alerts) |
| Lab | 7 Docker containers on an isolated `172.25.0.0/24` network |

## Running it

Prerequisites: Docker Desktop (WSL2), Node.js 20+.

```powershell
copy .env.example .env          # first time only, then change the secrets
.\scripts\stack.ps1 up          # Docker + db + backend + lab
.\scripts\stack.ps1 up -Automation   # ...plus n8n (alerts / scheduled scans, Phase 7+)
cd frontend; npm install; npm run dev
```

| URL | What |
|---|---|
| http://localhost:3000 | CampusShield UI |
| http://localhost:8000/docs | API (Swagger) |
| http://localhost:5678 | n8n (only with `-Automation`) |

When you are done: `.\scripts\stack.ps1 down` (stops containers, shuts Docker/WSL to free RAM; data is kept).

### Accounts

Created on first start (change them in `.env` before a real deployment):

| Role | Email | Password | Can |
|---|---|---|---|
| Admin | admin@campusshield.local | Admin@123 | everything, incl. user management |
| Auditor | auditor@campusshield.local | Auditor@123 | read-only |

Five failed sign-ins for one email lock it for 15 minutes. Every sign-in and change is
written to the audit log (Settings → Audit log).

## Tests

```powershell
# backend: unit + API tests (in-memory SQLite) and live lab checks
docker compose exec backend pytest
docker compose exec backend pytest -m "not lab"   # skip the live lab checks

# frontend: browser end-to-end tests against the running stack
cd frontend; npm run test:e2e
```

Database schema changes go through Alembic:
`docker compose exec backend alembic revision --autogenerate -m "describe change"`,
applied automatically when the backend starts.

## Lab network (172.25.0.0/24, no internet access)

| IP | Device | Notable exposure | Registered |
|---|---|---|---|
| .10 | ERP portal (HP) | HTTP/HTTPS | yes |
| .11 | Dept website (HP) | Apache 2.4.49 — CVE-2021-41773 | yes |
| .12 | Database server (HP) | MySQL 5.7 on 3306 | yes |
| .20 | Lab desktop (Dell) | Anonymous FTP, SSH | yes |
| .30 | Wi-Fi AP (Ubiquiti) | SSH, HTTP admin | yes |
| .40 | CCTV camera (Hikvision) | Telnet, RTSP, HTTP | yes |
| .66 | Rogue device (Raspberry Pi) | Open Redis, web panel | **no** |

The backend is the only container on both networks (`172.25.0.5`); it excludes itself from scans.
Scanning is restricted to `AUTHORIZED_SUBNETS` (scope guard).

## Repository layout

```
backend/    FastAPI app (app/api, core, models, schemas, services) + tests
frontend/   Next.js app
lab/        Dockerfiles for the simulated campus devices
n8n/        exported n8n workflows
scripts/    stack control and demo helpers
docs/       report material, test-case table, screenshots
```
