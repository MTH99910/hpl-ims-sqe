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
Spec change committed as its own PR (see `docs/14_ci_gate.md`): (1) `purpose.minLength` 10 → **15**, (2) `items[].qty` gets **`maximum: 50`**.
`python tests/team/datagen/generator.py` → case count and the new BVA rows (`minLength=15: 14/15/16`, `maximum=50: 49/50/51`) appear in `cases.json`/`cases.md`; the CI step `generator.py --check` fails until the generated file is refreshed; the API suite then shows which tests disagree with the unchanged server (purpose length 10–14 and qty 51 are now *expected* invalid but the server still accepts them) — exactly the prediction made before the run (see the PR description).
