# Use cases (browser end-to-end)

Two use cases per member, derived from the functional requirements in `01_test_basis.md`. Every flow below — main, alternative and exception — is automated in Playwright (Chromium) in `tests/team/e2e/uc/`, and each test asserts **both** what the screen shows **and** the postconditions on the persisted records (read back with `helpers/db_state.py`: status, approver/issuer, issued quantity, stock, outward transactions, notifications).

Seeded starting data: `scripts/team/seed_team.py` (reset before every test). Password for all accounts: `Test@12345`.

---

## UC-01 — HOD authorizes a pending requisition  (owner: Member A)
**Actor:** HOD (`hod_it`) · **Requirements:** FR-01, FR-02, FR-03, FR-06 · **Rules:** BR-2, BR-3
**Preconditions:** a requisition in `pending_hod` raised by an initiator of the HOD's department ("Pens for new IT interns batch", ST001 × 4); ST001 stock 10; HOD logged in.
**Trigger:** the HOD opens the pending queue.

**Main flow**
1. HOD logs in and lands on the HOD dashboard, which lists the department's pending requisitions.
2. HOD clicks **Review** on the requisition.
3. The approval screen shows header, purpose and line items with current stock.
4. HOD selects **Authorize** and clicks **Submit Decision**.
5. The system records the decision and shows "Requisition REQ-… has been approved." on the dashboard; the requisition is no longer offered for review.

**Alternative flows**
* **A1 – Authorize with notes:** at step 4 the HOD also types *Additional Notes* for the Admin → notes are stored with the requisition.
* **A2 – Start from the requisition detail page:** instead of steps 1–2 the HOD opens the requisition's detail page and clicks **Review & Approve**; a multi-line requisition shows every line before the decision.

**Exception flows**
* **E1 – Requisition of another department:** it is not listed on the HOD dashboard; opening its approval URL directly returns *404 Not Found*; nothing changes.
* **E2 – Already decided in another tab:** the HOD has the form open in two tabs, sends the requisition back in tab 2, then submits *Authorize* in tab 1 → *404*; the first decision (sent back) stands and only one notification exists.

**Postconditions** — success: status `authorized`, `hod_approver` = HOD, `hod_action_date` set, notifications `requisition_approved` for the initiator and every Admin, stock unchanged. Failure: status still `pending_hod`, no notifications.

**Automation:** `uc01-hod-authorize.spec.ts` — `UC-01 main`, `A1`, `A2`, `E1`, `E2`.

---

## UC-02 — HOD sends a requisition back for revision  (owner: Member B)
**Actor:** HOD (`hod_it`) · **Requirements:** FR-04, FR-05, FR-06 · **Rules:** BR-2 (reason rule), BR-3
**Preconditions:** as UC-01.

**Main flow**
1. HOD opens the requisition from the dashboard (**Review**).
2. HOD selects **Send Back**; the *Comments for Revision* field appears.
3. HOD enters the comments and clicks **Submit Decision**.
4. The system shows "Requisition REQ-… has been sent back for revision."

**Alternative flows**
* **A1 – Reject instead:** at step 2 the HOD selects **Reject**, enters a *Reason for Rejection* and submits → status `rejected`, reason stored, initiator notified.
* **A2 – Change the decision before submitting:** the HOD first selects **Authorize** (no comment field shown), then changes to **Send Back** and continues at step 3.

**Exception flows**
* **E1 – Send back without comments:** the browser blocks submission (required field); the page stays on the form; nothing is saved.
* **E2 – Reject without a reason (server check):** with the browser check bypassed, the server refuses the decision ("Rejection reason is required.") and nothing is saved. **Defect F20 (#13):** the error is rendered inside the hidden reason section, so the user cannot see it — the test is marked `test.fail` until the fix.

**Postconditions** — success: status `sent_back` (or `rejected` in A1) with the comment/reason and timestamp, initiator notified (`requisition_sent_back` / `requisition_rejected`). Failure: status `pending_hod`, no reason stored, no notifications.

**Automation:** `uc02-hod-send-back.spec.ts` — `UC-02 main`, `A1`, `A2`, `E1`, `E2`.

---

## UC-03 — Admin issues an authorized requisition in full  (owner: Member A)
**Actor:** Admin (`admin`) · **Requirements:** FR-07, FR-08, FR-10, FR-11, FR-12, FR-13 · **Rules:** BR-1, BR-3, BR-4
**Preconditions:** a requisition in `authorized` ("Pens for IT helpdesk counter", ST001 × 4, stock 10); Admin logged in.

**Main flow**
1. Admin logs in and lands on the Admin dashboard listing authorized requisitions.
2. Admin clicks **Issue Items**.
3. The issue screen pre-fills each line's quantity with the requested quantity (4).
4. Admin clicks **Issue Items & Complete**.
5. The system shows "Items issued for requisition REQ-…".

**Alternative flows**
* **A1 – Start from the detail page:** Admin opens the requisition detail page and clicks **Issue Items** (single-line paper requisition, stock = requested).
* **A2 – Multi-line requisition, quantities typed:** for a two-line requisition the Admin types each line's quantity and a note, then submits once.

**Exception flows**
* **E1 – Quantity above stock:** ST002 requested 3 with stock 1 → "Insufficient stock. Available: 1, Requested: 3."; nothing saved.
* **E2 – Already issued in another tab:** the requisition is issued in tab 2; submitting tab 1 returns *404*; exactly one outward transaction exists.

**Postconditions** — success: status `issued`, issuer = Admin, issued quantities stored, stock reduced by exactly the issued amount, one outward transaction per issued line, initiator notified. Failure: status `authorized`, stock and transactions unchanged.

**Defect F13 (#1):** in the main flow and A1 the pre-filled quantity is not saved, so stock is **not** reduced although the requisition shows *Issued*. These two tests are marked `test.fail` (they fail on the baseline, as expected) and become normal tests in the fix PR.

**Automation:** `uc03-admin-issue-full.spec.ts` — `UC-03 main`, `A1`, `A2`, `E1`, `E2`.

---

## UC-04 — Admin issues a partial quantity  (owner: Member B)
**Actor:** Admin · **Requirements:** FR-09, FR-10, FR-12 · **Rules:** BR-1, BR-4
**Preconditions:** an authorized requisition; Admin logged in.

**Main flow**
1. Admin opens the issue screen of the requisition (ST001 requested 4).
2. Admin changes the quantity to 2 and submits.
3. The system confirms the issue; the detail page shows the line as **Partial**.

**Alternative flows**
* **A1 – Zero on one line:** for a two-line requisition the Admin issues 0 of ST001 and 4 of HK002 → only HK002 gets an outward transaction.
* **A2 – Stock lower than requested:** ST002 requested 3, stock 1 → the Admin issues exactly 1; the item becomes *Out of Stock* in the inventory list.

**Exception flows**
* **E1 – More than requested:** 5 for a request of 4 → "Cannot issue more than requested (4)."; nothing saved.
* **E2 – Negative quantity:** −1 → blocked by the field's minimum (0); nothing saved.

**Postconditions** — success: status `issued`; each line's `quantity_issued` equals the typed value; stock reduced by exactly that amount; outward transactions only for lines > 0. Failure: status `authorized`, nothing changed.

**Automation:** `uc04-admin-issue-partial.spec.ts` — `UC-04 main`, `A1`, `A2`, `E1`, `E2`.

---

## Results (Playwright, Chromium 136)
All 20 use-case flows + 2 usability tasks ran: **22 passed** (including the 3 flows that are expected to fail because of F13 and F20 — Playwright counts an expected failure that does fail as a pass). Report: `reports/playwright/index.html`.
