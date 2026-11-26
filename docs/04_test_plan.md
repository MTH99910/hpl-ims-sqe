# Test plan — Requisition module (WF1 HOD approval, WF2 Admin issue)

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-11-26 | Initial plan (scope, approach, criteria) |
| 1.1 | 2026-11-26 | After first execution: F13 added as highest-severity defect; mutation threshold set to 95 % from measured run 1 (95.3 %); pair-group ownership |

## 1. Scope
**Test items:** HPL IMS at upstream commit `549113c` — requisition app, inventory Item/Transaction/Location models, core User role logic and Notification, and the HTTP endpoints of WF1/WF2 (test basis §7).
**Features to be tested:** FR-01…FR-15, BR-1…BR-4, the HOD/Admin permission boundary, usability/accessibility of the two key screens, security controls of the two workflows, performance of the approval screen, recovery of the issue operation.
**Not tested (and why):** Super Admin user/department management, Excel upload, item/location CRUD, stock-adjustment screen (not part of either workflow); production deployment settings (only reviewed); browsers other than Chromium (tool mandate).

## 2. Approach by risk level
| Level | Risks | Techniques | Depth |
|---|---|---|---|
| High | PR-1…PR-5 | MCC + MC/DC, decision tables, state-transition (all valid + ≥ 1 invalid per state), 3-point BVA, access matrix, failure injection, mutation with business-rule operators | every condition combination; every role; read-back after every success and rejection |
| Medium | PR-6…PR-8 | generator-driven EP/BVA, API coverage criteria, axe + Lighthouse + keyboard test, ZAP passive, configuration review, pip-audit | every input class once; key screens; both workflows proxied |
| Low | PR-9, PR-10 | k6 1 VU / 5 VUs ×2; notification assertions inside other tests | one operation; no dedicated suite |

Test levels: **unit** (pytest-django, white-box) → **API/integration** (pytest + Requests against a live server) → **browser E2E** (Playwright, use cases) → non-functional (usability/a11y, security, performance, recovery). Upstream has no tests; all team tests live in `tests/team/`.

## 3. Roles
| Role | Member |
|---|---|
| Area 1 — static analysis, white-box, mutation, CI; area 3b — security, performance (and recovery) | **Member A** |
| Area 2 — API testing and data generation; area 3a — use cases UC-02/UC-04, usability, accessibility | **Member B** |
| Use cases UC-01, UC-03 | Member A |
| Test management (plan, risks, RTM, defects, reports) | shared |

## 4. Environment
Linux (CachyOS, kernel 7.3), 12 CPU threads, 30 GB RAM; Python 3.12.16, Django 4.2.30, SQLite; Node 26.13.1, Playwright 1.52.0 with Chromium 136; SonarQube Community 26.11 (Docker); Grafana k6 1.0.0; OWASP ZAP (Docker); CI on GitHub Actions `ubuntu-latest`. Exact versions: `docs/tool_versions.md`, `requirements-lock.txt`, `tests/team/e2e/package-lock.json`.

## 5. Test data
Synthetic only. `scripts/team/seed_team.py` (fixed values, no randomness) → `golden.sqlite3`; unit tests build their own rows with factories in `tests/team/conftest.py`; API field values come from the generator (`tests/team/datagen/generated/cases.json`).

## 6. Schedule
| Day | Planned | Actual |
|---|---|---|
| Thu 26 Nov | setup, test basis, plan, risks, SonarQube baseline | setup, test basis, unit suite (100 %), generator + API suite, mutation (2 runs), Sonar (2 runs), E2E suite, k6 — far ahead of plan because work was automated end-to-end |
| Fri 27 Nov | unit, API, generator, mutation, CI | *(to be filled in at the end of the day)* |
| Sat 28 Nov | E2E, a11y, security, perf, CI gate | *(to be filled in)* |
| Sun 29 Nov | reports, package, submit | *(to be filled in)* |

## 7. Entry criteria
* Baseline reproducible from the documented commands (`docs/02_setup.md`) — **met** (26 Nov).
* Seed and reset scripts produce identical data — **met** (`golden.sqlite3`).
* Scope and test basis agreed — **met**.

## 8. Exit criteria
See risk register §"Exit criteria": EC-1 (0 open S1/S2 access-control & stock-integrity defects), EC-2 (100 % feasible coverage, mutation ≥ 95 %), EC-3 (p95 ≤ 800 ms and < 1 % failures at 5 VUs), EC-4 (100 % requirements coverage), EC-5 (0 serious/critical axe violations on the fixed screen).

## 9. Suspension criteria
* The SUT cannot be started or seeded.
* A blocker stops ≥ 30 % of the planned cases of a level.
* Environment drift (tool or library version differs from the lock files).
* A test command is found to be invalid (e.g. every mutant "killed" by a crashing test command — happened once, see doc 13).

## 10. Resumption criteria
Blocker fixed or worked around and the smoke run (`reset_db.sh` + unit suite) green; environment restored to the locked versions; the suspended level is re-run from the start.

## 11. Risks
`docs/06_risk_register.md` (10 product risks, 4 project risks).

## 12. Deliverables
Test basis, this plan, estimation, risk register, RTM, defect reports (GitHub Issues), RCA, weekly/daily progress report, test completion report, all automated suites and their reports, CI workflow, AI-use record.
