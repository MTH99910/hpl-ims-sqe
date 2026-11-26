"""Unit tests for the models used by WF1/WF2 (requisition, inventory, core).

Test IDs (UT-xx) are referenced from docs/07_rtm.csv.
"""
from unittest import mock

import pytest
from django.utils import timezone

from core.models import Notification
from inventory.models import Item, Transaction
from requisition.models import Requisition, RequisitionLineItem

ALL_STATUSES = [s for s, _ in Requisition.STATUS_CHOICES]


# --------------------------------------------------------------------------- Requisition
class TestRequisitionSave:
    def test_UT01_number_and_department_generated_on_create(self, users, make_req):
        req = make_req(users["user_it"])
        today = timezone.now().strftime("%Y%m%d")
        assert req.requisition_number == f"REQ-{today}-0001"
        assert req.department == "Information Technology"

    def test_UT02_number_increments_per_day(self, users, make_req):
        make_req(users["user_it"])
        second = make_req(users["user_it"])
        assert second.requisition_number.endswith("-0002")

    def test_UT03_initiator_without_department_gets_unknown(self, users, make_req):
        req = make_req(users["admin"])
        assert req.department == "Unknown"

    def test_UT04_number_not_regenerated_on_update(self, users, make_req):
        req = make_req(users["user_it"])
        number = req.requisition_number
        req.purpose = "Changed purpose text"
        req.save()
        req.refresh_from_db()
        assert req.requisition_number == number

    def test_UT05_str_and_absolute_url(self, users, make_req):
        req = make_req(users["user_it"])
        assert str(req) == f"{req.requisition_number} - Imran User (Pending HOD Approval)"
        assert req.get_absolute_url() == f"/requisition/{req.pk}/"


class TestRequisitionDisplayHelpers:
    @pytest.mark.parametrize("status,badge,icon", [
        ("draft", "bg-secondary", "bi-pencil"),
        ("pending_hod", "bg-warning text-dark", "bi-clock"),
        ("sent_back", "bg-info text-dark", "bi-arrow-repeat"),
        ("authorized", "bg-primary", "bi-check-circle"),
        ("rejected", "bg-danger", "bi-x-circle"),
        ("issued", "bg-success", "bi-box-seam"),
        ("cancelled", "bg-dark", "bi-slash-circle"),
        ("unknown_status", "bg-secondary", "bi-question"),   # dictionary default branch
    ])
    def test_UT06_status_badge_and_icon(self, status, badge, icon):
        req = Requisition(status=status)
        assert req.get_status_badge() == badge
        assert req.get_status_icon() == icon

    def test_UT07_totals_requested_and_issued(self, users, make_item, make_req):
        a, b = make_item(), make_item()
        req = make_req(users["user_it"], lines=[(a, 4), (b, 6)])
        RequisitionLineItem.objects.filter(item=a).update(quantity_issued=3)
        assert req.get_total_requested() == 10
        assert req.get_total_issued() == 3


class TestBR3StatePredicates:
    """BR-3: which actions each lifecycle state allows (model-level guards)."""

    @pytest.mark.parametrize("status", ALL_STATUSES)
    def test_UT08_predicates_for_every_state(self, status):
        req = Requisition(status=status)
        assert req.can_be_edited() is (status in ["draft", "pending_hod", "sent_back"])
        assert req.can_be_approved() is (status == "pending_hod")
        assert req.can_be_sent_back() is (status == "pending_hod")
        assert req.can_be_resubmitted() is (status == "sent_back")
        assert req.can_be_issued() is (status == "authorized")


class TestBR2IsPendingActionMCC:
    """BR-2 decision in Requisition.is_pending_action - full MCC table rows (docs/11_unit_testing.md).

    D1a: user.is_hod and status == 'pending_hod'
    D1b: user.department and initiator.department == user.department
    D1c: user.is_admin and status == 'authorized'
    """

    @pytest.mark.parametrize("row,user_key,status,expected", [
        ("M1", "hod_it", "pending_hod", True),     # hod T, pending T, dept T, same T
        ("M2", "hod_hr", "pending_hod", False),    # hod T, pending T, dept T, same F
        ("M3", "hod_nodept", "pending_hod", False),  # hod T, pending T, dept F (same masked)
        ("M4", "hod_it", "authorized", False),     # hod T, pending F -> falls to D1c: admin F
        ("M5", "admin", "authorized", True),       # hod F -> D1c admin T, authorized T
        ("M6", "admin", "pending_hod", False),     # hod F -> D1c admin T, authorized F
        ("M7", "user_it", "authorized", False),    # hod F -> D1c admin F (authorized masked)
        ("M8", "user_it", "pending_hod", False),   # hod F, admin F
    ])
    def test_UT09_is_pending_action(self, users, make_req, row, user_key, status, expected):
        req = make_req(users["user_it"], status=status)
        assert req.is_pending_action(users[user_key]) is expected, row


# --------------------------------------------------------------------------- Line item
class TestLineItem:
    @pytest.mark.parametrize("issued,display,full", [
        (0, "Pending", False),
        (3, "Partial (3/4)", False),
        (4, "Fulfilled", True),
        (5, "Fulfilled", True),
    ])
    def test_UT10_status_display_boundaries(self, users, make_item, make_req, issued, display, full):
        req = make_req(users["user_it"], lines=[(make_item(), 4)])
        line = req.items.get()
        line.quantity_issued = issued
        assert line.get_status_display() == display
        assert line.is_fully_issued() is full

    @pytest.mark.parametrize("length,expected_suffix", [(40, ""), (41, "...")])
    def test_UT11_short_description_boundary(self, users, make_item, make_req, length, expected_suffix):
        item = make_item(description="x" * length)
        line = make_req(users["user_it"], lines=[(item, 1)]).items.get()
        assert line.get_short_description() == "x" * 40 + expected_suffix

    def test_UT12_line_str(self, users, make_item, make_req):
        line = make_req(users["user_it"], lines=[(make_item(code="ST001"), 2)]).items.get()
        assert str(line) == "ST001 - 2 pcs"


# --------------------------------------------------------------------------- Item / Transaction
class TestItem:
    @pytest.mark.parametrize("stock,low,status,badge,label", [
        (0, True, "out_of_stock", "bg-danger", "Out of Stock"),
        (4, True, "low_stock", "bg-warning", "Low Stock"),    # reorder-1
        (5, True, "low_stock", "bg-warning", "Low Stock"),    # reorder (boundary: <=)
        (6, False, "in_stock", "bg-success", "In Stock"),     # reorder+1
    ])
    def test_UT13_stock_status_bva_around_reorder_level(self, make_item, stock, low, status, badge, label):
        item = make_item(stock=stock, reorder=5)
        assert item.is_low_stock is low
        assert item.stock_status == status
        assert item.get_stock_badge() == badge
        assert item.get_stock_status_display() == label

    @pytest.mark.parametrize("item_type,badge,icon", [
        ("stationery", "bg-primary", "bi-pencil-square"),
        ("housekeeping", "bg-info", "bi-basket"),
    ])
    def test_UT14_type_badge_and_icon(self, make_item, item_type, badge, icon):
        item = make_item(item_type=item_type)
        assert item.get_type_badge() == badge
        assert item.get_type_icon() == icon

    def test_UT15_str_and_url(self, make_item):
        item = make_item(code="ST001", description="Pen " * 20)
        assert str(item) == "ST001 - " + ("Pen " * 20)[:50]
        assert item.get_absolute_url() == f"/inventory/{item.pk}/"

    def test_UT16_new_item_with_stock_records_initial_inward_transaction(self, users, make_item):
        item = make_item(stock=10)
        txn = Transaction.objects.get(item=item)
        assert (txn.transaction_type, txn.quantity_change, txn.balance_after) == ("inward", 10, 10)
        assert txn.user == users["superadmin"]

    def test_UT17_new_item_with_zero_stock_records_no_transaction(self, make_item):
        item = make_item(stock=0)
        assert not Transaction.objects.filter(item=item).exists()

    def test_UT18_updating_item_records_no_new_transaction(self, make_item):
        item = make_item(stock=10)
        item.quantity_total = 20
        item.save()
        assert Transaction.objects.filter(item=item).count() == 1

    def test_UT19_initial_transaction_without_superuser_has_no_user(self, db, make_item):
        item = make_item(stock=3)
        assert Transaction.objects.get(item=item).user is None

    def test_UT20_superuser_lookup_failure_is_tolerated(self, db, make_item):
        with mock.patch("django.contrib.auth.models.UserManager.filter", side_effect=RuntimeError("db")):
            item = make_item(stock=2)
        assert Transaction.objects.get(item=item).user is None


class TestTransaction:
    @pytest.mark.parametrize("change,shown", [(5, "+5"), (-3, "-3"), (0, "0")])
    def test_UT21_quantity_display_and_str_sign(self, make_item, change, shown):
        item = make_item(stock=0, code="ST001")
        txn = Transaction.objects.create(item=item, transaction_type="adjustment",
                                         quantity_change=change, balance_after=0)
        assert txn.get_quantity_display() == shown
        sign = "+" if change > 0 else ""
        assert str(txn).startswith(f"ST001: {sign}{change} (adjustment) on ")

    @pytest.mark.parametrize("ttype,icon", [
        ("inward", "bi-box-arrow-in-down"), ("outward", "bi-box-arrow-up"),
        ("adjustment", "bi-gear"), ("return", "bi-arrow-repeat"),
        ("write_off", "bi-trash"), ("other", "bi-question"),
    ])
    def test_UT22_transaction_icon(self, ttype, icon):
        assert Transaction(transaction_type=ttype).get_transaction_icon() == icon


# --------------------------------------------------------------------------- core.User / Notification
class TestUserAndNotification:
    def test_UT23_department_and_user_str(self, users, it_dept):
        assert str(it_dept) == "Information Technology (IT)"
        assert str(users["hod_it"]) == "Hamid Head (Head of Department - Information Technology)"
        assert str(users["admin"]) == "Adam Admin (Admin/Issuer - No Department)"

    @pytest.mark.parametrize("first,last,expected", [("Ali", "Khan", "Ali Khan"), ("Ali", "", "u1"), ("", "Khan", "u1")])
    def test_UT24_full_name_requires_both_parts(self, make_user, first, last, expected):
        assert make_user("u1", first=first, last=last).get_full_name() == expected

    @pytest.mark.parametrize("key,flags", [
        ("superadmin", (True, False, False, False)), ("hod_it", (False, True, False, False)),
        ("admin", (False, False, True, False)), ("user_it", (False, False, False, True)),
    ])
    def test_UT25_role_properties(self, users, key, flags):
        u = users[key]
        assert (u.is_super_admin, u.is_hod, u.is_admin, u.is_initiator) == flags

    def test_UT26_pending_requisitions_count_per_role(self, users, make_req):
        make_req(users["user_it"], status="pending_hod")
        make_req(users["user_hr"], status="pending_hod")
        make_req(users["user_it"], status="authorized")
        make_req(users["user_it"], status="issued")
        assert users["superadmin"].get_pending_requisitions_count() == 3
        assert users["hod_it"].get_pending_requisitions_count() == 1   # own department only
        assert users["admin"].get_pending_requisitions_count() == 1    # authorized only
        assert users["user_it"].get_pending_requisitions_count() == 0  # initiator: no queue

    @pytest.mark.parametrize("ntype,icon", [
        ("requisition_created", "bi-plus-circle text-primary"),
        ("requisition_approved", "bi-check-circle text-success"),
        ("requisition_rejected", "bi-x-circle text-danger"),
        ("requisition_sent_back", "bi-arrow-repeat text-warning"),
        ("requisition_issued", "bi-box-seam text-success"),
        ("other", "bi-bell"),
    ])
    def test_UT27_notification_icon(self, ntype, icon):
        assert Notification(notification_type=ntype).get_icon() == icon

    def test_UT28_notification_str_and_unread_count(self, users):
        n = Notification.objects.create(user=users["admin"], notification_type="requisition_issued",
                                        title="T1", message="m")
        Notification.objects.create(user=users["admin"], notification_type="requisition_issued",
                                    title="T2", message="m", is_read=True)
        assert str(n) == "T1 - admin"
        assert users["admin"].get_unread_notifications_count() == 1


def test_UT29_item_model_default_ordering_and_reverse_accessors(make_item):
    """Smoke: Item manager returns created rows (guards accidental model changes)."""
    make_item(code="B1"), make_item(code="A1")
    assert list(Item.objects.values_list("material_code", flat=True)) == ["A1", "B1"]
