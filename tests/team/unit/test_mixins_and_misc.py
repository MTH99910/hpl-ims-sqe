"""Role mixins (BR-2 / access rules) and remaining reachable helpers.

The three mixins encode the documented role rules but NO view in requisition/views.py
uses them - this is the root cause of defect F3 (IssueItemsView unprotected). Testing them
directly proves the rule exists and works; the access tests prove it is not applied.
"""
import pytest
from django.test import RequestFactory

from inventory.models import Location
from requisition.views import (AdminRequiredMixin, HODRequiredMixin, InitiatorRequiredMixin,
                               RequisitionCreateView)


def mixin_allows(mixin_cls, user):
    m = mixin_cls()
    m.request = RequestFactory().get("/")
    m.request.user = user
    return m.test_func()


@pytest.mark.parametrize("who,initiator,hod,admin", [
    ("user_it", True, False, False),
    ("hod_it", True, True, False),
    ("admin", True, True, True),
    ("superadmin", False, False, False),
])
def test_UT130_role_mixins(users, who, initiator, hod, admin):
    u = users[who]
    assert mixin_allows(InitiatorRequiredMixin, u) is initiator
    assert mixin_allows(HODRequiredMixin, u) is hod
    assert mixin_allows(AdminRequiredMixin, u) is admin


def test_UT132_create_view_keeps_supplied_formset(users):
    view = RequisitionCreateView()
    view.request = RequestFactory().get("/")
    view.request.user = users["user_it"]
    view.object = None
    sentinel = object()
    ctx = view.get_context_data(line_items_formset=sentinel)
    assert ctx["line_items_formset"] is sentinel


def test_UT133_location_str(db):
    assert str(Location(name="Rack 1", code="R1")) == "Location R1 - Rack 1"
