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
