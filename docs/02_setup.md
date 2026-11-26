# Setup, start, seed and reset

All commands run from the repository root. Tested on Linux (CachyOS, kernel 7.3) and on GitHub Actions `ubuntu-latest`.

## 1. Prerequisites
| Tool | Version used | Why |
|---|---|---|
| Python | **3.12.16** | Django 4.2 supports Python ≤ 3.12 (the host's Python 3.14 is too new) |
| uv | 0.13.10 | installs Python 3.12 and the virtualenv quickly |
| Node.js / npm | 26.13.1 / 12.2.3 | Playwright + axe-core test runner |
| Docker | 29.10.0 | SonarQube, sonar-scanner, OWASP ZAP, Grafana k6 |

Full tool list with exact versions: `docs/tool_versions.md`.

## 2. Install
```bash
pip install uv                       # or: curl -LsSf https://astral.sh/uv/install.sh | sh
uv python install 3.12
uv venv -p 3.12 .venv
uv pip install -p .venv/bin/python -r requirements.txt -r requirements-test.txt
# exact versions actually installed are frozen in requirements-lock.txt:
#   uv pip install -p .venv/bin/python -r requirements-lock.txt
cd tests/team/e2e && npm ci && npx playwright install chromium && cd -
```

## 3. Seed synthetic test data / reset between runs
The upstream repository ships a populated `db.sqlite3`. The team suites **never use it**: `tests/team/settings_test.py` points Django at `tests/team/data/team.sqlite3` instead (override with `TEAM_DB=/path`).

```bash
scripts/team/reset_db.sh
```
This deletes the team DB, runs `migrate`, runs `scripts/team/seed_team.py` (fixed, non-random data) and refreshes `tests/team/data/golden.sqlite3` (used to restore identical starting data before every performance run).

Seeded data (all synthetic, password for every account: `Test@12345`):

| Username | Role | Department |
|---|---|---|
| superadmin | Super Admin | – |
| admin, admin2 | Admin (issuer) | – |
| hod_it | HOD | Information Technology |
| hod_hr | HOD | Human Resources |
| hod_nodept | HOD | *(none — negative case)* |
| user_it_1 | Initiator | Information Technology |
| user_hr_1 | Initiator | Human Resources |

| Item | Stock | Reorder level | Purpose in tests |
|---|---|---|---|
| ST001 Ball point pen | 10 | 5 | main WF1/WF2 item |
| ST002 A4 paper ream | 1 | 2 | stock-limit boundary |
| HK001 Floor cleaner | 0 | 3 | zero-stock boundary |
| HK002 Disposable gloves | 50 | 10 | multi-line requisitions |
| ST099 Discontinued marker | 5 | – | inactive item (must not be selectable) |

Requisitions: three `pending_hod` (two IT, one HR), three `authorized` (IT), and one each of `sent_back`, `rejected`, `issued`, `cancelled`, `draft`.

## 4. Start the application
```bash
scripts/team/run_server.sh              # Django dev server on http://127.0.0.1:8000 (functional / E2E tests)
MODE=perf scripts/team/run_server.sh    # gunicorn, 2 workers (performance runs - same build every run)
```

## 5. Run the test suites
```bash
FAST_HASH=1 .venv/bin/pytest tests/team/unit --cov --cov-report=json:reports/tmp/coverage.json
.venv/bin/python scripts/team/coverage_gate.py reports/tmp/coverage.json
```
(API, E2E, mutation, performance and security commands are added in their own sections of the report and in `.github/workflows/ci.yml`.)

`FAST_HASH=1` switches the password hasher to MD5 **for tests only**, which makes logins in tests faster without changing any application behaviour under test.
