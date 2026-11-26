# Upstream reference

| Field | Value |
|---|---|
| Upstream repository | https://github.com/arijit258/Inventory-Management-System |
| Baseline commit | `549113c379bd93b0090267c372f91a6dcc57e4f0` ("Update README.md") — tagged `baseline-upstream` in this repo |
| Cloned on | 2026-11-26 |
| Licence | **No LICENSE file in the repository.** README §License: "This project is provided for educational and organizational use. Modify and extend the application as needed." Used here for an educational assignment, consistent with that statement. Tracked as project risk PJ-3. |
| Stack | Python / Django 4.2 (tested on 4.2.30, Python 3.12.16), SQLite, Bootstrap 5, server-rendered forms + JSON endpoints |
| Module under test | Requisition — WF1 HOD approval, WF2 Admin issue |

All team work lives in `tests/team/`, `scripts/team/`, `docs/` and `.github/`. Any change to upstream application code is made only through a documented, reviewed pull request (defect fixes / accessibility fix).

Note: upstream commits compiled `__pycache__/*.pyc` files. They are untracked in the first team commit (they are build artefacts, not source) — the baseline tag still points at the untouched upstream state.
