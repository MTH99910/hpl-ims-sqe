# White-box unit testing

**Tools:** pytest 8.3.5 + pytest-django 4.11.1, coverage.py 7.8.0 with branch measurement (`.coveragerc`), gate `scripts/team/coverage_gate.py`.
**Suite:** `tests/team/unit/` — 237 test cases (227 pass, 10 `xfail(strict=True)` that expose confirmed defects; strict = they turn red the moment the defect is fixed).

```
FAST_HASH=1 .venv/bin/pytest tests/team/unit --cov --cov-report=json:reports/tmp/coverage.json --cov-report=html:reports/coverage
.venv/bin/python scripts/team/coverage_gate.py reports/tmp/coverage.json
```

## 1. Scope of "server-side business logic" and coverage result

| Scope | Files / functions | Statements | Branches | Result |
|---|---|---|---|---|
| Full files | `requisition/models.py`, `requisition/forms.py`, `requisition/views.py`, `inventory/models.py`, `core/models.py` | 794 | 202 | 100 % of feasible statements and branches |
| Endpoint functions used by the workflows | `core/views.py`: `login_view`, `logout_view`, `notifications_list`, `notifications_api`, `mark_notification_read`, `mark_all_notifications_read`, `create_notification`; `inventory/views.py`: `get_item_details` | (per function) | (per function) | 100 % |

Raw report (coverage.py): requisition/models.py 100 %, requisition/forms.py 100 %, inventory/models.py 100 %, core/models.py 100 %, requisition/views.py 93 % — the difference is exactly the justified code in §2. The gate fails CI if any other line or branch is uncovered, **and** if a justification becomes stale (code covered but still listed).

**Omitted files and why** (they are not business logic of WF1/WF2):
* `*/migrations/*` — generated schema; `*/admin.py`, `*/apps.py`, `*/urls.py`, `*/__init__.py` — declarative configuration.
* `core/forms.py`, rest of `core/views.py` — Super Admin user/department management and Excel upload: not part of either workflow (test basis §7).
* `inventory/forms.py`, rest of `inventory/views.py` — item/location CRUD and stock adjustment screens: not part of either workflow.
* `core/management/commands/seed_data.py`, `scripts/` — test-data tooling.

## 2. Uncovered code — justification (`tests/team/coverage_allowlist.json`)

| Code | Why it cannot be covered |
|---|---|
| `requisition/views.py:348` (`RequisitionUpdateView.get_success_url`) and `411–459` (rest of `RequisitionUpdateView.form_valid`) | **Unreachable on the baseline because of defect F14**: line 410 reads `cleaned_data` from an *unbound* formset and always raises `AttributeError`, so nothing after it can run. Test UT97 (xfail, strict) documents it. The same behaviour is tested through the JSON update API (UT107–UT114). Inside this block, lines 428–433 are dead even after a fix (the loop only receives items that are *not* marked DELETE, yet checks for DELETE). |
| Branch `views.py 299→298` and `578→577` (`if errors:` false edge) | **Infeasible**: Django only puts a field in `form.errors` when it has at least one error, so the list is never empty. |
| Branch `views.py 324→323` (`if item_data.get('item')` false edge) | **Infeasible**: `item` is a required field; a valid, non-deleted line always has one. |
| `views.py:404` (second `return context`) | Unreachable statement after a `return`; coverage.py does not count it as a statement, SonarQube reports it as bug S1763. |

## 3. All four business rules — where they are tested

| Rule | Unit tests |
|---|---|
| BR-1 issue quantity limits | UT30–UT38 (3-point BVA at 0, at requested, at stock; zero-stock item; check order), UT62/UT64/UT65 (view level) |
| BR-2 approval authority + reason rule | UT09 (MCC table D1), UT43 (DT-2), UT50–UT52, UT58, UT130, UT141–UT143 |
| BR-3 lifecycle | UT08, UT140 (all states, from memory and from DB), UT52, UT57, UT59, UT61, UT67, UT98 |
| BR-4 stock integrity | UT62, UT63 (F13), UT64, UT67, UT68 (rollback), UT70 (F7) |

## 4. Critical module — complete MCC, then MC/DC pairs

Critical module = the BR-2 / BR-1 decisions. For each decision every combination of its atomic conditions is listed (MCC). Python short-circuits `and`, so a later condition is *not evaluated* when an earlier one is false — written "–" (masked). Rows that cannot occur in the application are marked infeasible.

### D1 — `Requisition.is_pending_action(user)` (BR-2)
```
if A and B:            A = user.is_hod          B = status == 'pending_hod'
    if C and D:        C = user.department      D = initiator.department == user.department
        return True
elif E and F:          E = user.is_admin        F = status == 'authorized'
    return True
return False
```
Roles are exclusive (A and E cannot both be true).

| Row | A | B | C | D | E | F | Result | Test (UT09 row) |
|---|---|---|---|---|---|---|---|---|
| M1 | T | T | T | T | – | – | **True** | M1 hod_it / pending |
| M2 | T | T | T | F | – | – | False | M2 hod_hr / pending |
| M3 | T | T | F | – | – | – | False | M3 hod_nodept / pending |
| M4 | T | F | – | – | F | – | False | M4 hod_it / authorized |
| M5 | F | – | – | – | T | T | **True** | M5 admin / authorized |
| M6 | F | – | – | – | T | F | False | M6 admin / pending |
| M7 | F | – | – | – | F | – | False | M7 initiator / authorized |
| M8 | F | – | – | – | F | – | False | M8 initiator / pending |
| — | T | – | – | – | T | – | infeasible (a user has one role) | – |

Extra rows added after mutation analysis: HOD without department vs initiator without department (C = F while D would be `None == None` = T) — UT143; HOD with rejected / sent-back status — UT142; objects re-loaded from DB — UT141.

**MC/DC pairs (from the table):** for each condition, two rows that differ only in that condition (others fixed or masked identically) and whose outcomes differ.

| Condition | Pair | Outcome change |
|---|---|---|
| A (is_hod) | **M1 vs M8** — same pending IT requisition, both users in IT (B, C, D true in both), neither is admin (E = F); only the role changes | True → False |
| B (pending) | **M1 vs M4** | True → False |
| C (department) | **M1 vs M3** | True → False |
| D (same dept) | **M1 vs M2** | True → False |
| E (is_admin) | **M5 vs M7** (F=T both: admin vs initiator on an authorized requisition) | True → False |
| F (authorized) | **M5 vs M6** | True → False |

Minimal MC/DC set: {M1, M2, M3, M4, M5, M6, M7/M8} = 7 tests (= N + 1 for 6 conditions), all included in UT09.

### D2 — `clean_quantity_issued` stock check (BR-1): `if P and Q` with P = `item`, Q = `qty > stock`

| Row | P | Q | Raises | Test |
|---|---|---|---|---|
| 1 | T | T | yes | UT32 (5 > 4) |
| 2 | T | F | no | UT32 (3, 4) |
| 3 | F | – | no | **infeasible** — `item` is a non-null FK (equivalent mutant S03 confirms) |

MC/DC: Q → rows 1 vs 2. P has no feasible independence pair (row 3 impossible) — documented as defensive code.

### D3 — `HODActionForm.clean` reason rule (BR-2 companion)
`if R1 and not X` with R1 = `action == 'rejected'`, X = rejection_reason present; `if S1 and not Y` with S1 = `action == 'sent_back'`, Y = sent_back_reason present.

| Row | action | X | Y | error on | Test (UT43) |
|---|---|---|---|---|---|
| 1 | authorized | F | F | – | R1 |
| 2 | authorized | T | T | – | R2 |
| 3 | rejected | F | F | rejection_reason | R3 |
| 4 | rejected | T | F | – | R4 |
| 5 | rejected | F | T | rejection_reason | R7 |
| 6 | sent_back | F | F | sent_back_reason | R5 |
| 7 | sent_back | F | T | – | R6 |
| 8 | sent_back | T | F | sent_back_reason | R8 |

MC/DC: R1 → rows 3 vs 6 (only action changes, reason absent: error field differs); X → rows 3 vs 4; S1 → rows 6 vs 1; Y → rows 6 vs 7.

### D4 — `HODApprovalView.get_queryset`: `elif user.is_hod and user.department`
| Row | is_hod | department | Queryset | Test |
|---|---|---|---|---|
| 1 | T | T | own-department pending | UT50 |
| 2 | T | F | empty → 404 | UT51 (hod_nodept), UT143 |
| 3 | F | – | empty → 404 (non-admin) | UT51 (user_it, superadmin) |
MC/DC: is_hod → 1 vs 3; department → 1 vs 2.

## 5. Defects found by the unit suite (xfail strict)
F3 (UT69), F4 (UT58, UT59), F5 (UT121), F6 (UT105), F7 (UT70), F13 (UT63), F14 (UT97), F15 (UT95b).
