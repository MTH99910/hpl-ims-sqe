# API and integration testing — results and endpoint weaknesses

**Harness:** pytest 8.3.5 + Requests 2.32.3 against pytest-django's live server (real HTTP, real session login with CSRF). Field values come **only** from the generator output (`tests/team/datagen/generated/cases.json`); fixtures choose the logged-in role and the seeded state. Every request/response is recorded (`reports/tmp/api_calls.jsonl`) and compared with the spec by `tests/team/api/coverage_report.py`.

## 1. Results
| Suite | Cases | Passed | Expected-fail (open defect, strict) |
|---|---|---|---|
| `test_api_generated.py` — EP + 3-point BVA for every input of 7 operations (all 164 generated cases) | 164 | 134 | 30 |
| `test_api_workflows.py` — state transitions, DT-1, DT-4, repeated requests, cross-workflow, method/auth/content type | 52 | 45 | 7 |
| `tests/team/integration/test_recovery.py` | 3 | 2 | 1 |

Command (27 Nov, before Member A's fix PRs): `pytest tests/team/api tests/team/integration -q` → **181 passed, 38 xfailed**; `python tests/team/api/coverage_report.py` → 674 recorded calls.

**Login cases (decision).** For credentials, "valid" means *the real value of an existing account*, not only "satisfies `minLength`". `test_API_login_generated` therefore sends the seeded account `hod_it` / `Test@12345` with one field replaced by the generated value; for a valid case (`ok`, and the BVA values `p`, `pp`) the account is first provisioned so that the generated value *is* its username or password. The value sent still comes only from the generator, and the lower boundary (a 1-character credential) is a genuine successful login (302 to `/requisition/hod/`, dashboard then 200). Invalid cases (empty, missing) → 200 with "Invalid username or password" and the dashboard still redirects to the login page.

**Harness note.** `requests.Session.get()` follows redirects by default, so a GET that returned 302 was recorded as the 200 of the page it redirected to. `ApiClient.get()` now disables redirects (as `request()` already did for POST), so every GET assertion and the coverage log see the endpoint's own status. Re-running the suite after the change gave the same pass/xfail split for the existing 207 tests.

Techniques applied at API level (each executable case counted once):
* **EP** — 125 generated class cases (valid classes per enum value; invalid: missing, wrong type, outside enum, empty, whitespace-padded, unknown/inactive/other-requisition references); one invalid value per case.
* **3-point BVA** — 39 generated boundary cases: `qty` min 1 (0/1/2), `purpose` minLength 10 (9/10/11), `items` minItems 1 (0/1/2), `quantity_issued` min 0 (−1/0/1), `quantity_issued` ≤ requested (req−1/req/req+1), `quantity_issued` ≤ stock (stock−1/stock/stock+1), reasons minLength 1 (0/1/2), login `username`/`password` minLength 1 (0/1/2).
* **Decision tables** — DT-1 approval authority (7 rules incl. Admin), DT-4 issue permission (4 roles), DT-2 reason rule through the generator's `context`.
* **State transitions** — all 7 valid transitions + 11 invalid ones (≥ 1 from every state); read-back of status, stock and transactions after each.
* **Repeated requests** — repeat issue (404, still one transaction), repeat approval (no duplicate notifications), double create (two distinct numbers — no idempotency key).
* **Cross-workflow** — WF1 approve → WF2 issue (shared `status`, `stock`, transaction `balance_after`, read back through the item API); WF1 reject → WF2 refused; send back → resubmit → approve → issue.

## 2. API coverage criteria (Martín-López et al., 2019)
`reports/api_coverage.md` (674 recorded calls) — **100 % of every reachable criterion**: paths 9/9, operations 11/11, parameters 22/22, parameter values (enums) 14/14, request content types 5/5, status-code classes 23/23, status codes 25/25, response body properties 28/28, response content types 7/7.
Three documented status codes are **blocked by open defects** and listed separately (not hidden): 403 for a non-Admin `GET`/`POST /issue/` (F3) and 404 for a foreign `update` (F6 — returns 500).

## 3. Endpoint weaknesses (each: root cause · severity · risk · fix)

| # | Endpoint | Weakness (evidence) | Root cause | Sev | Risk | Fix |
|---|---|---|---|---|---|---|
| W1 | `POST /requisition/{pk}/issue/` | Any logged-in role can issue (DT-4, M8) — **F3 #2** | no server-side role check | S1 | PR-1 | `AdminRequiredMixin` on the view |
| W2 | `POST /requisition/{pk}/hod-approval/` | Admin can decide on any state, issued → authorized (ST, DT-1 R7) — **F4 #3** | admin branch returns unfiltered queryset | S1 | PR-3, PR-4 | restrict to HOD + own dept + `pending_hod` |
| W3 | `POST /requisition/{pk}/issue/` | Unchanged pre-filled quantity not saved (X4) — **F13 #1** | formset skips unchanged forms | S1 | PR-2 | save every line form |
| W4 | `POST /requisition/api/create/` | unknown item → 500 + orphan requisition (generated `items[0].id:EP:02`, REC03) — **F6 #5** | no `transaction.atomic`, lines validated after header insert | S2 | PR-5, PR-6 | validate first, wrap in atomic, 400 |
| W5 | create / update API | wrong types → 500; decimal qty truncated; unknown `uom` stored (16 generated cases) — **F16 #8** | hand-written validation assumes types | S3 | PR-6 | form/serializer validation, 400 per field |
| W6 | create / update API | inactive item accepted — **F17 #9** | `Item.objects.get(pk)` without `is_active` | S3 | PR-6 | filter `is_active=True` |
| W7 | `POST /requisition/{pk}/issue/` | tampered line id / management form → 500 — **F18 #10** | `clean_quantity_issued` reads `instance.item` of an unsaved form | S3 | PR-6 | guard `instance.pk`, form error |
| W8 | `GET /inventory/api/item-details/?type=` | every type filter → 500 — **F5 #11** | filter after slice | S3 | PR-6 | filter before slicing |
| W9 | `POST /requisition/{pk}/api/update/` | foreign pk → 500 instead of 404 (UT114) — F6 family | broad `except Exception` swallows `Http404` | S3 | PR-6 | catch only expected exceptions |
| W10 | all JSON endpoints | unauthenticated → 302 to HTML login instead of 401 JSON (M2) | `@login_required` designed for pages | S4 | PR-6 | return 401 JSON for API paths |
| W11 | create API | no idempotency — the same body twice creates two requisitions (REP) | no client token / duplicate check | S4 | PR-6 | optional idempotency key |
| W12 | create / update API | error messages echo internal exception text (`'Server error: Item matching query does not exist.'`) | `str(e)` returned to client | S3 | PR-8 | generic message, log details |

Observation (not a defect): CSRF protection is active for every unsafe method, including the JSON APIs (M4: login POST without token → 403).

## 4. Automated test data generation — regeneration demo (two changed constraints)
Branch `demo/spec-change-regeneration` (PR left open, **not merged** — the server is deliberately unchanged). Two constraints changed in `tests/team/datagen/openapi.yaml`: (1) `RequisitionInput.purpose.minLength` 10 → **15**, (2) `LineInput.qty` gets **`maximum: 50`**.

**Prediction** (written in the PR description before the spec was edited, from `generator.py` and `requisition/views.py`, which rejects `len(purpose.strip()) < 10` and `qty < 1` and has no upper qty limit): 164 → 170 cases; the `purpose` cases keep their count but change value; `qty` gets 3 BVA cases per operation; 6 tests fail — `purpose:EP:02` (whitespace-padded, 14 characters after trimming), `purpose:BVA:05` (14 characters) and `items[0].qty:BVA:09` (51), each for `createRequisition` and `updateRequisition`; the first failing CI step is `generator.py --check` while the data is stale, then the API test step.

**Actual** (27 Nov 2026, local run):

| Step | Command | Result |
|---|---|---|
| 1. spec edited, data not refreshed (commit `27ad72e`) | `python tests/team/datagen/generator.py --check` | `generated/cases.json is STALE - run tests/team/datagen/generator.py`, exit 1 |
| 2. regenerate (commit `936436c`) | `python tests/team/datagen/generator.py` | `wrote 170 cases (BVA 45, EP 125) from spec 93b0cd3c9df4` (before: 164 = BVA 39 + EP 125, spec `6c13ee4e1eff`) |
| 3. diff | `git diff --stat` | `cases.json` 120 +/− lines, `cases.md` 30, `openapi.yaml` 4 |
| 4. API suite | `pytest tests/team/api tests/team/integration tests/team/datagen` | **6 failed, 188 passed, 38 xfailed** |

New / changed rows in `generated/cases.md` (same for `updateRequisition`):

| Field | Class | Value | Expected |
|---|---|---|---|
| `purpose` | valid:normal | `"Valid text Valid tex"` (20) | valid |
| `purpose` | invalid:whitespace-padded-too-short | `"  aaaaaaaaaaaaaa  "` (14 after trim) | invalid |
| `purpose` | minLength=15: −1 / +0 / +1 | 14 / 15 / 16 × `p` | invalid / valid / valid |
| `items[0].qty` | maximum=50: −1 / +0 / +1 | 49 / 50 / 51 | valid / valid / invalid |

Failed tests — exactly the 6 predicted, each expected 400 and got 200 because the server still applies the old rules:
`test_API_create_generated[createRequisition:purpose:EP:02]`, `[createRequisition:purpose:BVA:05]`, `[createRequisition:items[0].qty:BVA:09]`, `test_API_update_generated[updateRequisition:purpose:EP:02]`, `[updateRequisition:purpose:BVA:05]`, `[updateRequisition:items[0].qty:BVA:09]`.
The 4 new cases at 49 and 50 pass, so the pass count stays 188 (= 181 API/integration + 7 generator self-tests before the change, + 4 new − 4 regressions). Predicted vs actual: no difference.

What it shows: the spec is the single oracle — tightening it regenerates the data and the tests without editing any test code, and the pipeline blocks a stale data set (step 1) as well as a server that does not meet the new spec (step 4).
