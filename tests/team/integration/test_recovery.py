"""Doc section 5 - controlled failure-and-recovery test for a state-changing operation.   owner: Member A

Operation: WF2 issue (writes Item.quantity_total, inventory.Transaction, RequisitionLineItem,
Requisition.status and Notification inside one transaction.atomic block).

Test double: the database "becomes unavailable" (django.db.OperationalError) while the SECOND
line's stock is being written - i.e. after part of the write has already happened.
Then: verify the persisted state, restore the dependency, retry the same request, verify the
final state, and verify that repeating the request creates no duplicates.

transaction=True -> real COMMIT/ROLLBACK semantics (no wrapping test transaction).
"""
from unittest import mock

import pytest
from django.db import OperationalError
from django.test import Client

from core.models import Notification
from inventory.models import Item, Transaction
from tests.team.conftest import issue_payload

pytestmark = pytest.mark.django_db(transaction=True)


def snapshot(req, *items):
    req.refresh_from_db()
    for it in items:
        it.refresh_from_db()
    return {
        "status": req.status,
        "issuer": req.issuer_id,
        "issued": list(req.items.order_by("pk").values_list("quantity_issued", flat=True)),
        "stock": [it.quantity_total for it in items],
        "outward": Transaction.objects.filter(transaction_type="outward", reference=req.requisition_number).count(),
        "issued_notifications": Notification.objects.filter(notification_type="requisition_issued").count(),
    }


def test_REC01_issue_survives_database_failure_and_recovers_without_duplicates(users, make_item, make_req):
    pen, gloves = make_item(stock=10, code="ST001"), make_item(stock=50, code="HK002")
    req = make_req(users["user_it"], status="authorized", lines=[(pen, 4), (gloves, 5)])
    admin = Client(raise_request_exception=False)
    admin.force_login(users["admin"])
    url = f"/requisition/{req.pk}/issue/"
    payload = issue_payload(req, [3, 2])        # typed quantities (avoids defect F13)
    initial = snapshot(req, pen, gloves)

    # ---- 1. dependency fails before the write completes (2nd Item.save raises)
    real_save = Item.save
    calls = {"n": 0}

    def failing_save(self, *a, **kw):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OperationalError("database is unavailable (simulated)")
        return real_save(self, *a, **kw)

    with mock.patch.object(Item, "save", failing_save):
        resp = admin.post(url, payload)
    assert resp.status_code == 500
    assert calls["n"] == 2                                  # the first line WAS written before the failure

    # ---- 2. persisted state after the failure: everything rolled back
    after_failure = snapshot(req, pen, gloves)
    assert after_failure == initial
    assert after_failure == {"status": "authorized", "issuer": None, "issued": [0, 0], "stock": [10, 50],
                             "outward": 0, "issued_notifications": 0}

    # ---- 3. dependency restored (patch removed) -> retry the identical request
    resp = admin.post(url, payload)
    assert resp.status_code == 302

    final = snapshot(req, pen, gloves)
    assert final == {"status": "issued", "issuer": users["admin"].pk, "issued": [3, 2], "stock": [7, 48],
                     "outward": 2, "issued_notifications": 1}

    # ---- 4. repeating the request after success creates nothing new
    assert admin.post(url, payload).status_code == 404
    assert snapshot(req, pen, gloves) == final


def test_REC02_failure_on_first_write_also_leaves_no_trace(users, make_item, make_req):
    pen = make_item(stock=10)
    req = make_req(users["user_it"], status="authorized", lines=[(pen, 4)])
    admin = Client(raise_request_exception=False)
    admin.force_login(users["admin"])
    with mock.patch.object(Transaction.objects, "create", side_effect=OperationalError("db down")):
        assert admin.post(f"/requisition/{req.pk}/issue/", issue_payload(req, [3])).status_code == 500
    assert snapshot(req, pen)["status"] == "authorized" and snapshot(req, pen)["stock"] == [10]
    assert admin.post(f"/requisition/{req.pk}/issue/", issue_payload(req, [3])).status_code == 302
    assert snapshot(req, pen)["stock"] == [7] and snapshot(req, pen)["outward"] == 1


@pytest.mark.defect
@pytest.mark.xfail(strict=True, reason="F6: create API is not atomic - a failure after the header insert leaves an orphan requisition")
def test_REC03_create_api_failure_leaves_no_orphan(users, make_item):
    import json
    from requisition.models import Requisition, RequisitionLineItem
    item = make_item(stock=10)
    c = Client(raise_request_exception=False)
    c.force_login(users["user_it"])
    with mock.patch.object(RequisitionLineItem.objects, "create", side_effect=OperationalError("db down")):
        c.post("/requisition/api/create/", json.dumps({"purpose": "Pens for interns batch",
                                                       "items": [{"id": item.pk, "qty": 1}]}),
               content_type="application/json")
    assert not Requisition.objects.exists()
