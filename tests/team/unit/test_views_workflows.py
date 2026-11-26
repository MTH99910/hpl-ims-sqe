"""White-box tests for the two workflow views.

WF1 = HODApprovalView (pending_hod -> authorized / sent_back / rejected)
WF2 = IssueItemsView  (authorized -> issued, stock deducted, outward Transaction)

Tests marked xfail(strict=True) assert the CORRECT (documented) behaviour for a confirmed,
logged defect. strict=True means the test turns red as soon as the defect is fixed, which
forces the marker to be removed in the fix PR - it is a tracked expectation, not a bypass.
"""
from unittest import mock

import pytest
from django.contrib.messages import get_messages

from core.models import Notification
from inventory.models import Transaction
from requisition.models import Requisition
from tests.team.conftest import issue_payload


def msgs(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


@pytest.fixture
def pending(users, make_item, make_req):
    item = make_item(stock=10, code="ST001")
    return make_req(users["user_it"], status="pending_hod", lines=[(item, 4)])


@pytest.fixture
def authorized(users, make_item, make_req):
    item = make_item(stock=10, code="ST001")
    return make_req(users["user_it"], status="authorized", lines=[(item, 4)],
                    hod_approver=users["hod_it"])


# =========================================================================== WF1
class TestWF1HODApproval:
    url = "/requisition/{}/hod-approval/"

    def test_UT50_hod_same_department_sees_approval_screen(self, client_for, pending):
        r = client_for("hod_it").get(self.url.format(pending.pk))
        assert r.status_code == 200
        assert r.context["title"] == "HOD Approval"
        assert list(r.context["line_items"]) == list(pending.items.all())

    @pytest.mark.parametrize("who", ["hod_hr", "hod_nodept", "user_it", "superadmin"])
    def test_UT51_out_of_scope_users_get_404(self, client_for, pending, who):
        assert client_for(who).get(self.url.format(pending.pk)).status_code == 404

    @pytest.mark.parametrize("status", ["authorized", "sent_back", "rejected", "issued", "cancelled", "draft"])
    def test_UT52_hod_cannot_act_on_non_pending(self, client_for, users, make_req, status):
        req = make_req(users["user_it"], status=status)
        assert client_for("hod_it").get(self.url.format(req.pk)).status_code == 404

    def test_UT53_authorize_sets_status_approver_date_and_notifies(self, client_for, users, pending, make_user):
        make_user("admin_b", "admin")
        r = client_for("hod_it").post(self.url.format(pending.pk), {"action": "authorized", "status": "pending_hod"})
        assert r.status_code == 302 and r.url == "/requisition/hod/"
        pending.refresh_from_db()
        assert pending.status == "authorized"
        assert pending.hod_approver == users["hod_it"] and pending.hod_action_date is not None
        assert pending.sent_back_at is None
        approved = Notification.objects.filter(notification_type="requisition_approved")
        assert sorted(n.user.username for n in approved) == ["admin", "admin_b", "user_it"]
        assert approved.first().message.startswith("Your requisition has been approved by Hamid Head")
        assert f"Requisition {pending.requisition_number} has been approved." in msgs(r)

    def test_UT54_send_back_sets_reason_and_timestamp(self, client_for, pending):
        r = client_for("hod_it").post(self.url.format(pending.pk), {
            "action": "sent_back", "status": "pending_hod", "sent_back_reason": "Add cost centre"})
        pending.refresh_from_db()
        assert (pending.status, pending.sent_back_reason) == ("sent_back", "Add cost centre")
        assert pending.sent_back_at is not None
        n = Notification.objects.get()
        assert (n.user.username, n.notification_type) == ("user_it", "requisition_sent_back")
        assert "sent back for revision" in msgs(r)[0]

    def test_UT55_reject_stores_reason_and_notifies_initiator(self, client_for, pending):
        r = client_for("hod_it").post(self.url.format(pending.pk), {
            "action": "rejected", "status": "pending_hod", "rejection_reason": "Not needed"})
        pending.refresh_from_db()
        assert (pending.status, pending.rejection_reason) == ("rejected", "Not needed")
        n = Notification.objects.get()
        assert n.notification_type == "requisition_rejected" and "Reason: Not needed" in n.message
        assert "has been rejected" in msgs(r)[0]

    @pytest.mark.parametrize("payload,field", [
        ({"action": "rejected"}, "rejection_reason"),
        ({"action": "sent_back"}, "sent_back_reason"),
    ])
    def test_UT56_missing_reason_rerenders_and_persists_nothing(self, client_for, pending, payload, field):
        r = client_for("hod_it").post(self.url.format(pending.pk), {**payload, "status": "pending_hod"})
        assert r.status_code == 200 and field in r.context["form"].errors
        pending.refresh_from_db()
        assert pending.status == "pending_hod" and pending.hod_approver is None
        assert not Notification.objects.exists()

    def test_UT57_repeat_approval_is_rejected_no_duplicate_notifications(self, client_for, pending):
        c = client_for("hod_it")
        c.post(self.url.format(pending.pk), {"action": "authorized", "status": "pending_hod"})
        before = Notification.objects.count()
        assert c.post(self.url.format(pending.pk), {"action": "authorized", "status": "pending_hod"}).status_code == 404
        assert Notification.objects.count() == before

    @pytest.mark.defect
    @pytest.mark.xfail(strict=True, reason="F4: Admin can use the HOD approval view (separation of duties)")
    def test_UT58_admin_cannot_approve(self, client_for, pending):
        assert client_for("admin").get(self.url.format(pending.pk)).status_code in (403, 404)

    @pytest.mark.defect
    @pytest.mark.xfail(strict=True, reason="F4: Admin can move an ISSUED requisition back to authorized")
    def test_UT59_issued_requisition_cannot_be_reauthorized(self, client_for, users, make_req):
        req = make_req(users["user_it"], status="issued")
        client_for("admin").post(self.url.format(req.pk), {"action": "authorized", "status": "issued"})
        req.refresh_from_db()
        assert req.status == "issued"


# =========================================================================== WF2
class TestWF2Issue:
    url = "/requisition/{}/issue/"

    def test_UT60_admin_sees_issue_screen_with_defaults(self, client_for, authorized):
        r = client_for("admin").get(self.url.format(authorized.pk))
        assert r.status_code == 200 and r.context["title"] == "Issue Items"
        assert r.context["formset"].forms[0].initial["quantity_issued"] == 4

    @pytest.mark.parametrize("status", ["pending_hod", "sent_back", "rejected", "issued", "cancelled", "draft"])
    def test_UT61_non_authorized_cannot_be_issued(self, client_for, users, make_req, make_item, status):
        req = make_req(users["user_it"], status=status, lines=[(make_item(), 1)])
        assert client_for("admin").post(self.url.format(req.pk), issue_payload(req, [1])).status_code == 404

    def test_UT62_changed_quantity_deducts_stock_and_records_transaction(self, client_for, users, authorized):
        r = client_for("admin").post(self.url.format(authorized.pk), issue_payload(authorized, [3]))
        assert r.status_code == 302 and r.url == "/requisition/admin/"
        authorized.refresh_from_db()
        line = authorized.items.get()
        assert (authorized.status, authorized.issuer, line.quantity_issued) == ("issued", users["admin"], 3)
        assert authorized.issued_date is not None
        line.item.refresh_from_db()
        assert line.item.quantity_total == 7
        txn = Transaction.objects.get(transaction_type="outward")
        assert (txn.quantity_change, txn.balance_after, txn.reference) == (-3, 7, authorized.requisition_number)
        assert txn.user == users["admin"]
        assert Notification.objects.get().notification_type == "requisition_issued"
        assert f"Items issued for requisition {authorized.requisition_number}" in msgs(r)

    @pytest.mark.defect
    @pytest.mark.xfail(strict=True, reason="F13: issuing the pre-filled default quantity deducts no stock")
    def test_UT63_default_quantity_issue_deducts_stock(self, client_for, authorized):
        client_for("admin").post(self.url.format(authorized.pk), issue_payload(authorized, [4]))
        line = authorized.items.get()
        line.item.refresh_from_db()
        assert line.quantity_issued == 4
        assert line.item.quantity_total == 6
        assert Transaction.objects.filter(transaction_type="outward").count() == 1

    def test_UT64_zero_quantity_line_records_no_transaction(self, client_for, users, make_item, make_req):
        a, b = make_item(stock=10), make_item(stock=10)
        req = make_req(users["user_it"], status="authorized", lines=[(a, 2), (b, 5)])
        client_for("admin").post(self.url.format(req.pk), issue_payload(req, [0, 3]))
        a.refresh_from_db(), b.refresh_from_db()
        assert (a.quantity_total, b.quantity_total) == (10, 7)
        assert Transaction.objects.filter(transaction_type="outward").count() == 1

    @pytest.mark.parametrize("qty,expected", [
        (5, "quantity_issued: Cannot issue more than requested (4)."),
        (-1, "quantity_issued: Issued quantity cannot be negative."),
    ])
    def test_UT65_invalid_quantity_rerenders_and_persists_nothing(self, client_for, authorized, qty, expected):
        r = client_for("admin").post(self.url.format(authorized.pk), issue_payload(authorized, [qty]))
        assert r.status_code == 200
        assert msgs(r) == [f"Please correct the errors: {expected}"]
        authorized.refresh_from_db()
        assert authorized.status == "authorized"
        assert not Transaction.objects.filter(transaction_type="outward").exists()

    def test_UT66_broken_management_form_gives_generic_error(self, client_for, authorized):
        r = client_for("admin").post(self.url.format(authorized.pk), {"items-0-quantity_issued": 1})
        assert r.status_code == 200
        assert msgs(r) == ["Please correct the errors below."]

    def test_UT67_repeat_issue_returns_404_and_no_duplicate(self, client_for, authorized):
        c = client_for("admin")
        c.post(self.url.format(authorized.pk), issue_payload(authorized, [3]))
        assert c.post(self.url.format(authorized.pk), issue_payload(authorized, [3])).status_code == 404
        assert Transaction.objects.filter(transaction_type="outward").count() == 1

    def test_UT68_failure_mid_issue_rolls_back_everything(self, client_for, users, make_item, make_req):
        """BR-4 all-or-nothing: a failure on line 2 must undo line 1 (transaction.atomic)."""
        a, b = make_item(stock=10), make_item(stock=10)
        req = make_req(users["user_it"], status="authorized", lines=[(a, 2), (b, 3)])
        real_create = Transaction.objects.create
        calls = {"n": 0}

        def flaky(**kw):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("database unavailable")
            return real_create(**kw)

        c = client_for("admin")
        c.raise_request_exception = False
        with mock.patch.object(Transaction.objects, "create", side_effect=flaky):
            assert c.post(self.url.format(req.pk), issue_payload(req, [1, 1])).status_code == 500
        req.refresh_from_db(), a.refresh_from_db(), b.refresh_from_db()
        assert req.status == "authorized" and (a.quantity_total, b.quantity_total) == (10, 10)
        assert list(req.items.values_list("quantity_issued", flat=True)) == [0, 0]
        assert not Transaction.objects.filter(transaction_type="outward").exists()

    @pytest.mark.defect
    @pytest.mark.xfail(strict=True, reason="F3: IssueItemsView has no Admin role check")
    @pytest.mark.parametrize("who", ["hod_it", "user_it"])
    def test_UT69_non_admin_cannot_issue(self, client_for, authorized, who):
        client_for(who).post(self.url.format(authorized.pk), issue_payload(authorized, [3]))
        authorized.refresh_from_db()
        assert authorized.status == "authorized"

    @pytest.mark.defect
    @pytest.mark.xfail(strict=True, reason="F7: two lines of the same item can jointly exceed stock")
    def test_UT70_same_item_on_two_lines_cannot_exceed_stock(self, client_for, users, make_item, make_req):
        item = make_item(stock=5)
        req = make_req(users["user_it"], status="authorized", lines=[(item, 4), (item, 4)])
        client_for("admin").post(self.url.format(req.pk), issue_payload(req, [3, 3]))
        item.refresh_from_db()
        assert item.quantity_total >= 0


def test_UT71_requisition_status_values_are_the_documented_lifecycle():
    assert [s for s, _ in Requisition.STATUS_CHOICES] == [
        "draft", "pending_hod", "sent_back", "authorized", "rejected", "issued", "cancelled"]
