"""Shared pytest fixtures for the team test suites (unit + integration).

Each test gets a fresh, empty test database (pytest-django) and builds only the data it
needs through the small factories below, so every assertion has a known starting state.
"""
import pytest
from django.test import Client

from core.models import Department, User
from inventory.models import Item
from requisition.models import Requisition, RequisitionLineItem

PASSWORD = "Test@12345"


@pytest.fixture
def it_dept(db):
    return Department.objects.create(name="Information Technology", code="IT")


@pytest.fixture
def hr_dept(db):
    return Department.objects.create(name="Human Resources", code="HR")


@pytest.fixture
def make_user(db):
    def _make(username, role="initiator", department=None, superuser=False, first="", last=""):
        user = User(username=username, role=role, department=department, is_superuser=superuser,
                    first_name=first, last_name=last)
        user.set_password(PASSWORD)
        user.save()
        return user
    return _make


@pytest.fixture
def users(make_user, it_dept, hr_dept):
    """The standard cast: one user per role (+ cross-department HOD, HOD without dept)."""
    return {
        "superadmin": make_user("superadmin", "super_admin", superuser=True),
        "admin": make_user("admin", "admin", first="Adam", last="Admin"),
        "hod_it": make_user("hod_it", "hod", it_dept, first="Hamid", last="Head"),
        "hod_hr": make_user("hod_hr", "hod", hr_dept),
        "hod_nodept": make_user("hod_nodept", "hod"),
        "user_it": make_user("user_it", "initiator", it_dept, first="Imran", last="User"),
        "user_hr": make_user("user_hr", "initiator", hr_dept),
    }


@pytest.fixture
def make_item(db):
    counter = {"n": 0}

    def _make(stock=10, reorder=5, code=None, item_type="stationery", active=True, description="Blue pen"):
        counter["n"] += 1
        return Item.objects.create(material_code=code or f"T{counter['n']:03d}", description=description,
                                   item_type=item_type, quantity_total=stock, reorder_level=reorder,
                                   is_active=active)
    return _make


@pytest.fixture
def make_req(db):
    def _make(initiator, status="pending_hod", lines=(), purpose="Supplies for the IT helpdesk", **extra):
        req = Requisition(initiator=initiator, purpose=purpose, status=status, **extra)
        req.save()
        for item, qty in lines:
            RequisitionLineItem.objects.create(requisition=req, item=item, quantity_requested=qty,
                                               uom=item.unit_of_measurement)
        return req
    return _make


@pytest.fixture
def client_for(users):
    """client_for('hod_it') -> a Django test Client logged in as that user."""
    def _client(name):
        c = Client()
        c.force_login(users[name])
        return c
    return _client


def issue_payload(req, quantities, notes=""):
    """Build the inline-formset POST body that the Issue Items page submits."""
    lines = list(req.items.order_by("pk"))
    data = {"items-TOTAL_FORMS": len(lines), "items-INITIAL_FORMS": len(lines),
            "items-MIN_NUM_FORMS": 0, "items-MAX_NUM_FORMS": 1000}
    for i, (line, qty) in enumerate(zip(lines, quantities)):
        data.update({f"items-{i}-id": line.pk, f"items-{i}-requisition": req.pk,
                     f"items-{i}-quantity_issued": qty, f"items-{i}-notes": notes})
    return data
