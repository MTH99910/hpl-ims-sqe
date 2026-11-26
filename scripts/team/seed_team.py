#!/usr/bin/env python
"""Deterministic synthetic test data for the Requisition WF1/WF2 tests.

Run (after migrate):  DJANGO_SETTINGS_MODULE=tests.team.settings_test python scripts/team/seed_team.py

Every value here is fixed (no randomness) so that tests, k6 runs and demos always
start from the same known state. All people/data are synthetic.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.team.settings_test")

import django  # noqa: E402

django.setup()

from django.utils import timezone  # noqa: E402

from core.models import Department, User  # noqa: E402
from inventory.models import Item, Location  # noqa: E402
from requisition.models import Requisition, RequisitionLineItem  # noqa: E402

PASSWORD = "Test@12345"  # synthetic test-only password


def make_user(username, role, dept=None, superuser=False, first="", last=""):
    u = User(username=username, role=role, department=dept, first_name=first, last_name=last,
             is_superuser=superuser, is_staff=superuser, email=f"{username}@example.test")
    u.set_password(PASSWORD)
    u.save()
    return u


def make_req(initiator, status, lines, purpose="Office supplies for monthly operations", **extra):
    r = Requisition(initiator=initiator, purpose=purpose, status=status, **extra)
    r.save()
    for item, qty in lines:
        RequisitionLineItem.objects.create(requisition=r, item=item, quantity_requested=qty,
                                           uom=item.unit_of_measurement)
    return r


def seed():
    it = Department.objects.create(name="Information Technology", code="IT")
    hr = Department.objects.create(name="Human Resources", code="HR")

    # Superuser first: Item.save() attributes initial-stock transactions to it.
    make_user("superadmin", "super_admin", superuser=True, first="Sara", last="Super")
    admin = make_user("admin", "admin", first="Adam", last="Admin")
    make_user("admin2", "admin", first="Amna", last="Admin")
    hod_it = make_user("hod_it", "hod", it, first="Hamid", last="IT-Head")
    make_user("hod_hr", "hod", hr, first="Hina", last="HR-Head")
    make_user("hod_nodept", "hod", None, first="Haris", last="NoDept")
    u_it = make_user("user_it_1", "initiator", it, first="Imran", last="IT-User")
    u_hr = make_user("user_hr_1", "initiator", hr, first="Iqra", last="HR-User")

    loc = Location.objects.create(name="Rack 1", code="R1")
    st001 = Item.objects.create(material_code="ST001", description="Ball point pen (blue)",
                                item_type="stationery", unit_of_measurement="pcs",
                                location=loc, quantity_total=10, reorder_level=5)
    st002 = Item.objects.create(material_code="ST002", description="A4 paper ream 80gsm",
                                item_type="stationery", unit_of_measurement="ream",
                                location=loc, quantity_total=1, reorder_level=2)
    hk001 = Item.objects.create(material_code="HK001", description="Floor cleaner 1L",
                                item_type="housekeeping", unit_of_measurement="bottle",
                                location=loc, quantity_total=0, reorder_level=3)
    hk002 = Item.objects.create(material_code="HK002", description="Disposable gloves",
                                item_type="housekeeping", unit_of_measurement="box",
                                location=loc, quantity_total=50, reorder_level=10)
    Item.objects.create(material_code="ST099", description="Discontinued marker",
                        item_type="stationery", quantity_total=5, is_active=False)

    now = timezone.now()
    # One requisition per state (WF1 targets are pending, WF2 targets are authorized).
    make_req(u_it, "pending_hod", [(st001, 4)], purpose="Pens for new IT interns batch")
    make_req(u_it, "pending_hod", [(st001, 6), (hk002, 10)], purpose="Server room supplies restock")
    make_req(u_hr, "pending_hod", [(st001, 2)], purpose="Pens for HR onboarding desk")
    make_req(u_it, "authorized", [(st001, 4)], purpose="Pens for IT helpdesk counter",
             hod_approver=hod_it, hod_action_date=now)
    make_req(u_it, "authorized", [(st001, 3), (hk002, 5)], purpose="Lab cleaning and stationery",
             hod_approver=hod_it, hod_action_date=now)
    make_req(u_it, "authorized", [(st002, 1)], purpose="Printer paper for IT reports",
             hod_approver=hod_it, hod_action_date=now)
    make_req(u_it, "sent_back", [(st001, 1)], purpose="Single pen request for review",
             hod_approver=hod_it, hod_action_date=now, sent_back_reason="Add cost centre", sent_back_at=now)
    make_req(u_it, "rejected", [(hk002, 2)], purpose="Gloves for an unapproved event",
             hod_approver=hod_it, hod_action_date=now, rejection_reason="Not a department need")
    make_req(u_it, "issued", [(hk002, 1)], purpose="Gloves already issued earlier",
             hod_approver=hod_it, hod_action_date=now, issuer=admin, issued_date=now)
    make_req(u_it, "cancelled", [(st001, 1)], purpose="Cancelled pen request example")
    make_req(u_it, "draft", [(st001, 1)], purpose="Draft pen request (fixture only)")
    _ = hk001  # zero-stock item used by BVA tests
    print(f"Seeded: {User.objects.count()} users, {Item.objects.count()} items, "
          f"{Requisition.objects.count()} requisitions. Password for all users: {PASSWORD}")


if __name__ == "__main__":
    if User.objects.exists():
        sys.exit("Database is not empty - run scripts/team/reset_db.sh instead.")
    seed()
