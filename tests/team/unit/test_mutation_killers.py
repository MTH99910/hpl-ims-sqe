"""Tests added after analysing the surviving mutants of the baseline mutation run
(docs/13_mutation.md). Each test names the survivor(s) it kills.
"""
import pytest

from core.models import User
from requisition.forms import RequisitionLineItemUpdateForm
from requisition.models import Requisition

ALL = [s for s, _ in Requisition.STATUS_CHOICES]


@pytest.mark.parametrize("status", ALL)
def test_UT140_state_predicates_on_requisitions_loaded_from_db(users, make_req, status):
    """Kills S04 S05 S07 S08: `status is '...'` is False for strings read from the database."""
    req = Requisition.objects.get(pk=make_req(users["user_it"], status=status).pk)
    assert req.can_be_approved() is (status == "pending_hod")
    assert req.can_be_sent_back() is (status == "pending_hod")
    assert req.can_be_resubmitted() is (status == "sent_back")
    assert req.can_be_issued() is (status == "authorized")


@pytest.mark.parametrize("user_key,status,expected", [
    ("hod_it", "pending_hod", True), ("admin", "authorized", True),
    ("hod_hr", "pending_hod", False), ("admin", "issued", False),
])
def test_UT141_is_pending_action_with_fresh_db_objects(users, make_req, user_key, status, expected):
    """Kills S11 S12 S14: identity (`is`) comparisons fail for separately loaded objects."""
    req = Requisition.objects.get(pk=make_req(users["user_it"], status=status).pk)
    user = User.objects.get(pk=users[user_key].pk)
    assert req.is_pending_action(user) is expected


@pytest.mark.parametrize("status", ["rejected", "sent_back"])
def test_UT142_hod_has_no_pending_action_on_later_states(users, make_req, status):
    """Kills S10: `status >= 'pending_hod'` would also match rejected / sent_back."""
    req = make_req(users["user_it"], status=status)
    assert req.is_pending_action(users["hod_it"]) is False


def test_UT143_hod_without_department_cannot_act_for_initiator_without_department(users, make_user, make_req, client_for):
    """Kills S13 and S17: without the `user.department` guard, None == None would give a
    department-less HOD authority over every department-less initiator (BR-2 condition C2)."""
    loner = make_user("loner", "initiator")                       # no department
    req = make_req(loner, status="pending_hod")
    assert req.is_pending_action(users["hod_nodept"]) is False
    assert client_for("hod_nodept").get(f"/requisition/{req.pk}/hod-approval/").status_code == 404


def test_UT144_negative_issued_quantity_is_not_treated_as_unissued(users, make_item, make_req):
    """Kills S02 and S16: the '== 0' boundary must not widen to '<= 0'."""
    line = make_req(users["user_it"], status="authorized", lines=[(make_item(), 4)]).items.get()
    line.quantity_issued = -1
    assert RequisitionLineItemUpdateForm(instance=line).initial.get("quantity_issued") != 4
    assert line.get_status_display() == "Partial (-1/4)"
