# Progress report — week 2 (23–29 Nov 2026)

Reported per day because all execution happened in this week. Planned = `docs/04_test_plan.md` §6 / `PROJECT_PLAN.md` §14.

## Thu 26 Nov
| Planned for the day | Actual | Status |
|---|---|---|
| Setup, baseline, seed/reset | done (Python 3.12 via uv; isolated test DB; deterministic seed) | ✔ |
| Test basis, test plan, risk register, exit criteria | done | ✔ |
| SonarQube baseline | done (baseline + with-tests runs) | ✔ |
| *(planned for Fri)* unit tests, MCC/MC-DC, generator, API tests, mutation, CI skeleton | done ahead of plan | ✔ ahead |
| *(planned for Sat)* E2E/use cases, usability, a11y before/after, ZAP, pip-audit, k6, recovery | done ahead of plan (a11y fix prepared; PR pending) | ✔ ahead |
| Defects logged | 14 GitHub Issues (#1–#14) with severity/priority/status/triage/category | ✔ |

**Problems and control actions**
| Problem | Effect | Control action |
|---|---|---|
| Host Python 3.14 too new for Django 4.2 | app would not run | installed Python 3.12 with uv, documented in setup |
| Network ≈ 260 KB/s (SonarQube image, Chromium) | downloads blocked tests for ~1 h | worked on other tasks in parallel; installed Chromium manually from the verified zip; used pysonar instead of the 600 MB scanner image |
| Mutation run reported 0 survivors | false confidence | traced to the wrong interpreter; fixed; added `cosmic-ray baseline` to CI |
| First k6 run 98 % failures | invalid measurement | traced to k6 cookie reset; fixed (`noCookiesReset`), re-ran all 4 runs, kept the invalid attempt with explanation |
| CI E2E failed on ubuntu-latest (26.04) | e2e gate red | pinned runners to ubuntu-24.04 |
| Workload carried by one machine (risk PJ-1) | partner's areas at risk | work split: handover package for Member B (areas 2 + 3a), private shared notes |

## GQM
**Goal:** assess the release readiness of the Requisition workflows WF1/WF2 from the tester's point of view.

| Question | Metric | Value (26 Nov) | Reading in context |
|---|---|---|---|
| Q1 How defect-prone is the module? | **Defect density** = confirmed code defects / KLOC in scope | 13 / 1.406 KLOC = **9.2 defects/KLOC** (F21 is a documentation mismatch, excluded; KLOC = SonarQube ncloc of the 5 full-scope files 1 312 + 94 lines of in-scope endpoint functions) | High for such a small module, but expected: upstream had **no tests** at all, and the first full test pass always finds the backlog. 3 of the 13 are S1 and all three sit on the main path of the two workflows (F3, F4, F13) — density alone understates the risk. |
| Q2 How completely are the requirements verified? | **Requirements coverage** = FR/BR with ≥ 1 linked test executed and passing / total (`scripts/team/rtm_check.py` on the JUnit results of all suites) | **19 / 19 = 100 %** | Coverage by *passing* tests is 100 %, but 7 requirements also have *expected-fail* tests pointing at open defects — "covered" does not mean "satisfied". |
| Q3 How effective are the fixes? | **Reopen rate** = reopened / fixed | 0 / 0 (no fix merged yet) | Becomes meaningful after the fix PRs (F13, F3, F4, F20). |
