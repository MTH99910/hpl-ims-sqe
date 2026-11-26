#!/usr/bin/env python
"""Restrict a Cosmic Ray session to the business-rule functions (marks the rest SKIPPED).

Mutating all of views.py would create hundreds of mutants in presentation code (context
dictionaries, messages, print debugging) that say nothing about the business rules and would
make the CI job too slow. The scope is the functions that implement BR-1..BR-4; it is found
by name with `ast`, so it follows the code if lines move.
"""
import ast
import sys
from pathlib import Path

from cosmic_ray.work_db import WorkDB, use_db
from cosmic_ray.work_item import WorkerOutcome, WorkResult

ROOT = Path(__file__).resolve().parents[3]
SCOPE = {
    "requisition/forms.py": {"RequisitionLineItemForm.clean_quantity_requested",
                             "RequisitionLineItemUpdateForm.__init__",
                             "RequisitionLineItemUpdateForm.clean_quantity_issued",
                             "HODActionForm.clean"},
    "requisition/models.py": {"Requisition.can_be_edited", "Requisition.can_be_approved",
                              "Requisition.can_be_sent_back", "Requisition.can_be_resubmitted",
                              "Requisition.can_be_issued", "Requisition.is_pending_action",
                              "RequisitionLineItem.is_fully_issued", "RequisitionLineItem.get_status_display"},
    "requisition/views.py": {"InitiatorRequiredMixin.test_func", "HODRequiredMixin.test_func",
                             "AdminRequiredMixin.test_func", "HODApprovalView.get_queryset",
                             "HODApprovalView.form_valid", "IssueItemsView.get_queryset",
                             "IssueItemsView.form_valid"},
}


def ranges(path, names):
    tree = ast.parse((ROOT / path).read_text())
    out = []
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        for fn in [n for n in cls.body if isinstance(n, ast.FunctionDef)]:
            if f"{cls.name}.{fn.name}" in names:
                out.append((fn.lineno, fn.end_lineno))
    return out


def main(db_path):
    scope = {p: ranges(p, n) for p, n in SCOPE.items()}
    keep, skip = 0, []
    with use_db(db_path, WorkDB.Mode.open) as db:
        for item in db.pending_work_items:
            m = item.mutations[0]
            line = m.start_pos[0]
            if any(a <= line <= b for a, b in scope.get(str(m.module_path), [])):
                keep += 1
            else:
                skip.append(item.job_id)
        db.set_multiple_results(skip, WorkResult(worker_outcome=WorkerOutcome.SKIPPED,
                                                 output="outside business-rule scope"))
    print(f"mutants in scope: {keep}   skipped (outside scope): {len(skip)}")


if __name__ == "__main__":
    main(sys.argv[1])
