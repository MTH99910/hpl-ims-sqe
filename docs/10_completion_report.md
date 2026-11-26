# Test completion report

**Scope:** Requisition module of HPL IMS @ `549113c` — WF1 (HOD approval) and WF2 (Admin issue), as defined in `docs/01_test_basis.md`.
**Status of this report:** 26 Nov 2026 (after test execution). Rows marked ⟳ are updated when the fix PRs (F13, F3+F4, a11y/F20) are merged.

## 1. What was tested — and what was not
| Level / activity | Tested | Result |
|---|---|---|
| Unit (white-box) | 237 cases; models, forms, all requisition views, in-scope endpoint functions | 227 pass, 10 expected-fail (open defects); 100 % feasible statement + branch coverage |
| MCC / MC-DC | BR-2 `is_pending_action` (8 rows + 1 infeasible), BR-1 stock check, reason rule (8 rows), HOD queryset | all rows executed; MC/DC pairs identified for every condition |
| Mutation | 267 business-rule mutants, 3 custom operators | 100 % of non-equivalent killed (13 equivalent, justified) |
| API / integration | 204 API cases (EP + 3-point BVA from generated data, DT-1/DT-4, 18 state transitions, repeated requests, cross-workflow) + recovery | 167 pass, 37 expected-fail; 9 API coverage criteria at 100 % of reachable |
| Use cases (E2E) | UC-01…UC-04, every main/alternative/exception flow (20 flows) | all executed; 3 expected failures (F13 ×2, F20) |
| Usability / accessibility | 2 task tests (one keyboard-only), axe on 5 screens, Lighthouse on 2 key screens, fix + re-scan | HOD screen: Lighthouse a11y 92 → 100, axe 3 → 0 rules |
| Security | 8 access decisions, ZAP passive (361 messages), 6 controls, pip-audit (84 packages) | 4 access violations (F3, F4); configuration weaknesses (DEBUG, cookies, CSP, SRI) |
| Performance / recovery | 4 k6 runs (1 VU ×2, 5 VU ×2), failure injection on the issue | all within targets; full rollback and clean retry |

**Not tested (and why):** Super Admin user/department management, Excel upload, item/location CRUD, stock-adjustment screen (outside both workflows); browsers other than Chromium; production deployment (only configuration reviewed); load on write operations (one operation required; SQLite write locking is a residual risk); the `draft` state end-to-end (no code path creates it — tested at unit level only).

## 2. Deviations from the plan
* Schedule compressed to 3 days; most of the planned Fri/Sat work was done on Thu (tool-supported execution).
* Pair group → 4 use cases instead of 6; area 3 split (3a Member B, 3b Member A).
* Lighthouse run through its Node API with a Playwright login (persistent profile) instead of DevTools — allowed option ("Lighthouse CI with a login script").
* SonarQube scanner: `pysonar` instead of the scanner Docker image (network too slow); CI runner pinned to ubuntu-24.04.
* Two measurement attempts were invalid and repeated (mutation run with the wrong interpreter; k6 cookie reset) — both kept/documented.
* Fix PRs were planned for Saturday; they wait for Member B's commits so that CI fails only for the intended reason.

## 3. Defects
14 logged (#1–#14): **S1 × 3** (F13 stock not deducted, F3 any user can issue, F4 Admin approves / re-authorizes), **S2 × 4** (F7, F6, F14, F19), **S3 × 6**, **S4 × 1**. Pareto: error-handling 36 %, then validation / data-integrity / access-control 14 % each → 4 categories = 79 % of defects. Root-cause analyses: F13, F3 (`docs/09_rca.md`).
⟳ Fixed and verified after the PRs: F13, F3, F4, F20. Open (triaged *defer*): F7, F6, F14, F15, F16, F17, F18, F5, F19; *won't fix*: F21.

## 4. Exit / release criteria — actual vs target
| Criterion | Target | Actual now | Actual after fix PRs ⟳ | Met? |
|---|---|---|---|---|
| **EC-1** open S1/S2 defects in access control and stock integrity (PR-1, PR-2, PR-3) | 0 | 4 (F3, F4, F13 S1; F7 S2) | 1 (F7 S2 — two lines of the same item can drive stock negative) | **No** |
| **EC-2** feasible coverage / mutation score | 100 % / ≥ 95 % | 100 % / 100 % | 100 % / ≥ 95 % (re-checked by CI on the PRs) | **Yes** |
| **EC-3** p95 and failures at 5 VUs | ≤ 800 ms, < 1 % | 6.18 / 6.00 ms, 0 % | unchanged (read path not touched) | **Yes** |
| EC-4 requirements coverage | 100 % | 19 / 19 | 19 / 19 | Yes |
| EC-5 serious/critical axe violations on the fixed screen | 0 | 0 after fix (1 serious before) | 0 | Yes (after B's PR) |

## 5. Residual risk per risk
| Risk | Before testing | Evidence | Residual (after fix PRs) |
|---|---|---|---|
| PR-1 non-Admin issues | 25 High | F3 confirmed; fixed (role check) + access matrix 8/8 in CI | **Low (4)** — regression covered by SEC tests and DT-4 in every PR |
| PR-2 wrong stock | 20 High | F13 fixed; **F7 open** (negative stock with duplicate lines); no concurrency control (no `select_for_update`) | **Medium-High (12)** — requires a duplicate item in one requisition, or two simultaneous issues |
| PR-3 HOD/Admin authority | 20 High | F4 fixed; MCC/MC-DC + mutation (dept-less HOD case added) | **Low (4)** |
| PR-4 invalid transition | 16 High | F4 (issued → authorized) fixed; all 7 valid + 11 invalid transitions tested; **F19** cancel via GET | **Low–Medium (6)** |
| PR-5 partial failure | 15 High | issue is atomic (REC01/REC02); **create API not atomic (F6)** | **Medium (9)** |
| PR-6 API input crashes | 12 Medium | F5, F6, F16, F17, F18 open | **Medium (12)** — unchanged, deferred |
| PR-7 usability / a11y | 9 Medium | F20 fixed; key screen 100; dashboards still have contrast/link-name issues | **Low–Medium (6)** |
| PR-8 configuration / session | 9 Medium | DEBUG on, secret in code, cookie not Secure, no CSP, CDN without SRI, Django 4.2 EOL | **Medium (9)** — must be closed before any production use |
| PR-9 performance | 6 Low | p95 ~6 ms at 5 users | **Low (2)** for reads; writes not measured |
| PR-10 notifications | 4 Low | asserted in API/E2E read-backs | **Low (2)** |

## 6. Recommendation: **HOLD** ⟳
Release criterion EC-1 is not met even after the three S1 fixes: **F7** can still make stock negative (stock integrity is the purpose of WF2), and the deployment configuration (PR-8) is not production-safe. EC-2 and EC-3 are met.
**Conditions for release:** (1) merge the F13 and F3+F4 fixes (green CI, issues verified); (2) fix F7 (aggregate the issued quantity per item and lock the item rows during the issue); (3) production settings (DEBUG off, secret from environment, secure cookies, CSP) and upgrade to Django 5.2 LTS; (4) F6/F19 strongly recommended. After (1)–(3) all three release criteria would be met.

## 7. Effort — estimate vs actual
See `docs/05_estimation.md` (PERT per area; final actuals of both members added at the end).
