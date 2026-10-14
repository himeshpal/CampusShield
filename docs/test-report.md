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

---

# Addendum: Phase 4 (risk scoring)

**Results:** backend **179 / 179** (incl. live lab), E2E **29 / 29**, 0 server errors,
0 hydration warnings; layout audit of 6 pages × 4 widths: 0 overflow, 0 console errors.

## Verification of the model

| ID | Check | Result |
|---|---|---|
| TC-20 | All 14 CVE reference entries checked against the NIST NVD API (CVSS + description) | 14/14 match |
| TC-21 | Lab device scores vs. hand calculation (6 devices, table-driven test) | All equal |
| TC-22 | Band boundaries (24.9/25, 49.9/50, 74.9/75), CVSS-to-points boundaries, component caps, 100 ceiling | Pass |
| TC-23 | Quick sweep after a deep scan keeps CVE and NSE evidence (carry-forward) | Scores unchanged, source scan shown |
| TC-24 | Editing criticality / baseline / registering a device rescores immediately | Pass (API + E2E) |
| TC-25 | Live deep scan: scores and findings attributed to that scan | 7 scores, 24 findings on scan #23 |
| TC-26 | Risk-band colours validated (dataviz palette validator, light + dark) | CVD ΔE 14.1, normal-vision ΔE 18.0 |

## Defects found and fixed during Phase 4

| ID | Defect | Root cause | Fix |
|---|---|---|---|
| D-7 | Risk scores were always one scan behind; deep-scan findings were never scored | Scoring runs while the scan is still "running", and evidence was read only from completed scans | Scoring explicitly includes the scan being finished (`current_scan_id`); regression test reproduces the real sequence |
| D-8 | HTTPS (443) scored as unencrypted HTTP and shown as `443/http` | python-nmap drops nmap's `tunnel="ssl"` attribute | Parser reads the tunnel from the XML and reports `ssl/http` |
| D-9 | High vs. Critical colours indistinguishable (ΔE 7.5; colour-blind ΔE 5-6) | Palette chosen by eye | Re-stepped to a validated status palette; text uses separate ink shades (WCAG ≥ 4.5:1) |
| D-10 | Amber/orange used as text colour (contrast 1.6-2.6:1) | Same tokens used for marks and text | `-ink` text tokens; 21 usages migrated |
| D-11 | "Not confirmed" checklist items shown with a green (= "fine") dot | Low severity mapped to the Low-risk colour | Low severity is neutral grey; green reserved for the Low band |

## Known limitations (risk model)

- CVE matching uses service banners: distribution backports are invisible, so a matched
  CVE can be a false positive and should be confirmed on the host (stated in the UI).
- Only TCP services in the scan profile are assessed.
- Until the checklist (Phase 5) is filled in, every asset carries the full 20 points
  for unconfirmed controls; they are 42 % of all campus risk points in the demo data.

---

# Addendum: Phase 5 (security checklist)

**Results:** backend **194 / 194** (incl. live lab), E2E **34 / 34**, 0 server errors,
0 hydration warnings, 0 console errors; checklist page fits a 390 px phone.

| ID | Check | Result |
|---|---|---|
| TC-27 | Answering a control rescores the asset and reports before/after | Pass (API + E2E toast) |
| TC-28 | "In place" and "Not applicable" add no points; "Missing" costs as much as unknown | Pass |
| TC-29 | Bulk answers: one rescore, one audit entry; duplicate keys rejected | Pass |
| TC-30 | Re-saving an identical answer creates no audit entry or new score | Pass |
| TC-31 | Unregistered device, unknown control, bad status, 501-char evidence | 409 / 404 / 422 / 422 |
| TC-32 | Auditor can read answers and evidence but cannot change them | Pass (403 + read-only editor) |
| TC-33 | Editor usable on short screens (600 px and 720 px tall) | Pass after fix D-13 |

## Defects found and fixed during Phase 5

| ID | Defect | Root cause | Fix |
|---|---|---|---|
| D-12 | Confirming the first control did not change the score (67.8 → 67.8) | Risk model v1 capped controls at 20 while six controls x 4 = 24 | Cap is 4 x number of controls (model v2, rescored on start); regression test checks every confirmation lowers the score |
| D-13 | On a 720 px-tall window the checklist editor's Save button was off-screen and unreachable | Fixed-position popover taller than the space below the cell | Popover limited to the measured available height with internal scroll and 12 px collision padding |
| D-14 | Hand-checked score 73 x 1.15 = 83.95 shown as 83.9 | Binary floating-point rounding | Exact decimal arithmetic with round-half-up |

**Observation (environment, not a defect):** the E2E suite runs ~2.5x slower than in
earlier phases on this laptop (API endpoints still answer in < 50 ms). Windows Defender
real-time scanning of the Next.js dev build and other running applications are the
likely cause; a Defender exclusion for the project folder is the usual remedy.

---

# Addendum: Phase 6 (dashboard and PDF report)

**Results:** backend **211 / 211** (incl. live lab), E2E **38 / 38**, 0 console errors;
dashboard and reports pages have no horizontal overflow at 390, 768 and 1280 px.
A full report of the lab (7 devices) is 17 A4 pages / ~285 KB and renders in ~2.3 s;
"summary only" is 10 pages.

| ID | Check | Result |
|---|---|---|
| TC-34 | Report headline numbers equal the dashboard's (average, band counts) | Pass |
| TC-35 | All six Apache 2.4.49 CVEs become one critical "upgrade" action; points capped like the score | Pass |
| TC-36 | Same service on several devices is one action listing each device and port | Pass |
| TC-37 | Unregistered device gets "identify / register" and no checklist actions | Pass |
| TC-38 | PDF served inline or as attachment, `Cache-Control: private, no-store`, dated file name | Pass |
| TC-39 | Report routes: 401 without login; auditor may generate (201) but not delete (403) | Pass |
| TC-40 | Generating and deleting are written to the audit log | Pass |
| TC-41 | Report before any scan renders (explains that nothing was assessed) | Pass |
| TC-42 | Campus trend groups scores written within 60 s into one point | Pass |
| TC-43 | Visual check of every PDF page: running header, page x of y, table of contents page numbers, no clipped tables | Pass after D-16 |

## Defects found and fixed during Phase 6

| ID | Defect | Root cause | Fix |
|---|---|---|---|
| D-15 | First draft of the recommendations listed six separate "upgrade Apache" actions, and the "confirm controls" action included the unregistered device | Grouping by CVE id instead of software; checklist gaps not filtered by status | Grouped by software version with all CVE ids in the reason; checklist actions only for registered devices; points capped per score component |
| D-16 | PDF running header (report title) and footer (report number) were empty | WeasyPrint only takes `string-set` from rendered elements; the source spans were `display: none` | Strings taken from the visible cover title and report number |
| D-17 | Next.js "blocking prerender" error on /reports | Date-based title placeholder computed while prerendering | Placeholder computed only while the dialog is open |


---

# Addendum: Phase 7 (change alerts and n8n)

**Results:** backend **230 / 230** (incl. live lab), E2E **41 / 41** (the alert test drives
the real lab: Telnet switched on, scan, acknowledge, Telnet off, scan, auto-resolved),
0 hydration errors after fix D-19, Alerts page has no overflow at 390 px.

**Live pipeline check (lab):** Telnet opened on the lab PC → standard scan #30 raised
"port opened" (high) and "risk rose 44.8 → 60.8, Medium to High"; n8n delivered one email
to Mailpit and reported Telegram as not set up; both results were stored on the alerts.
Telnet closed + Wi-Fi AP stopped → quick scan #31 resolved the port alert and raised
"Wi-Fi AP Block A did not respond"; AP back → scan #32 resolved it and the risk alert.
A scheduled scan triggered by n8n (scan #29, shown as "n8n") raised no false alarms after
a standard audit.

| ID | Check | Result |
|---|---|---|
| TC-44 | First scan: only the rogue device is reported (registered devices have no earlier scan to differ from) | Pass |
| TC-45 | Identical rescan raises nothing; each condition is reported once | Pass |
| TC-46 | Port opened → closed: alert resolves itself, no duplicate "closed" alert | Pass |
| TC-47 | Quick ↔ standard mixes: no opened/closed claims for ports one scan did not probe | Pass |
| TC-48 | Missing host reported once, resolves when it answers; a single-IP scan reports nothing missing | Pass |
| TC-49 | Different MAC on a registered IP: critical, names the registered asset | Pass |
| TC-50 | Risk rise names the components that grew and resolves when the score falls back | Pass |
| TC-51 | Below-threshold alerts kept but not pushed; n8n missing or crashing never fails a scan | Pass |
| TC-52 | Service-key endpoints: 401 without or with a wrong key; scheduled scan recorded as n8n | Pass |
| TC-53 | n8n webhook rejects a request without the shared secret (401) | Pass (live) |
| TC-54 | Auditor reads alerts but cannot acknowledge, resolve or change settings (403) | Pass |

## Defects found and fixed during Phase 7

| ID | Defect | Root cause | Fix |
|---|---|---|---|
| D-18 | After 25+ quick sweeps the rogue device dropped from 84 to 67; CVE matches could be lost the same way | Model v2 searched only the last 20 observations for version / NSE evidence | Model v3: evidence carried while the port stays open (stops at the first scan that probed it and found it closed), safety bound 500; regression tests for both directions |
| D-19 | Hydration error on /alerts and /dashboard | Sidebar badge and page share the alert-summary query; the sidebar's fetch could finish before the page hydrated | Summary data withheld until hydration (`useHydrated`) |
| D-20 | n8n restart loop on first start | `import:workflow --activeState` is not allowed in single-instance n8n 2.x | Import, then `publish:workflow` for each workflow |

**Environment note:** Docker Desktop stopped once during this phase with "WSL update
required" while Windows updated WSL to 3.0.3 in the background; `stack.ps1 down` / `up`
was enough to recover.

---

# Addendum: Phase 8 (Wazuh, polish and final system test)

**Final results (all phases):** backend **300 / 300** (incl. live lab checks with the Wazuh
manager running), E2E **43 / 43**, lint / format / type-check clean, `next build` succeeds
(14 routes). Layout audit: 14 pages × 4 widths (1440, 1280, 768, 390 px) × light and dark
mode = 112 page views, **0 console errors, 0 page errors**, 0 horizontal overflow after
fix D-23. Access-control sweep (`test_access_control.py`, generated from the OpenAPI
schema): every one of the API operations returns 401 without credentials, every admin
write returns 403 for the auditor, and the machine endpoints refuse a user session.

**Footprint (whole stack incl. n8n, Mailpit and the Wazuh manager):** about 1.2 GB RAM;
Wazuh manager 282 MB, n8n 410 MB, backend 300 MB, lab devices ≤ 60 MB each.

**Live SIEM check:** the rogue Raspberry Pi (.66) tried 10 SSH passwords on the lab PC →
Wazuh rule 51007 "Dropbear: brute force attempt" (level 10) → CampusShield alert
"Dropbear: brute force attempt on CS-0004 Lab 3 Workstation 01" (high) with the source
resolved to "CS-0007, an unregistered device"; e-mailed through n8n. The nine individual
bad-password events (rule 51003, level 5) became one low alert with "9 events". A new
account on the lab PC → "User accounts changed" (local rule 100100, high) listing
/etc/passwd, /etc/shadow and /etc/group; a file dropped on the anonymous FTP share →
"File uploaded to the anonymous FTP share" (local rule 100101, medium).

| ID | Check | Result |
|---|---|---|
| TC-55 | Wazuh alert tied to the asset of the agent's IP; attack source resolved in the inventory | Pass |
| TC-56 | Rule levels map to severities (5 low, 7 medium, 10 high, 12+ critical) | Pass |
| TC-57 | Repeats of a rule on a host within 15 min merged with a counter; not pushed again | Pass |
| TC-58 | File-integrity events on several files merged into one alert listing every path | Pass |
| TC-59 | Agent with an unknown address still produces an alert (no asset) | Pass |
| TC-60 | Wazuh endpoint: 401 without / with a wrong service key, 401 with an admin session, 422 for non-Wazuh JSON | Pass |
| TC-61 | Open alerts and Wazuh events listed in the PDF report and on the asset page | Pass |
| TC-62 | Agent re-enrols automatically after the manager or the lab PC is re-created | Pass (live) |

## Defects found and fixed during Phase 8

| ID | Defect | Root cause | Fix |
|---|---|---|---|
| D-21 | Dropbear log lines matched no Wazuh decoder | busybox syslogd writes a facility field ("authpriv.warn") that the syslog pre-decoder does not expect | rsyslog with the traditional file format on the lab PC |
| D-22 | Adding a user raised no alert until the hourly scan | Wazuh real-time FIM watches directories, not single files | Watch /etc in real time, restricted to passwd / shadow / group |
| D-23 | Settings page 9 px wider than a 390 px phone | Fifth tab (Notifications) made the tab bar too wide | Tab bar scrolls inside itself |
| D-24 | The manager's own CIS assessment arrived as campus alerts | SCA / rootcheck / FIM enabled on the manager by default | Disabled on the manager (infrastructure, not a monitored campus device) |

**Not a defect (recorded to save time later):** intermittent 401s seen while testing with
curl were caused by the Git Bash setting `MSYS_NO_PATHCONV=1`, which also disables the
translation of the cookie-file path, so curl sent no valid cookie. Confirmed by sending the
same cookie with and without the setting (401 / 200).
