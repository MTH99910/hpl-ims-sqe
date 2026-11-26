#!/usr/bin/env python
"""CI coverage gate for the in-scope server-side business logic.

Reads coverage.py's JSON report and fails (exit 1) unless:
  * every FULL-SCOPE file has 100% statement and 100% branch coverage, and
  * every listed FUNCTION in a partially-scoped file has 100% statement and branch coverage,
except for lines/branches listed in tests/team/coverage_allowlist.json - each entry there
carries a written justification (infeasible branch, or unreachable because of a logged defect).
An allowlist entry that is no longer needed (because it became covered) also fails the gate,
so the list can never silently hide code.

Usage:  python scripts/team/coverage_gate.py reports/tmp/coverage.json
"""
import json
import sys
from pathlib import Path

FULL_SCOPE = ["requisition/models.py", "requisition/forms.py", "requisition/views.py",
              "inventory/models.py", "core/models.py"]
FUNCTION_SCOPE = {
    "core/views.py": ["login_view", "logout_view", "notifications_list", "notifications_api",
                      "mark_notification_read", "mark_all_notifications_read", "create_notification"],
    "inventory/views.py": ["get_item_details"],
}
ALLOWLIST = Path(__file__).resolve().parents[2] / "tests/team/coverage_allowlist.json"


def fmt_branch(b):
    return f"{b[0]}->{b[1]}"


def main(report_path):
    data = json.loads(Path(report_path).read_text())["files"]
    allow = json.loads(ALLOWLIST.read_text())
    ranges = [(e["file"], e["from"], e["to"]) for e in allow["lines"]]
    allowed_branches = {(e["file"], e["branch"]) for e in allow["branches"]}
    problems, used_ranges, used_branches = [], set(), set()

    def in_range(path, ln):
        for r in ranges:
            if r[0] == path and r[1] <= ln <= r[2]:
                used_ranges.add(r)
                return True
        return False

    def check(path, missing_lines, missing_branches, label):
        for ln in missing_lines:
            if not in_range(path, ln):
                problems.append(f"{label}: line {ln} not covered")
        for br in missing_branches:
            key = (path, fmt_branch(br))
            if key in allowed_branches:
                used_branches.add(key)
            elif not in_range(path, br[0]):   # branch inside a justified unreachable block
                problems.append(f"{label}: branch {fmt_branch(br)} not covered")

    for path in FULL_SCOPE:
        f = data[path]
        check(path, f["missing_lines"], f["missing_branches"], path)
    for path, funcs in FUNCTION_SCOPE.items():
        for name in funcs:
            fn = data[path]["functions"][name]
            check(path, fn["missing_lines"], fn["missing_branches"], f"{path}::{name}")

    stale = [f"{p}:{a}-{b}" for p, a, b in sorted(set(ranges) - used_ranges)]
    stale += [f"{p}:{b}" for p, b in sorted(allowed_branches - used_branches)]
    for s in stale:
        problems.append(f"allowlist entry no longer needed (now covered): {s} - remove it")

    total_stmts = sum(data[p]["summary"]["num_statements"] for p in FULL_SCOPE)
    total_br = sum(data[p]["summary"]["num_branches"] for p in FULL_SCOPE)
    print(f"In-scope files: {len(FULL_SCOPE)} full + {sum(map(len, FUNCTION_SCOPE.values()))} functions; "
          f"{total_stmts} statements, {total_br} branches")
    print(f"Justified uncovered: {len(used_ranges)} line ranges, {len(used_branches)} infeasible branches "
          f"(see tests/team/coverage_allowlist.json)")
    if problems:
        print("COVERAGE GATE FAILED:\n  " + "\n  ".join(problems))
        return 1
    print("COVERAGE GATE PASSED: 100% of feasible in-scope statements and branches covered")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "reports/tmp/coverage.json"))
