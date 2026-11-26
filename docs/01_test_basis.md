# Test basis — Requisition module (WF1 HOD approval, WF2 Admin issue)

**SUT:** HPL Inventory Management System, upstream `549113c` (see `UPSTREAM.md`).
**Sources used:** upstream `README.md` (sections *User Roles & Permissions*, *Workflow*, *API Endpoints*), the source code at the baseline commit, and the justified assumptions in §6. Where README and code disagree, the README is treated as the specification and the code behaviour is reported as a defect, unless an assumption below says otherwise.

## 1. Workflows

| | WF1 — HOD approves a pending requisition | WF2 — Admin issues the authorized requisition |
|---|---|---|
| Starting condition | Requisition R is `pending_hod`; its initiator belongs to department D; the logged-in user is the HOD of D. Item ST001 has stock 10; R requests 4. | R is `authorized` (output of WF1); the logged-in user is an Admin; ST001 stock 10; no outward transaction references R. |
| User action | HOD dashboard → R → *Authorize* → *Submit Decision* | Admin dashboard → R → *Issue Items* (quantity pre-filled with 4) → *Issue Items* |
| Expected outcome | Message "Requisition REQ-… has been approved."; R.status = `authorized`, `hod_approver` = HOD, `hod_action_date` set; initiator and every Admin notified; **stock unchanged (10)** | Message "Items issued for requisition REQ-…"; R.status = `issued`, `issuer` = Admin, `issued_date` set; **ST001 stock = 6**; exactly one outward Transaction (−4, balance_after 6, reference = R's number); initiator notified; a second issue attempt is refused and stock stays 6 |
| Negative example | HOD of another department opens R → not found (404); R stays `pending_hod` | Issue 11 with stock 10 → "Insufficient stock. Available: 10…", R stays `authorized`, stock 10, no transaction |

**Value changed by one workflow and used by the other:** `Requisition.status`. WF1 writes `authorized`; WF2's issue view only accepts requisitions whose status is `authorized` (`IssueItemsView.get_queryset`) and writes `issued`. A second shared value is `Item.quantity_total`: WF1 displays it to the HOD on the approval screen, WF2 validates the issue against it and decrements it.

## 2. Shared records — who reads / writes what

| Record / field | WF1 reads | WF1 writes | WF2 reads | WF2 writes |
|---|:-:|:-:|:-:|:-:|
| Requisition.status | ✔ | ✔ | ✔ | ✔ |
| Requisition.hod_approver / hod_action_date | | ✔ | ✔ (shown) | |
| Requisition.sent_back_reason / sent_back_at / rejection_reason | | ✔ | | |
| Requisition.issuer / issued_date | | | | ✔ |
| RequisitionLineItem.quantity_requested | ✔ | | ✔ (upper limit) | |
| RequisitionLineItem.quantity_issued | | | ✔ | ✔ |
| Item.quantity_total | ✔ (shown) | | ✔ (limit) | ✔ |
| inventory.Transaction | | | | ✔ (outward row) |
| core.Notification | | ✔ | | ✔ |
| User.role / User.department | ✔ | | ✔ | |

## 3. Functional requirements

| ID | WF | Requirement | Source |
|---|---|---|---|
| FR-01 | 1 | The HOD dashboard lists only `pending_hod` requisitions whose initiator is in the HOD's department. | README "approval scope is limited to users within their assigned department"; `HODDashboardView` |
| FR-02 | 1 | The HOD can open the approval screen (header, line items, current stock) only for requisitions in scope. | README; `HODApprovalView` |
| FR-03 | 1 | *Authorize* sets status `authorized`, records the approving HOD and the action time, and confirms with a message. | README Workflow |
| FR-04 | 1 | *Reject* requires a rejection reason; the requisition becomes `rejected` and the reason is stored. | README; `HODActionForm.clean` |
| FR-05 | 1 | *Send back* requires comments; the requisition becomes `sent_back` and the time is recorded. | README; `HODActionForm.clean` |
| FR-06 | 1 | On authorization the initiator and all Admins are notified; on reject / send back the initiator is notified. | README ("notifies admins") |
| FR-07 | 2 | The Admin dashboard lists `authorized` requisitions awaiting issue. | README; `AdminDashboardView` |
| FR-08 | 2 | The issue form pre-fills each line's issued quantity with the requested quantity. | `RequisitionLineItemUpdateForm.__init__` |
| FR-09 | 2 | The Admin may issue a partial quantity per line (0 ≤ issued ≤ requested). | README "supporting partial fulfillment" |
| FR-10 | 2 | Issuing reduces `Item.quantity_total` by the issued quantity and records one outward Transaction per issued line (> 0) with `balance_after` and the requisition number as reference. | README "inventory quantities are reduced, transactions are recorded" |
| FR-11 | 2 | After issue: status `issued`, issuer and issue time recorded, initiator notified, confirmation message. | README |
| FR-12 | 2 | An issue that exceeds stock or the requested quantity is refused with a message that says what to correct, and nothing is saved. | `clean_quantity_issued`; `transaction.atomic` |
| FR-13 | 2 | A requisition that is not `authorized` (including one already issued) cannot be issued; repeating the request creates no duplicate transaction. | `IssueItemsView.get_queryset` |
| FR-14 | entry to WF1 | An initiator can create a requisition (purpose ≥ 10 characters, ≥ 1 item, quantity ≥ 1); it starts `pending_hod` and the department's HODs are notified. | README; `create_requisition_api` |
| FR-15 | re-entry to WF1 | An initiator can revise a `sent_back` requisition; it returns to `pending_hod`, the send-back data is cleared and HODs are notified again. | README; `update_requisition_api` |

## 4. Business rules

| ID | Kind | Rule | Implemented in |
|---|---|---|---|
| **BR-1** | Boundary / limit | For every line: **0 ≤ quantity_issued ≤ min(quantity_requested, item.quantity_total)**. Outside the range the issue is refused with a message naming the limit. (Supporting limits on creation: purpose length ≥ 10 after trimming; quantity ≥ 1.) | `forms.py` `clean_quantity_issued`; `views.py` `create_requisition_api` |
| **BR-2** | Decision (≥ 2 Boolean conditions) | A user may act on R as approver **iff** C1 role = HOD **and** C2 the user has a department **and** C3 R's initiator is in that department **and** C4 R.status = `pending_hod`. Companion rule: a reason is required **iff** (action = reject **and** rejection reason empty) **or** (action = send back **and** comments empty). | `models.py` `is_pending_action`; `views.py` `HODApprovalView.get_queryset`; `forms.py` `HODActionForm.clean` |
| **BR-3** | Change of state | Lifecycle: `pending_hod → authorized / sent_back / rejected` (HOD only); `sent_back → pending_hod` (initiator resubmits); `draft / pending_hod → cancelled` (initiator); `authorized → issued` (Admin only). `issued`, `rejected`, `cancelled` are final. | `models.py` `can_be_*`; views |
| **BR-4** | Stock integrity (cross-workflow) | An issue is all-or-nothing; stock falls by exactly the issued quantity; each issued line has exactly one outward Transaction with `balance_after = old − issued`; stock never becomes negative. | `views.py` `IssueItemsView.form_valid` |

## 5. Roles

| Role | May | Must not |
|---|---|---|
| **HOD** | view and act on (authorize / send back / reject) `pending_hod` requisitions of their own department; create own requisitions | act on other departments' requisitions; **issue items** |
| **Admin** | view all requisitions; issue `authorized` requisitions; manage items and stock | **approve requisitions** (README: approval and issuing are separate duties) |
| Initiator *(supporting)* | create, revise (when sent back) and cancel (before HOD action) own requisitions | approve or issue |
| Super Admin *(negative case only)* | user/department administration | "cannot directly approve requisitions or issue items" (README) |

## 6. Justified assumptions (recorded where the documentation is silent or contradicts the code)

| ID | Assumption | Reason |
|---|---|---|
| A1 | Only HODs approve and only Admins issue. Code that lets an Admin approve, or any logged-in user issue, is a **defect**. | README *Super Admin*: "these functions are reserved for HODs and Admins respectively. This separation of duties ensures proper checks and balances." |
| A2 | An HOD approving a requisition they raised themselves is **allowed** (recorded as an observation, not a defect). | README is silent; the code allows it; no rule forbids it. |
| A3 | "Leave it pending" is not a transition — it means no action is taken. | README lists it among the HOD's options but there is no control for it. |
| A4 | "Cancelled with the reason recorded" is **not implemented** (no reason field); logged as a documentation mismatch, out of the functional scope. | README *Workflow* vs `cancel_requisition`. |
| A5 | JSON endpoints should answer unauthenticated callers with 401/403 JSON. The observed 302 redirect to the HTML login page is reported as an endpoint weakness. | Usual HTTP API contract; README calls them "REST API endpoints". |
| A6 | The pre-filled issue quantity is the intended normal path (FR-08), so issuing it must deduct stock exactly like a typed quantity. | README "issues the items, which automatically deducts quantities". |
| A7 | The `draft` state exists in the model but no code path creates it; it is treated as a dead state and only tested at unit level with a fixture row. | Source code: default status is `pending_hod`; no view sets `draft`. |
| A8 | The HTTP interface of WF1/WF2 is the form-encoded POST endpoints `/requisition/{pk}/hod-approval/` and `/requisition/{pk}/issue/`, plus the JSON create/update/read endpoints. All are documented in `tests/team/datagen/openapi.yaml`. | These are HTTP endpoints with fixed request/response contracts that any HTTP client can call; the application has no separate REST layer for the two actions. |

## 7. Scope

**In scope:** requisition app (models, forms, all views incl. create/update/cancel and JSON APIs), `inventory.Item` / `Transaction` / `Location` models, `core.User` role logic and `Notification`, and the endpoints used by the workflows: login/logout, notifications API, item look-up APIs.

**Out of scope (not part of either workflow):** Super Admin user and department management, Excel item upload, item/location CRUD and stock adjustment screens, Django admin. These are only touched by the access-control smoke checks.
