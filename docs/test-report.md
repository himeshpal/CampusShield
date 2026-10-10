# CampusShield: System Test Report (Phases 1-3)

**Date:** 10 Oct 2026 · **Build:** after Phase 3 (`3176005`) + test-pass fixes
**Scope:** authentication & audit log, Nmap discovery, asset inventory & matching, UI
**Environment:** Windows 11, Docker Desktop (WSL2, 4 GB cap), 7-device lab on 172.25.0.0/24,
Next.js 16 dev server, Chromium (Playwright 1.64)

## 1. Summary

| Area | Result |
|---|---|
| Backend automated tests (pytest) | **110 / 110 passed** (incl. 2 live-lab tests) |
| Browser end-to-end tests (Playwright) | **23 / 23 passed**, 0 server errors, 0 hydration warnings |
| Lint / format / type-check / production build | Clean |
| UI layout audit | 11 pages × 4 widths (1440, 1280, 768, 390 px): **0 overflow, 0 console errors** |
| Access-control sweep | All 21 API routes: 401 without login, 403 for auditor writes |
| Defects found during this pass | **6 found, 6 fixed** (1 security) |

## 2. Test cases (manual / exploratory, against the live lab)

| ID | Scenario | Expected | Actual | Result |
|---|---|---|---|---|
| TC-01 | Every API route without a session | 401 (except health, login) | 401 on all 19 protected routes | Pass |
| TC-02 | Auditor calls every write route | 403 | 403 on all 8 write routes | Pass |
| TC-03 | Replay a session token after logout | 401 | **200 before fix**, 401 after | Fixed (D-1) |
| TC-04 | Session cookie flags | HttpOnly, SameSite | HttpOnly, SameSite=Lax (Secure is a config switch for HTTPS) | Pass |
| TC-05 | SQL-injection strings in search and login | No effect, no error | 0 rows / 422, tables intact | Pass |
| TC-06 | Stored XSS in asset name and notes | Rendered as text | Rendered as text, no script executed | Pass |
| TC-07 | 1 MB and 20 MB request bodies, broken JSON | Rejected cleanly | 422 / 404 in ~0.2 s, backend stable | Pass |
| TC-08 | Security headers on pages and API | Present | **Missing before fix**, present after | Fixed (D-4) |
| TC-09 | Deep scan of the lab | 7 hosts, OS, NSE results stored | 125 s; 7 hosts, 13 ports, OS for all, ftp-anon + redis-info findings | Pass |
| TC-10 | Cancel a running deep scan | Status cancelled, nmap killed | Cancelled, 0 nmap processes; latency **3.4-5.5 s before fix**, 0.6-1.0 s after | Fixed (D-5) |
| TC-11 | Restart backend during a scan | Scan marked interrupted, no orphan process | `failed / Interrupted`, 0 nmap processes, session still valid | Pass |
| TC-12 | DHCP: lab PC's MAC appears on a new IP | Same asset, IP updated | CS-0004 matched by MAC, IP .20 → .21 → .20, no duplicate | Pass |
| TC-13 | IP conflict: other MAC on the DB server's IP | Flagged, new unregistered asset | `ip_conflict`, new unregistered asset; real DB not marked seen | Pass |
| TC-14 | Rogue device seen across many scans | One asset, history grows | CS-0007 matched by MAC in 7+ scans, never duplicated | Pass |
| TC-15 | Asset pages on a phone (390 px) | No horizontal scroll | **193 px overflow before fix**, 0 after | Fixed (D-2) |
| TC-16 | Login page console | No errors | **401 error logged before fix**, clean after | Fixed (D-3) |
| TC-17 | Cold restart (Docker + WSL shut down) | Clean start, no duplicate seed data | Healthy in 194 s (Docker boot); migrations no-op; 2 users, 6 controls, 7 assets | Pass |
| TC-18 | API response time | Interactive | Median 3 ms, p95 25 ms via 127.0.0.1 | Pass (see D-6) |
| TC-19 | Resource use, whole stack idle | Fits 4 GB cap | ~255 MB total (backend 121 MB, Postgres 38 MB) | Pass |

## 3. Defects found and fixed

| ID | Defect | Severity | Root cause | Fix | Regression test |
|---|---|---|---|---|---|
| D-1 | A session token stayed valid after logout (up to 8 h) | **High (security)** | Stateless JWT; logout only deleted the cookie | `users.token_version` stored in every token; logout increments it, revoking all earlier tokens of that user | `test_token_copied_before_logout_is_revoked` |
| D-2 | Asset detail page 193 px wider than a phone screen | Medium | CSS grid items default to `min-width: auto`, so tables widened the column | `min-w-0` on the grid columns | `asset detail fits a phone screen` (E2E) |
| D-3 | Login page logged a 401 error in the console | Low | "Already signed in?" check used `/auth/me`, which 401s when signed out | New `/auth/session` endpoint that returns `null` instead | `login page loads without console errors` (E2E), `test_session_endpoint_never_401s` |
| D-4 | No browser security headers | Medium (hardening) | Not configured | X-Frame-Options, CSP `frame-ancestors 'none'`, nosniff, Referrer-Policy on pages (Next.js) **and** API (FastAPI middleware; Next does not add them to proxied responses) | `security headers on pages and proxied API responses` (E2E), `test_security_headers_on_every_response` |
| D-5 | Cancel took 3-5 s | Low | Cancel was only checked when nmap printed a line | Line reader wakes every 0.5 s (`select` with timeout) | live-lab cancel test |
| D-6 | API ~210 ms slower via `localhost` | Low (docs) | Windows tries IPv6 `::1` first; ports are published on 127.0.0.1 | Docs and scripts use `127.0.0.1` (the app itself already did) | n/a |

## 4. Known limitations / open items

- **Deep-scan progress plateau:** the bar can sit at ~73 % for about a minute while nmap
  waits on slow web panels during version detection; nmap reports no progress then.
- **Sign-out is global:** because of D-1's fix, signing out ends that user's sessions on
  every device.
- **Cookie `Secure` flag** is off because the lab runs over plain HTTP (`COOKIE_SECURE`).
- **No full script Content-Security-Policy** (Next.js dev mode needs inline scripts);
  clickjacking protection is in place.
- **Cold start ~3 min** is dominated by Docker Desktop/WSL booting, not the application.
