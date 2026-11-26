# CI quality gate (GitHub Actions)

Workflow: `.github/workflows/ci.yml` — runs on **every pull request to `main`** and every push to `main`, on `ubuntu-24.04` (pinned: Playwright 1.52 has no browser build for the newer `ubuntu-latest` = 26.04 image — found when the first E2E job failed).

## 1. Jobs (every job is a required status check on `main`)

| Job | What it runs | Fails when |
|---|---|---|
| `lint-ci (no escape hatches)` | `scripts/team/lint_ci.sh` | any workflow contains `continue-on-error`, `\|\| true` or `set +e` (comments ignored) |
| `unit + coverage gate` | white-box unit suite + operator self-tests, coverage.py (branch) | a test fails, or `scripts/team/coverage_gate.py` finds an in-scope line/branch that is neither covered nor justified (or a justification that is no longer needed) |
| `api + integration + data generation` | spec validation, `generator.py --check`, API + integration + generator tests, API coverage criteria | spec invalid, generated data stale, a test fails, a reachable API coverage criterion < 100 % |
| `e2e (Playwright + axe)` | use cases, usability, access matrix, axe scans (Chromium) | a test fails |
| `mutation (Cosmic Ray, business-rule module)` | `cosmic-ray baseline` (unmutated suite must pass), init → scope filter → exec, `score.py` | baseline broken, mutants pending, score of non-equivalent mutants < threshold |
| `sonarqube quality gate` | SonarQube Community service container, `sonar_gate.sh` creates the custom gate, `pysonar` with `qualitygate.wait=true` | any gate condition violated |
| `deploy` | publishes the release candidate (only on `main`) | — it **needs all six jobs**, so any failing gate also blocks deployment |

**No escape hatches:** no `continue-on-error`, no `|| true`, no `set +e` in any workflow (checked by `lint-ci`). Report-upload steps use `if: success() || failure()` — they only upload artefacts and are not gates. Known open defects are tested with `xfail(strict=True)` / Playwright `test.fail()`: the test asserts the correct behaviour and *fails the build as soon as the defect is fixed* unless the marker is removed in the same PR — every marker is linked to a GitHub issue.

## 2. Thresholds and why (justified from the measurements)

| Gate | Threshold | Evidence it is based on |
|---|---|---|
| Unit coverage | **100 % of feasible in-scope statements and branches**; every exclusion written in `tests/team/coverage_allowlist.json` | course requirement; measured 100 % feasible (doc 11). A lower number would let new untested business logic in silently. |
| Mutation score | **≥ 95 %** of non-equivalent mutants killed | run 1 (first suite) 95.3 %, run 2 100 % (doc 13). Below 95 % would accept a suite weaker than our first version; exactly 100 % would block every PR that creates a new equivalent mutant before it can be analysed — a survivor must be killed or justified in `equivalent.json` in the same PR. |
| API coverage criteria | **100 % of reachable** for all 9 criteria | measured 100 %; responses blocked by open defects are reported separately and become required when the defect is fixed. |
| SonarQube "SQE gate" (overall code) | coverage ≥ 95 %; bugs ≤ 1; vulnerabilities ≤ 19; duplicated lines ≤ 3 %; reliability and security rating not worse than C | measured baseline: coverage 95.9 %, 1 bug (upstream dead `return`), 19 vulnerabilities (9× S3752, 9× S2245 in the seed command, 1× DEBUG), duplication 1.2 %, ratings C/C (doc 03). Overall-code conditions because every CI run is a first analysis on a fresh Community container — the default "new code" conditions would always be empty and could never fail. Verified on a fresh container: gate created, analysis PASSED. |
| Performance | not a CI gate (by design) | comparable numbers need the same machine and data; k6 runs are done manually (doc 18). |

## 3. Required pull requests

### 3.1 Documented fix through a pull request (fails before, passes after) — F13 (#1)
* Branch `fix/f13-issue-saves-default-quantity`, two commits:
  1. `test(F13): expect the pre-filled quantity to be issued (remove xfail markers)` — CI **red**: `unit` fails on `test_UT63_default_quantity_issue_deducts_stock`, `e2e` fails on UC-03 main/A1.
  2. `fix(F13): save every issue line so the pre-filled quantity deducts stock` — CI **green**.
* PR link, failing run link and passing run link: **_to be filled in when the PR is opened (waiting for Member B's commits so that only the intended job fails)_**.

### 3.2 Pull request blocked by the pipeline
* Branch `demo/blocked-br1-boundary-regression`: changes `qty_issued > qty_requested` to `>=` in `clean_quantity_issued` (looks like a tidy-up, breaks BR-1 at the upper boundary).
* Locally exactly **one** unit test fails — the 3-point BVA case `test_UT31_upper_bound_requested[4-True]` (issue exactly the requested amount). Mutation and API jobs are expected to fail as well.
* Branch protection on `main` requires all jobs → merge button blocked. PR link + run link + screenshot: **_to be filled in_**.

### 3.3 Second fix PR — F3 (#2) + F4 (#3)
`fix/f3-f4-role-checks`: commit 1 removes the F3/F4 markers (4 unit tests fail locally), commit 2 adds `AdminRequiredMixin` to `IssueItemsView` and stops giving Admins an unfiltered approval queryset. After the fix the access matrix is 8/8 as expected (`reports/security/after-fix/`). Links: **_to be filled in_**.
