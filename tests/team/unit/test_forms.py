"""Unit tests for requisition/forms.py - BR-1 (issue quantity limit) and BR-2b (reason required).

Boundary values are 3-point BVA (just below / at / just above every limit).
"""
import pytest

from requisition.forms import (HODActionForm, RequisitionFilterForm, RequisitionLineItemForm,
                               RequisitionLineItemUpdateForm)


def update_form(line, qty):
    return RequisitionLineItemUpdateForm({"quantity_issued": qty, "notes": ""}, instance=line)


@pytest.fixture
def line_factory(users, make_item, make_req):
    def _line(requested, stock):
        item = make_item(stock=stock)
        return make_req(users["user_it"], status="authorized", lines=[(item, requested)]).items.get()
    return _line


# --------------------------------------------------------------------------- BR-1
class TestBR1IssueQuantity:
    @pytest.mark.parametrize("qty,valid", [(-1, False), (0, True), (1, True)])
    def test_UT30_lower_bound_zero(self, line_factory, qty, valid):
        form = update_form(line_factory(requested=4, stock=10), qty)
        assert form.is_valid() is valid
        if not valid:
            assert form.errors["quantity_issued"] == ["Issued quantity cannot be negative."]

    @pytest.mark.parametrize("qty,valid", [(3, True), (4, True), (5, False)])
    def test_UT31_upper_bound_requested(self, line_factory, qty, valid):
        form = update_form(line_factory(requested=4, stock=10), qty)
        assert form.is_valid() is valid
        if not valid:
            assert form.errors["quantity_issued"] == ["Cannot issue more than requested (4)."]

    @pytest.mark.parametrize("qty,valid", [(3, True), (4, True), (5, False)])
    def test_UT32_upper_bound_stock(self, line_factory, qty, valid):
        form = update_form(line_factory(requested=6, stock=4), qty)
        assert form.is_valid() is valid
        if not valid:
            assert form.errors["quantity_issued"] == ["Insufficient stock. Available: 4, Requested: 6."]

    def test_UT33_zero_stock_item_only_zero_allowed(self, line_factory):
        line = line_factory(requested=2, stock=0)
        assert update_form(line, 0).is_valid()
        assert not update_form(line, 1).is_valid()

    def test_UT34_requested_checked_before_stock_when_both_exceeded(self, line_factory):
        """DT-3 row: qty > requested AND qty > stock -> the 'requested' message wins (check order)."""
        form = update_form(line_factory(requested=6, stock=4), 7)
        assert form.errors["quantity_issued"] == ["Cannot issue more than requested (6)."]

    def test_UT35_non_numeric_rejected_by_field(self, line_factory):
        assert not update_form(line_factory(requested=4, stock=10), "abc").is_valid()

    def test_UT36_initial_quantity_defaults_to_requested(self, line_factory):
        """FR-08: the issue form pre-fills quantity_issued with quantity_requested."""
        line = line_factory(requested=4, stock=10)
        assert RequisitionLineItemUpdateForm(instance=line).initial["quantity_issued"] == 4

    def test_UT37_initial_not_overridden_when_already_issued(self, line_factory):
        line = line_factory(requested=4, stock=10)
        line.quantity_issued = 2
        assert RequisitionLineItemUpdateForm(instance=line).initial["quantity_issued"] == 2

    def test_UT38_unsaved_instance_has_no_default(self):
        assert "quantity_issued" not in RequisitionLineItemUpdateForm().initial


# --------------------------------------------------------------------------- create-line validation
class TestCreateLineQuantity:
    @pytest.mark.parametrize("qty,valid", [(0, False), (1, True), (2, True)])
    def test_UT39_requested_lower_bound(self, make_item, qty, valid):
        item = make_item(stock=10)
        form = RequisitionLineItemForm({"item": item.pk, "quantity_requested": qty, "uom": "pcs"})
        assert form.is_valid() is valid

    @pytest.mark.parametrize("qty,valid", [(9, True), (10, True), (11, False)])
    def test_UT40_requested_upper_bound_stock(self, make_item, qty, valid):
        item = make_item(stock=10)
        form = RequisitionLineItemForm({"item": item.pk, "quantity_requested": qty, "uom": "pcs"})
        assert form.is_valid() is valid
        if not valid:
            assert "exceeds available stock (10)" in form.errors["quantity_requested"][0]

    def test_UT41_missing_item_skips_stock_check(self):
        form = RequisitionLineItemForm({"quantity_requested": 5, "uom": "pcs"})
        assert not form.is_valid()
        assert "item" in form.errors and "quantity_requested" not in form.errors

    def test_UT42_only_active_items_selectable(self, make_item):
        active, inactive = make_item(), make_item(active=False)
        qs = RequisitionLineItemForm().fields["item"].queryset
        assert active in qs and inactive not in qs


# --------------------------------------------------------------------------- BR-2b (reason required)
class TestHODActionFormDT2:
    """DT-2: action x rejection_reason x sent_back_reason."""

    @pytest.mark.parametrize("rule,action,rej,sent,valid,error_field,status", [
        ("R1", "authorized", "", "", True, None, "authorized"),
        ("R2", "authorized", "x", "y", True, None, "authorized"),
        ("R3", "rejected", "", "", False, "rejection_reason", "rejected"),
        ("R4", "rejected", "Not needed", "", True, None, "rejected"),
        ("R5", "sent_back", "", "", False, "sent_back_reason", "sent_back"),
        ("R6", "sent_back", "", "Add cost centre", True, None, "sent_back"),
        ("R7", "rejected", "", "comment", False, "rejection_reason", "rejected"),  # wrong field filled
        ("R8", "sent_back", "reason", "", False, "sent_back_reason", "sent_back"),
    ])
    def test_UT43_reason_required_decision_table(self, rule, action, rej, sent, valid, error_field, status):
        form = HODActionForm({"action": action, "status": "pending_hod", "notes": "",
                              "rejection_reason": rej, "sent_back_reason": sent})
        assert form.is_valid() is valid, rule
        assert form.cleaned_data["status"] == status
        if error_field:
            assert list(form.errors) == [error_field]

    @pytest.mark.parametrize("action", ["", "approve"])
    def test_UT44_invalid_action_rejected_and_status_untouched(self, action):
        form = HODActionForm({"action": action, "status": "pending_hod"})
        assert not form.is_valid()
        assert "action" in form.errors
        assert form.cleaned_data.get("status") == "pending_hod"

    def test_UT45_status_widget_hidden_and_reasons_optional(self):
        form = HODActionForm()
        assert form.fields["status"].widget.attrs["style"] == "display: none;"
        assert not form.fields["rejection_reason"].required
        assert not form.fields["sent_back_reason"].required


def test_UT46_filter_form_accepts_empty_and_valid_status():
    assert RequisitionFilterForm({}).is_valid()
    assert RequisitionFilterForm({"status": "issued", "date_from": "2026-11-01"}).is_valid()
    assert not RequisitionFilterForm({"status": "bogus"}).is_valid()
