# Defensive security assessment

Local copy only, synthetic data and test accounts. Penetration-testing activity was limited to **passive inspection, source/configuration review and normal application actions** (no active scanning, fuzzing of production systems or exploitation).

## 1. Attack surface of the two workflows

| Route | Method | Who should use it | Data read / written | Protection observed |
|---|---|---|---|---|
| `/login/` | GET/POST | everyone | credentials → session | CSRF token, Django auth |
| `/requisition/hod/` | GET | HOD | pending requisitions of own dept | login only |
| `/requisition/{pk}/hod-approval/` | GET/POST | HOD of initiator's dept | Requisition.status, approver, reasons, Notification | login + queryset filter (**Admin bypass — F4**) |
| `/requisition/admin/` | GET | Admin | authorized requisitions | login only (no role check — any user sees the queue) |
| `/requisition/{pk}/issue/` | GET/POST | Admin | line `quantity_issued`, Item.quantity_total, Transaction, Requisition.status, Notification | **login only — F3** |
| `/requisition/{pk}/` | GET | initiator / HOD dept / Admin | requisition + lines | queryset by role |
| `/requisition/{pk}/cancel/` | **GET** | initiator | Requisition.status | login; state change on GET (**F19**) |
| `/requisition/api/create/`, `/{pk}/api/update/` | POST (JSON) | initiator | Requisition, lines, Notification | login + CSRF |
| `/requisition/api/items/`, `/inventory/api/item-details/`, `/api/notifications/` | GET | logged-in users | item stock, notifications | login |

## 2. Access matrix and automated checks (Playwright — `tests/team/e2e/security/access-matrix.spec.ts`)

Expected decision per role (from the README separation of duties, test basis A1):

| Action | HOD (same dept) | HOD (other dept) | Admin | Initiator | Anonymous |
|---|---|---|---|---|---|
| Open/submit approval of a pending requisition | allow | deny | **deny** | deny | → login |
| Open/submit issue of an authorized requisition | **deny** | deny | allow | deny | → login |

Results of the automated checks (`reports/security/access_matrix.json`, screenshots `reports/security/SEC-0x.png`):

| Check | Role | Action | Expected | Observed | Evidence | Verdict |
|---|---|---|---|---|---|---|
| SEC-01 | hod_it | open approval of own-dept pending requisition | allow | allow (200) | SEC-01.png | ✔ |
| SEC-02 | hod_it | open approval of HR requisition | deny | deny (404) | SEC-02.png | ✔ |
| SEC-03 | hod_it | open Issue Items screen | deny | **allow (200)** | SEC-03.png | ✘ F3 #2 |
| SEC-04 | admin | open Issue Items screen | allow | allow (200) | SEC-04.png | ✔ |
| SEC-05 | admin | open HOD approval screen | deny | **allow (200)** | SEC-05.png | ✘ F4 #3 |
| SEC-06 | user_it_1 (initiator) | open Issue Items screen | deny | **allow (200)** | SEC-06.png | ✘ F3 #2 |
| SEC-07 | anonymous | open Issue Items screen | deny | deny (redirect to /login/) | SEC-07.png | ✔ |
| SEC-08 | hod_it | submit an issue of 3 units | deny | **allow** — DB: status issued, issuer hod_it, stock 7 | DB snapshot in JSON | ✘ F3 #2 |

8 access decisions across HOD and Admin (plus initiator/anonymous); 4 as expected, 4 violations. The violations are encoded with `test.fail` so the suite stays green while the defect is open and turns red once it is fixed (marker removed in the fix PR).

## 3. OWASP ZAP 2.16.1 — passive scan during both workflows
`scripts/team/zap_passive.sh`: ZAP daemon as proxy, Playwright (UC-01, UC-03, UC-04 and the access matrix — 23 tests passed) sent **361 messages** through it; Chromium's loopback bypass was disabled (`--proxy-bypass-list=<-loopback>`). Only passive rules ran. Reports: `reports/security/zap/zap-report.html`, `zap-alerts.json`.

| Risk | Alert | Count | Our assessment |
|---|---|---|---|
| Medium | Content Security Policy header not set | 19 | **Valid.** No CSP configured (`settings.py`, no middleware). Any future XSS would run unrestricted. |
| Medium | Cross-Domain Misconfiguration | 4 | Response of the **CDN** (`cdn.jsdelivr.net`, `Access-Control-Allow-Origin: *`) — normal for a public CDN, not the application. Informational for us. |
| Low | Server leaks version (`WSGIServer/0.2 CPython/3.12.16`) | 24 | Dev server header — would disappear behind a production server; DEBUG/dev setup (see C3). |
| Low | Cookie without HttpOnly | 17 | Only `csrftoken` — by design (Django lets JS read it for AJAX). `sessionid` **is** HttpOnly (C1). Not a defect. |
| Low | X-Content-Type-Options missing | 2 | Only on `/static/` files served by the dev server; application pages send `nosniff` (C2). |
| Low | Cross-domain JavaScript inclusion | 16 | Bootstrap loaded from jsDelivr **without Subresource Integrity** (`templates/base.html` lines 9, 11, 62; 0 `integrity=` attributes) — valid: a compromised CDN could inject script. |
| Info | Suspicious comments, modern web app, retrieved from cache, user-controllable attribute (`items-MAX_NUM_FORMS` echoed into a hidden input) | 53 | Reviewed: the echoed value is HTML-escaped by Django templates — no XSS. |

## 4. Security controls reviewed (observation corroborated in source/configuration)

| # | Control | Observation (evidence) | Source / config corroboration | Verdict |
|---|---|---|---|---|
| C1 | **Session cookie attributes** | `sessionid`: HttpOnly ✔, SameSite=Lax ✔, **Secure ✘**, lifetime 14 days (`reports/security/cookie_check.txt`, ZAP) | `settings.py` has no `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE`/`SESSION_COOKIE_AGE` → Django defaults | partly effective — Secure must be set when served over HTTPS |
| C2 | Security headers | `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `COOP` present; **no CSP, no HSTS** | `SecurityMiddleware` + `XFrameOptionsMiddleware` in `MIDDLEWARE`; no CSP package/setting | partly effective |
| C3 | Debug / error disclosure | 404 page shows the full URL configuration (`Using the URLconf defined in …`); 500s on the JSON APIs return exception text | `DEBUG = True`, `ALLOWED_HOSTS = ['*']`, hard-coded `SECRET_KEY` (`settings.py` lines 12–17); `str(e)` returned in `create/update_requisition_api` | **not effective** (deployment configuration) |
| C4 | **Role checks on workflow endpoints** | §2: issue open to every logged-in user; approval open to Admin | `IssueItemsView` lacks `AdminRequiredMixin`; `HODApprovalView.get_queryset` admin branch | **not effective** → F3, F4 |
| C5 | CSRF protection | every unsafe request without token rejected (API test M4: 403); tokens in all forms | `CsrfViewMiddleware` enabled; **but** cancel is a GET (F19) | effective except F19 |
| C6 | Third-party front-end assets | Bootstrap 5.3.0 / icons 1.10.0 from CDN without SRI | `templates/base.html` | weakness (supply chain) |

## 5. Dependency audit — pip-audit 2.9.0
Command: `pip-audit -r requirements-lock.txt --format json` → `reports/security/pip-audit.json`. **84 packages checked** (exact installed versions, application + test tooling). Application packages and versions checked: Django 4.2.30, django-crispy-forms 2.5, crispy-bootstrap5 2026.3, Pillow 13.0.0, pandas 3.1.1, openpyxl 3.1.5 (plus their transitive dependencies; full list in `requirements-lock.txt`). No advisory was reported for crispy-forms, crispy-bootstrap5, Pillow, pandas or openpyxl.

| Component | Version | Advisories | Relevance to this application | Likely impact | Recommended correction |
|---|---|---|---|---|---|
| **Django** | 4.2.30 | 8 (CVE-2026-15830, CVE-2026-15307, CVE-2026-48587, CVE-2026-6873, CVE-2026-8404, CVE-2026-48588, CVE-2026-53877, CVE-2026-53878) — fixed only in 5.2.15–5.2.17 / 6.0.6–6.0.8 | The affected features (GeoDjango, cache middleware / `cache_page`, `get_signed_cookie`, `DomainNameValidator`) are **not used** (grep of core/inventory/requisition/hpl_ims: no matches). The real finding: **4.2 is end-of-life** — no fix is published for the 4.2 line, so future advisories will not be patched either. | low today; rising over time | upgrade to the 5.2 LTS line (≥ 5.2.17) and re-run the suites |
| requirements.txt (all) | `>=` ranges | — | upstream pins nothing; two installs can get different versions | non-reproducible builds, silent upgrades | pin exact versions (team uses `requirements-lock.txt`) |
| requests | 2.32.3 | CVE-2024-47081, CVE-2026-25645 | **test tooling only** (API test client), not deployed | none for the application | bump to ≥ 2.33.0 in `requirements-test.txt` |
| pytest | 8.3.5 | CVE-2025-71176 | test tooling only; local temp-dir issue | none for the application | bump to ≥ 9.0.3 |

## 6. Findings summary (root cause · severity · risk · fix)

| Finding | Root cause | Severity | Risk | Fix |
|---|---|---|---|---|
| F3 any user can issue | role check not applied server-side | S1 | PR-1 | `AdminRequiredMixin` on `IssueItemsView` (fix PR) |
| F4 Admin can approve / re-authorize | admin branch in approval queryset | S1 | PR-3, PR-4 | restrict to HODs (fix PR) |
| F19 state change on GET | function view without `require_POST`, link in template | S2 | PR-8 | POST form + `@require_POST` |
| C3 DEBUG / secret / hosts | development settings committed | S2 (deployment) | PR-8 | env-based settings: `DEBUG=False`, secret from env, explicit `ALLOWED_HOSTS` |
| C1 session cookie not Secure, 14-day life | defaults | S3 | PR-8 | `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, shorter `SESSION_COOKIE_AGE` behind HTTPS |
| C2 no CSP / HSTS | not configured | S3 | PR-8 | CSP header (e.g. django-csp), `SECURE_HSTS_SECONDS` |
| C6 CDN without SRI | template | S3 | PR-8 | add `integrity` + `crossorigin` or self-host |
| Django 4.2 EOL, unpinned deps | dependency management | S3 | PR-8 | upgrade to 5.2 LTS; pin versions |
