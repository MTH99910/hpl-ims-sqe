# AI-use record

Course rule: AI tools are allowed if every output is checked and disclosed (tool, purpose, output, what was checked or changed); prompts are kept.

**Tool used by Member A:** Claude Code (CLI) with the model Claude Opus 5.5, on Member A's machine, 26–29 Nov 2026.
**Prompts:** kept by Member A (session export); available on request.

| # | Date | Member | Purpose | Output (files / artefacts) | What was checked / changed (verification done) | Reviewed by the member (filled in by the member) |
|---|---|---|---|---|---|---|
| 1 | 26 Nov | A | Read the course PDF and the SUT code; draft the project plan | `PROJECT_PLAN.md` | Plan audited item-by-item against the PDF by a separate AI agent with no context; 20+ gaps found and fixed (licence, API eligibility, Sonar new-code gate, CI deadlock, ZAP loopback, k6 sessions, …) | |
| 2 | 26 Nov | A | Set-up, deterministic seed and reset scripts, isolated test settings | `scripts/team/*`, `tests/team/settings_test.py`, `docs/02_setup.md` | Exploratory probes on a scratch DB confirmed F3, F4, F5 and found **F13** before any test was written; seed re-run from scratch | |
| 3 | 26 Nov | A | Test basis (FRs, rules, roles, assumptions) | `docs/01_test_basis.md` | Every requirement traced to a README sentence or a code location; README/code contradictions recorded as assumptions A1–A8 | |
| 4 | 26 Nov | A | White-box unit suite, MCC/MC-DC tables, coverage gate | `tests/team/unit/*`, `scripts/team/coverage_gate.py`, `docs/11_unit_testing.md` | All tests executed; two test-side errors fixed after running (Django absolute_max = 2000, not 1000; an always-true assertion removed); found F14, F15 during the run; MC/DC pair for condition A corrected | |
| 5 | 26 Nov | A | Static analysis + hand-calculated cyclomatic complexity | `docs/03_static_analysis.md`, `sonar-project.properties` | Sonar values read from the server API (not estimated); hand V(G) = 5 matched Sonar's function value 5; for `is_pending_action` hand 7 vs Sonar 6 explained; coverage path problem in `coverage.xml` found and fixed | |
| 6 | 26 Nov | A | Mutation testing, 3 custom operators, survivor analysis | `tests/team/mutation/*`, `docs/13_mutation.md`, `reports/mutation/*` | First run was invalid (0 survivors because the test command used the wrong Python) — detected, fixed, guarded with `cosmic-ray baseline`; all 25 survivors analysed; operator counts initially written without measuring and then **corrected** from the session database | |
| 7 | 26 Nov | A | CI workflow and gates | `.github/workflows/ci.yml`, `scripts/team/lint_ci.sh`, `scripts/team/sonar_gate.sh`, `docs/14_ci_gate.md` | Sonar gate script tested on a fresh container (gate PASSED); lint job matched its own pattern on first CI run → moved to a script; runner pinned after Playwright failed on ubuntu 26.04 | |
| 8 | 26 Nov | A | E2E harness, UC-01, UC-03, access matrix | `tests/team/e2e/helpers/*`, `uc01*`, `uc03*`, `security/*`, `docs/17_security.md` | Several selectors fixed after real runs (ambiguous labels, row order of the issue table); access results generated from the run, not typed | |
| 9 | 26 Nov | A | ZAP passive scan, control review, pip-audit | `scripts/team/zap_passive.sh`, `reports/security/*` | Alerts triaged by hand (csrftoken HttpOnly is by design, CDN CORS not the app); cookie flags and headers corroborated with a direct request and with `settings.py`; Django advisories checked against actual feature use | |
| 10 | 26 Nov | A | Load test, recovery test | `tests/team/perf/*`, `tests/team/integration/test_recovery.py`, `docs/18_performance.md` | Targets committed before the first run; first run invalid (k6 cookie reset) — kept with explanation, re-run | |
| 11 | 26 Nov | A | Risk register, test plan, RCA, estimation, RTM, figures | `docs/04, 05, 06, 07, 09`, `docs/figures/*` | Figures generated from data (GitHub Issues for the Pareto); schedule "actual" cells left empty for future days instead of predicted | |
| 12 | 26–27 Nov | A | Fix PRs F13, F3+F4; blocked PR | branches `fix/*`, `demo/blocked-*` | Each fix: failing tests first, then fix; unit + integration + E2E re-run on the fix; access matrix 8/8 after fix | |

Member B adds his own rows below for his areas.

**Tool used by Member B:** Claude Code (CLI) with the model Claude Opus 5.5, on Member B's machine (Windows 11, native, Python 3.12 via uv), 27–29 Nov 2026.
**Prompts:** kept by Member B (session export); available on request.

| # | Date | Member | Purpose | Output (files / artefacts) | What was checked / changed (verification done) | Reviewed by the member (filled in by the member) |
|---|---|---|---|---|---|---|
| 13 | 27 Nov | B | Set up on Windows; install the Area 2 / 3a files written on Member A's machine and re-verify them before committing | `tests/team/datagen/*`, `tests/team/api/*`, `uc02*`, `uc04*`, `usability/*`, `a11y/*`, `reports/a11y/before/*`, `reports/api_coverage.md`, `docs/12`, `docs/15` | Every number re-run on this machine before commit: unit 227 passed + 10 xfailed; spec valid; `generator.py --check` up to date (164 cases); datagen 7 passed; API + integration 169 passed + 38 xfailed; coverage 9/9 at 100 %; UC-02/UC-04/UX 12 passed — all equal to the handover numbers | |
| 14 | 27 Nov | B | Execute the 12 generated login cases (T2b) | `test_API_login_generated` in `tests/team/api/test_api_generated.py`, `docs/12` §1 | First run failed 6 cases: the read-back GET followed the redirect to the login page (200). Traced to `requests.Session.get()` forcing `allow_redirects=True`; fixed once in `ApiClient.get()` instead of in the test. Full suite re-run: 181 passed + 38 xfailed (existing tests unchanged), coverage still 100 % | |
| 15 | 27 Nov | B | Accessibility fix PR (fixes F20) and after-measurements | `templates/*` (patch), UC-02 E2 `test.fail` removed, `reports/a11y/after/*` | Patch read line by line before applying; the copied after-reports were deleted and regenerated from this machine's run; Lighthouse `finalUrl` checked (logged in); full E2E 35 passed; Member A's security screenshots overwritten by the run were restored, not committed | |
| 16 | 27 Nov | B | Accessibility and usability findings document | `docs/16_a11y_findings.md` | Every score and node count read from the JSON reports by script; one wrongly attributed source ("found by UX-01" for the fieldset finding) corrected to code review | |
| 17 | 27 Nov | B | Regeneration demo (T5) | branch `demo/spec-change-regeneration`, `docs/12` §4 | Prediction written from the generator and view code before editing the spec; actual run matched (6 failed, same ids; 170 cases) | |
