# Static analysis (SonarQube) and cyclomatic complexity

**Tool:** SonarQube Community Build 26.11.0.134175 (Docker `sonarqube:community`), scanner `pysonar` 1.11.0.6012, default *Sonar way* profile for Python.
**Runs:** (1) project `hpl-ims-baseline` = untouched upstream commit `549113c` (no team tests); (2) project `hpl-ims-sqe` = team repository with the unit suite and `coverage.xml` imported. Configuration: `sonar-project.properties`.

## 1. Metrics

| Metric | Baseline `549113c` | With team tests | What it tells us about this system |
|---|---|---|---|
| Lines of code (ncloc) | 2 834 | 2 834 | Small Django app; three apps (core, inventory, requisition). |
| Cyclomatic complexity (total) | 389 | 389 | ≈ 0.14 decisions per line. Concentrated in `requisition/views.py`: `update_requisition_api` **15**, `create_requisition_api` **13**, `RequisitionCreateView.form_valid` **13**, `RequisitionUpdateView.form_valid` **10** — exactly the functions where defects F6, F14, F15, F16 were found. |
| Cognitive complexity | 332 | 332 | Nesting in the JSON API views (validation loops inside `try`) makes them hard to read; matches the duplication below. |
| Duplications | 1.2 % lines, 2 blocks | same | The two blocks are the validation code copied between `create_requisition_api` and `update_requisition_api` — a fix in one is easy to forget in the other (F16 exists in both). |
| Code smells / maintainability issues | 0 | 0 | The Sonar way profile raises no smell for this code; maintainability rating **A**. (Debug `print` calls and the dead `return` are reported under other rules.) |
| Bugs / reliability issues | **1** | 1 | `python:S1763` unreachable code — the second `return context` in `RequisitionUpdateView.get_context_data` (`views.py:404`). Harmless itself, but it sits in the same view as F14/F15 and signals copy-paste editing. Reliability rating **C**. |
| Vulnerabilities / security issues | **19** | 19 | 9× `S3752` endpoints accept every HTTP method — most important: `cancel_requisition` **changes state on GET** (CSRF-able, logged as F19); 9× `S2245` pseudo-random generator in `seed_data.py` (test-data command — not a risk, reviewed as safe); 1× `S4507` `DEBUG = True` in `settings.py` (stack traces and settings leak on errors, see security report). Security rating **C**. |
| Security hotspots | 0 | 0 | Hard-coded `SECRET_KEY` and `ALLOWED_HOSTS=['*']` are **not** flagged by the default profile — found in the manual configuration review instead (shows the limit of the default rule set). |
| Coverage | **0.0 %** | **95.9 %** (lines 96.7 %, branches 92.6 %) | Upstream has no tests. With the team suite every *feasible* in-scope line/branch is covered; the remaining 4.1 % is the unreachable code behind F14 and three infeasible branches (justified in `docs/11_unit_testing.md`). |
| Technical debt | 0 min (ratio 0.0 %) | 0 min | Debt is computed from code smells only, so it is 0 — the real risk in this code is functional (defects) and security, not maintainability. |
| Ratings | Maintainability A · Reliability C · Security C · Security review A | same | Tests do not change ratings (they measure the code, not the tests). |

**Reading:** SonarQube's numbers point at the same places the dynamic testing found defects (the high-complexity JSON API and create/update views, the method-agnostic state-changing endpoint), but it **did not** detect any of the critical workflow defects (F3 missing role check, F4 invalid transition, F13 no stock deduction). Those are semantic/business-rule errors that a rule-based analyser cannot know about — which is why the risk register gives them deep dynamic testing.

## 2. Hand-calculated cyclomatic complexity — `RequisitionLineItemUpdateForm.clean_quantity_issued` (BR-1)

```python
 97 def clean_quantity_issued(self):
 99     qty_issued = self.cleaned_data['quantity_issued']          # N1
100     item = self.instance.item
101     qty_requested = self.instance.quantity_requested
103     if qty_issued < 0:                                         # N2  (P1)
104         raise ValidationError("Issued quantity cannot be negative.")          # N3
106     if qty_issued > qty_requested:                             # N4  (P2)
107         raise ValidationError(f"Cannot issue more than requested ...")         # N5
111     if item and qty_issued > item.quantity_total:              # N6 (P3a: item)  N7 (P3b: qty > stock)
112         raise ValidationError(f"Insufficient stock. ...")                      # N8
116     return qty_issued                                          # N9
                                                                  # N10 = exit
```

Control-flow graph (the short-circuit `and` is split into two predicate nodes, because each operand is a separate decision):

```
N1 → N2
N2 --T--> N3 → N10          N2 --F--> N4
N4 --T--> N5 → N10          N4 --F--> N6
N6 --T--> N7                N6 --F--> N9
N7 --T--> N8 → N10          N7 --F--> N9
N9 → N10
```

* Nodes **N = 10**, edges **E = 13** (N1→N2, N2→N3, N2→N4, N3→N10, N4→N5, N4→N6, N5→N10, N6→N7, N6→N9, N7→N8, N7→N9, N8→N10, N9→N10).
* **V(G) = E − N + 2 = 13 − 10 + 2 = 5.**
* Check 1 — predicates + 1: P1, P2, P3a, P3b = 4 → **5**.
* Check 2 — regions of the planar graph: 4 bounded + 1 outer = **5**.

**Basis paths (5) and the tests that execute them:**

| Path | Route | Example | Test |
|---|---|---|---|
| B1 | N2 T | qty −1 | UT30 (−1) |
| B2 | N2 F → N4 T | req 4, qty 5 | UT31 (5) |
| B3 | N4 F → N6 T → N7 T | req 6, stock 4, qty 5 | UT32 (5) |
| B4 | N6 T → N7 F → N9 | qty 3 | UT31 (3) |
| B5 | N6 F → N9 | `item` empty | **infeasible** — `RequisitionLineItem.item` is a non-null FK, so P3a is always true; also confirmed by the equivalent mutant S03 (`DropConjunct` on this `and` survives). |

**SonarQube value:** 5 (read by temporarily activating rule `python:FunctionComplexity` with threshold 1 in a copy of the profile — the issue message states "Function has a complexity of 5"). **Hand value = tool value = 5.**

### Second function — `Requisition.is_pending_action` (BR-2), where the numbers differ
Atomic predicates: `user.is_hod`, `status == 'pending_hod'`, `user.department`, `initiator.department == user.department`, `user.is_admin`, `status == 'authorized'` → 6 predicate nodes → **V(G) = 7** by hand.
SonarQube reports **6**. Sonar's Python metric adds 1 per function, per `if` statement and per boolean-operator sequence; in its syntax tree the `elif` branch belongs to the parent `if` statement and is not counted as a separate decision, so the hand count (which treats `elif` as its own decision node in the CFG) is one higher. Both agree that the function needs 7 tests for full basis-path coverage at condition level — the MCC table in `docs/11_unit_testing.md` uses 8 rows.
