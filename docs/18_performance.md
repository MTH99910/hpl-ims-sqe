# Performance and recovery

## 1. Targets (fixed before any measurement — committed ahead of the first k6 run)

**Operation measured:** `GET /requisition/{pk}/hod-approval/` — the screen an HOD opens to decide on a requisition (WF1). It authenticates the session, runs the department-scoped query of BR-2, and renders the line items with live stock, so it exercises the same code and data as the workflow. It is a read, so repeated runs do not change the data and every run starts from identical state.

| Workload | p95 response time | Unexpected failures | Why this limit |
|---|---|---|---|
| 1 simulated user | **≤ 300 ms** | **< 1 %** | One HOD working alone on a LAN. A form that appears within a few hundred ms feels instant; a single-user run must leave headroom for concurrency. |
| 5 simulated users at once | **≤ 800 ms** | **< 1 %** | Several HODs deciding at the same time (month-end). The 1-second limit for keeping a user's flow of thought uninterrupted, minus a safety margin; SQLite + 2 gunicorn workers on one laptop are the constraint. |

* **Unexpected failure** = any response that is not HTTP 200 **or** does not contain the decision form (`Submit Decision`). Login requests are not counted. There are no *expected* failures in this script.
* **p95** = 95 % of the measured requests completed within the limit.
* Measurement window: after a 15 s warm-up, **70 s** at the full number of users (≥ 60 s required).
* Same build (commit recorded in `results/env.txt`), same machine, same starting data (`golden.sqlite3` copied before every run), gunicorn with 2 workers (`MODE=perf`), think time 1 s per user.
* The limits are enforced as k6 thresholds in `tests/team/perf/approval_screen.js`, so each run prints PASS/FAIL against the target.

## 2. Results (4 comparable runs, 26 Nov 2026, same build / machine / starting data)

Raw output: `tests/team/perf/results/` — `summary-*.json` (k6 summary export), `raw-*.json.gz` (every sample), `console-*.txt` (k6 console incl. threshold verdicts), `server-*.log` (gunicorn), `env.txt` (machine, commit, versions).

| Run | VUs | Measured window | Requests (measured) | Requests / s | p95 (ms) | median (ms) | max (ms) | Unexpected failures | Target | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 VU – run 1 | 1 | 70 s | 70 | 1.00 | **5.42** | 5.07 | 5.76 | **0.00 %** | p95 ≤ 300, < 1 % | **PASS** |
| 1 VU – run 2 | 1 | 70 s | 70 | 1.00 | **5.45** | 5.13 | 5.92 | **0.00 %** | p95 ≤ 300, < 1 % | **PASS** |
| 5 VU – run 1 | 5 | 70 s | 350 | 5.00 | **6.18** | 5.16 | 257.73 | **0.00 %** | p95 ≤ 800, < 1 % | **PASS** |
| 5 VU – run 2 | 5 | 70 s | 350 | 5.00 | **6.00** | 5.12 | 229.79 | **0.00 %** | p95 ≤ 800, < 1 % | **PASS** |

**Interpretation**
* Both workloads are far inside their limits (p95 ≈ 2 % of the 1-VU limit and < 1 % of the 5-VU limit). Requests/s equals the number of users because each user waits 1 s between views (think time) — throughput is set by the workload model, not by a server limit.
* Repeatability: the two runs of each setup differ by < 0.2 ms at p95 (0.6 % and 3 %), so the measurements are stable on this machine.
* Concurrency effect: from 1 to 5 users p95 rises only ≈ 0.6 ms; the *max* rises to ≈ 230–260 ms — single requests queuing behind each other on the 2 sync gunicorn workers when several users arrive at the same moment. That tail is still well under the limit, but it is the first thing that would grow with more users (more workers or a server DB would be the remedy).
* Limits of the result: SQLite and a read-only operation; the write operations (approve/issue) take a write lock and would behave worse under concurrency — not measured here (one operation required), recorded as residual risk for PR-9.
* An earlier attempt was **invalid** (k6 resets cookies between iterations by default, so most requests were redirected to the login page); it is kept in `results/invalid-attempt-1/` with an explanation and was not used.

## 3. Failure and recovery (state-changing operation: WF2 issue)
`tests/team/integration/test_recovery.py` (pytest, real transactions):
* **REC01** — a test double makes `Item.save` raise `OperationalError("database is unavailable")` on the **second** stock write, i.e. after the first line has already been written. Response 500. Persisted state verified: status `authorized`, issuer empty, `quantity_issued` [0, 0], stock [10, 50], 0 outward transactions, 0 notifications — everything rolled back. Dependency restored → the **same request retried** → 302; final state: `issued`, issued [3, 2], stock [7, 48], exactly 2 outward transactions, 1 notification. A further repeat returns 404 and nothing changes (no duplicates).
* **REC02** — failure on the very first write (`Transaction.objects.create`) → no trace; retry succeeds with exactly one transaction.
* **REC03** — the same failure injected in the **create API** leaves an orphan requisition → defect **F6 (#5)** (xfail strict).
Result: 2 passed, 1 expected failure (defect).
