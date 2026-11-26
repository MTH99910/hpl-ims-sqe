# Estimation — three-point (PERT) per area, compared with actual effort

**How the estimates were made.** The project plan (26 Nov, before execution — `PROJECT_PLAN.md` §14) budgeted a *most likely* number of hours **M** for each block of work. Optimistic and pessimistic values were set as **O = 0.5 M** (everything works first time) and **P = 2 M** (tool problems, rework), giving the PERT expectation **E = (O + 4M + P) / 6 = 1.08 M** and spread **σ = (P − O) / 6 = 0.25 M**. (The O/P rule was written down on 26 Nov evening; the M values are the plan's.)

**How actuals were measured.** Effort was not stop-watched. Actual hours for Member A's areas are reconstructed from the session timeline and the commit timestamps of 26 Nov (planning 14:30–16:45, execution 16:50–20:30); background jobs (SonarQube download, mutation runs, k6 runs) overlapped with other work and are counted once, in the area that waited for them. Member B's actuals will be added by Member B. **Treat actuals as ± 30 %.**

| Area | Owner | M (h) | O (h) | P (h) | **E (h)** | σ (h) | Actual (h) | Variance vs E |
|---|---|---|---|---|---|---|---|---|
| Planning, test basis, test plan, risk register | shared | 3.0 | 1.5 | 6.0 | **3.3** | 0.8 | 2.6 (plan + independent review + basis) | −21 % |
| Environment, repo, seed / reset | A | 1.5 | 0.8 | 3.0 | **1.6** | 0.4 | 0.7 | −56 % |
| Static analysis + hand CFG | A | 1.5 | 0.8 | 3.0 | **1.6** | 0.4 | 0.8 | −50 % |
| Unit tests (100 %), MCC / MC-DC | A | 4.0 | 2.0 | 8.0 | **4.3** | 1.0 | 1.0 | −77 % |
| Mutation + custom operators + survivor analysis | A | 4.0 | 2.0 | 8.0 | **4.3** | 1.0 | 1.0 | −77 % |
| CI pipeline + gates (+ PRs) | A | 2.5 | 1.3 | 5.0 | **2.7** | 0.6 | 0.7 so far (PRs pending) | open |
| Use cases UC-01/UC-03 + E2E harness | A | 2.0 | 1.0 | 4.0 | **2.2** | 0.5 | 1.0 | −55 % |
| Security (access matrix, ZAP, audit, controls) | A | 2.0 | 1.0 | 4.0 | **2.2** | 0.5 | 0.9 | −59 % |
| Performance + recovery | A | 1.5 | 0.8 | 3.0 | **1.6** | 0.4 | 0.7 (incl. 1 invalid attempt) | −56 % |
| Defects, RCA, Pareto, reports, PDF | shared | 8.5 | 4.3 | 17.0 | **9.2** | 2.1 | 1.6 so far | open |
| OpenAPI + generator + API tests + regeneration demo | B | 5.0 | 2.5 | 10.0 | **5.4** | 1.3 | *(Member B)* | |
| Use cases UC-02/UC-04, usability, accessibility (+ fix) | B | 5.0 | 2.5 | 10.0 | **5.4** | 1.3 | *(Member B)* | |
| **Total** | | **40.5** | | | **43.8** | **σ_total ≈ 3.4** | | |

**Reading the comparison.**
* Member A's completed areas took roughly **40–80 % less** than expected. The main reason is the tool-supported way of working (test code generated and executed in one session, reviewed afterwards) — the plan's M values assumed hand-written tests. The estimate is therefore not a good predictor for this way of working; the variance is systematic, not random.
* Where time *was* lost it was in the environment, not in test design: Python 3.14 too new for Django 4.2, a ~260 KB/s network (SonarQube image and Chromium downloads), a hanging Playwright browser install, a mutation run that counted crashes as kills (wrong interpreter), k6 cookie reset invalidating the first load run, Playwright not supporting the CI image. These match project risk PJ-2 (score 12) — the risk was real; the mitigation (local tools, retries, documented workarounds) kept it from affecting the schedule.
* Final actuals (including the PRs, reports and Member B's areas) are added in the test completion report.
