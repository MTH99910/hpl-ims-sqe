# Mutation testing — business-rule module

**Tool:** Cosmic Ray 8.4.1 (`tests/team/mutation/cosmic-ray.toml`).
**Target (business-rule module):** the functions that implement BR-1…BR-4 in `requisition/forms.py`, `requisition/models.py` and `requisition/views.py` — selected by name with `filter_scope.py` (issue-quantity / requested-quantity validation, HOD decision form, `can_be_*`, `is_pending_action`, line-item status, the three role mixins, `HODApprovalView` and `IssueItemsView` query/transition/stock-posting code). The other 514 generated mutants (templates' context dictionaries, messages, debug printing) are marked *skipped* because they test presentation, not rules.
**Test command:** the white-box unit suite (`test_forms.py`, `test_models.py`, `test_views_workflows.py`, `test_mixins_and_misc.py`, `test_mutation_killers.py`) — ≈ 1 s per mutant.
**Score formula:** killed ÷ (killed + surviving non-equivalent). Equivalent mutants are excluded only after the written analysis below (`tests/team/mutation/equivalent.json`).

## 1. Custom operators (based on the business rules)

| Operator | Rule | Mutation | What a survivor would mean |
|---|---|---|---|
| `sqe/WorkflowStatusSwap` | BR-3 state change | a status literal is replaced by its "plausible wrong" neighbour (`pending_hod→authorized`, `authorized→issued`, `issued→authorized`, `sent_back→pending_hod`, …) | a guard or assignment of the lifecycle could point at the wrong state without any test noticing |
| `sqe/DropConjunct` | BR-2 decision | in an `a and b [and c]` chain one operand is removed (one mutant per operand) | an authority condition (role / department / status) could be deleted unnoticed — the MC/DC question "does every condition independently matter?" asked mechanically |
| `sqe/StockDeltaOffByOne` | BR-4 stock integrity | `x -= y` → `x -= (y + 1)` (also `+=`) | an off-by-one in a stock posting would not be caught |

Package: `tests/team/mutation/sqe_operators` (entry point `cosmic_ray.operator_providers → sqe`), self-tested by `tests/team/mutation/test_operators.py` (every documented example must mutate exactly as stated). In the scoped run they generated (run 2): WorkflowStatusSwap **23** (23 killed), DropConjunct **18** (16 killed, 2 equivalent: S01, S03), StockDeltaOffByOne **1** (1 killed) — counted from `reports/mutation/run2-after-kills.sqlite`.

## 2. Results

| Run | Mutants in scope | Killed | Survived | Equivalent (of the survivors) | Score (non-equivalent) | Raw score |
|---|---|---|---|---|---|---|
| Run 1 — baseline suite | 267 | 242 | 25 | 13 | **242 / 254 = 95.3 %** | 90.6 % |
| Run 2 — after `test_mutation_killers.py` | 267 | 254 | 13 | 13 | **254 / 254 = 100 %** | 95.1 % |

Raw evidence: `reports/mutation/run1-baseline-report.txt`, `run2-after-kills-report.txt` (with diffs) and the two session databases.

**A false start worth recording:** the very first run reported *0 survivors out of 267*. That was not a strong suite — the test command called `python`, which on this machine is Python 3.14 without Django, so every mutant "failed" and was counted as killed. The command now uses `.venv/bin/python`, and CI runs `cosmic-ray baseline` first, which fails if the *unmutated* suite does not pass.

## 3. Analysis of the 25 surviving mutants of run 1

| # | Location | Mutation | Class | Reasoning | Action |
|---|---|---|---|---|---|
| S01 | forms.py:93 | `self.instance and self.instance.pk` → `self.instance.pk` (DropConjunct) | **Equivalent** | A ModelForm always has an instance (Django creates an empty one), so the dropped operand is always truthy. | justified |
| S02 | forms.py:94 | `quantity_issued == 0` → `<= 0` | **Missing test** | No test had a negative stored `quantity_issued`; with the mutant the form would pre-fill the requested quantity for −1. | killed by UT144 |
| S03 | forms.py:111 | `item and qty > stock` → `qty > stock` (DropConjunct) | **Equivalent** | `item` is a non-null FK — the guard is defensive; same infeasible MCC row as in docs/11. | justified |
| S04 | models.py:166 | `status == 'pending_hod'` → `is` | **Weak assertion / test data** | Tests built objects from string literals, which CPython interns, so `is` happened to be true. A status read **from the database** is a new string object. | killed by UT140 (objects re-loaded from DB) |
| S05 | models.py:170 | same, `can_be_sent_back` | Weak test data | as S04 | killed by UT140 |
| S06 | models.py:174 | `== 'sent_back'` → `>= 'sent_back'` | **Equivalent** | Over the 7 valid statuses only `sent_back` sorts ≥ `'sent_back'`. | justified |
| S07 | models.py:174 | `== 'sent_back'` → `is` | Weak test data | as S04 | killed by UT140 |
| S08 | models.py:178 | `== 'authorized'` → `is` | Weak test data | as S04 | killed by UT140 |
| S09 | models.py:178 | `== 'authorized'` → `<=` | **Equivalent** | `authorized` is the smallest status alphabetically. | justified |
| S10 | models.py:182 | `== 'pending_hod'` → `>=` | **Missing test** | `>=` would also match `rejected` and `sent_back` — no test asked an HOD about a rejected / sent-back requisition. | killed by UT142 |
| S11 | models.py:182 | `== 'pending_hod'` → `is` | Weak test data | as S04 | killed by UT141 |
| S12 | models.py:183 | `initiator.department == user.department` → `is` | Weak test data | Both sides were the *same* fixture object; two separately loaded Department rows are equal but not identical. | killed by UT141 (fresh DB objects) |
| S13 | models.py:183 | drop `user.department and` (**custom DropConjunct**) | **Missing test — real gap** | Without the guard, `None == None` gives an HOD **without a department** authority over every initiator **without a department**. No test combined those two. | killed by UT143 |
| S14 | models.py:185 | `== 'authorized'` → `is` | Weak test data | as S04 | killed by UT141 |
| S15 | models.py:185 | `== 'authorized'` → `<=` | **Equivalent** | as S09 | justified |
| S16 | models.py:231 | `quantity_issued == 0` → `<= 0` | **Missing test** | negative issued quantity not tested for the line status text | killed by UT144 |
| S17 | views.py:474 | `user.is_hod and user.department` → `user.is_hod` (**custom DropConjunct**) | **Missing test — real gap** | Same hole as S13 at the view level: the HOD queryset would filter `initiator__department=None`. | killed by UT143 (HTTP 404 check) |
| S18 | views.py:494 | `form.save(commit=False)` → `commit=True` | **Equivalent** | The object is saved once more before the final `save()` at the end of `form_valid`; final state and notifications are identical. | justified |
| S19 | views.py:499 | `== 'sent_back'` → `>=` | **Equivalent** | domain argument as S06 | justified |
| S20 | views.py:499 | `== 'sent_back'` → `is` | **Equivalent** | Here the value was just assigned from the literal in `HODActionForm.clean()`; interned literal ⇒ identity holds on every reachable path. | justified |
| S21 | views.py:502 | `== 'authorized'` → `is` | **Equivalent** | as S20 | justified |
| S22 | views.py:502 | `== 'authorized'` → `<=` | **Equivalent** | as S09 | justified |
| S23 | views.py:510 | `== 'sent_back'` → `>=` | **Equivalent** | as S06 | justified |
| S24 | views.py:510 | `== 'sent_back'` → `is` | **Equivalent** | as S20 | justified |
| S25 | views.py:602 | `qty_issued > 0` → `!= 0` | **Equivalent** | Negative quantities are rejected before `form_valid`, so `> 0` and `!= 0` agree on every reachable value. | justified |

**Summary:** 25 analysed → **13 equivalent**, **12 killable** (5 missing tests, 7 weak test data/assertions) → all 12 killed in run 2.

**What the custom operators found:** `DropConjunct` produced the two most useful survivors (S13, S17) — a genuine untested combination in the BR-2 authority rule (department-less HOD vs department-less initiator). `WorkflowStatusSwap` mutants were all killed in run 1 — the state-transition tests already pin every literal. `StockDeltaOffByOne` was killed by the stock read-back assertions (UT62).

## 4. Threshold for the CI gate
Measured: 95.3 % with the first suite, 100 % after the analysis. Gate: **≥ 95 %** of non-equivalent mutants killed (`MUTATION_MIN` in `ci.yml`). Rationale: the baseline suite already reached 95.3 %, so a lower gate would accept a regression to a suite weaker than our *first* version; 100 % would make every new, not-yet-analysed equivalent mutant block a PR before it can be justified. A survivor must either be killed or be added to `equivalent.json` with a written reason in the same PR.
