#!/usr/bin/env python
"""E2E helper (called from Playwright through child_process).

  db_state.py reset                 copy the golden seeded DB over the E2E DB
  db_state.py state "<purpose>"     JSON snapshot of one requisition + its shared records

Used to assert POSTCONDITIONS directly on the persisted records after a UI flow.
"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.team.settings_test")
os.environ.setdefault("TEAM_DB", str(ROOT / "tests/team/data/e2e.sqlite3"))


def reset():
    shutil.copyfile(ROOT / "tests/team/data/golden.sqlite3", os.environ["TEAM_DB"])
    print(json.dumps({"reset": os.environ["TEAM_DB"]}))


def state(purpose):
    import django
    django.setup()
    from core.models import Notification
    from inventory.models import Transaction
    from requisition.models import Requisition
    r = Requisition.objects.get(purpose=purpose)
    print(json.dumps({
        "pk": r.pk, "number": r.requisition_number, "status": r.status,
        "hod_approver": r.hod_approver.username if r.hod_approver else None,
        "issuer": r.issuer.username if r.issuer else None,
        "rejection_reason": r.rejection_reason, "sent_back_reason": r.sent_back_reason, "notes": r.notes,
        "lines": [{"code": li.item.material_code, "requested": li.quantity_requested,
                   "issued": li.quantity_issued, "stock": li.item.quantity_total}
                  for li in r.items.select_related("item").order_by("pk")],
        "outward": [{"code": t.item.material_code, "change": t.quantity_change, "balance_after": t.balance_after}
                    for t in Transaction.objects.filter(reference=r.requisition_number, transaction_type="outward")],
        "notifications": sorted(f"{n.user.username}:{n.notification_type}"
                                for n in Notification.objects.filter(title__endswith=r.requisition_number)),
    }))


if __name__ == "__main__":
    reset() if sys.argv[1] == "reset" else state(sys.argv[2])
