"""Generator-driven API tests: EP classes and 3-point BVA for every input of every operation.

One test per generated case. Each test sends a base payload whose other fields are valid
(generator representatives) with exactly ONE field replaced by the case value, then
asserts the response AND reads back the shared records (requisition, stock, transactions)
after success and after rejection.

Deviations of the baseline from the expected behaviour are listed in KNOWN_DEVIATIONS and
run as xfail(strict=True) linked to the defect id - they fail loudly once fixed.
"""
import copy

import pytest

from inventory.models import Transaction
from requisition.models import Requisition
from tests.team.api.conftest import apply_value, case_id, cases_for, valid_value

# case-id prefix -> defect id (observed behaviour differs from the spec's expected behaviour)
# Each entry was confirmed by inspecting the server response / traceback (docs/12_api_findings.md).
KNOWN_DEVIATIONS = {
    **{f"{op}:{f}": d for op in ("createRequisition", "updateRequisition") for f, d in {
        "purpose:EP:03": "F16: non-string purpose -> 500 AttributeError (.strip on int)",
        "notes:EP:02": "F16: non-string notes -> 500 AttributeError (.strip on int)",
        "items:EP:01": "F16: non-array items -> 500 (iterates characters of the string)",
        "items[0].id:EP:01": "F17: inactive item accepted into a requisition",
        "items[0].id:EP:02": "F6: unknown item id -> 500 (and orphan requisition on create)",
        "items[0].id:EP:03": "F16: non-integer item id -> 500 ValueError",
        "items[0].qty:EP:01": "F16: non-integer qty -> 500 TypeError",
        "items[0].qty:EP:02": "F16: decimal qty silently truncated and accepted",
        "items[0].uom:EP:10": "F16: unit of measure outside the allowed list accepted",
        "items[0].notes:EP:02": "F16: non-string line notes accepted",
    }.items()},
    **{f"issueItems:items-INITIAL_FORMS:EP:{n:02d}": "F18: tampered formset management data -> 500"
       for n in (1, 2, 3)},
    **{f"issueItems:items-0-id:EP:{n:02d}": "F18: other/unknown/missing line id -> 500 RelatedObjectDoesNotExist"
       for n in (1, 2, 3, 4)},
    **{f"itemDetails:type:EP:{n:02d}": "F5: type filter after slice -> 500 TypeError" for n in (0, 1, 2)},
}


def maybe_xfail(case):
    for prefix, defect in KNOWN_DEVIATIONS.items():
        if case["id"] == prefix:
            return pytest.param(case, id=case_id(case), marks=pytest.mark.xfail(strict=True, reason=defect))
    return pytest.param(case, id=case_id(case))


def params(operation):
    return [maybe_xfail(c) for c in cases_for(operation)]


# --------------------------------------------------------------------------- createRequisition (FR-14)
@pytest.fixture
def create_ctx(users, make_item):
    return {"active_item": make_item(stock=10).pk, "inactive_item": make_item(active=False).pk,
            "unknown_item": 999_999}


def json_base(op, ctx):
    return {"purpose": valid_value(op, "purpose"), "notes": valid_value(op, "notes"),
            "items": [{"id": ctx["active_item"], "qty": valid_value(op, "items[0].qty"),
                       "uom": valid_value(op, "items[0].uom"), "notes": valid_value(op, "items[0].notes")}]}


def make_resolver(ctx, base_line):
    def resolve(v):
        if isinstance(v, dict) and "ref" in v:
            return ctx[v["ref"]]
        if isinstance(v, dict) and "array_len" in v:
            return [copy.deepcopy(base_line) for _ in range(v["array_len"])]
        return v
    return resolve


@pytest.mark.parametrize("case", params("createRequisition"))
def test_API_create_generated(api, create_ctx, case):
    payload = json_base("createRequisition", create_ctx)
    payload = apply_value(payload, case["field"], case["value"], make_resolver(create_ctx, payload["items"][0]))
    r = api("user_it").post("/requisition/api/create/", json=payload)
    if case["expected"] == "valid":
        assert r.status_code == 200 and r.json()["success"] is True
        req = Requisition.objects.get(pk=r.json()["requisition_id"])            # read-back
        assert req.status == "pending_hod" and req.items.count() == len(payload["items"])
    else:
        assert r.status_code == 400 and r.json()["success"] is False
        assert not Requisition.objects.exists()                                 # read-back after rejection


# --------------------------------------------------------------------------- updateRequisition (FR-15)
@pytest.mark.parametrize("case", params("updateRequisition"))
def test_API_update_generated(api, users, make_req, create_ctx, case):
    req = make_req(users["user_it"], status="sent_back", sent_back_reason="Add cost centre")
    payload = json_base("updateRequisition", create_ctx)
    payload = apply_value(payload, case["field"], case["value"], make_resolver(create_ctx, payload["items"][0]))
    r = api("user_it").post(f"/requisition/{req.pk}/api/update/", json=payload)
    req.refresh_from_db()
    if case["expected"] == "valid":
        assert r.status_code == 200 and r.json()["success"] is True
        assert req.status == "pending_hod" and req.sent_back_reason is None
    else:
        assert r.status_code == 400 and r.json()["success"] is False
        assert req.status == "sent_back" and req.sent_back_reason == "Add cost centre"


# --------------------------------------------------------------------------- hodDecision (WF1)
@pytest.mark.parametrize("case", params("hodDecision"))
def test_API_hod_decision_generated(api, users, make_item, make_req, case):
    req = make_req(users["user_it"], status="pending_hod", lines=[(make_item(stock=10), 4)])
    op = "hodDecision"
    form = {"action": valid_value(op, "action"), "status": valid_value(op, "status"),
            "notes": valid_value(op, "notes"), "rejection_reason": "", "sent_back_reason": ""}
    form.update(case["context"])                       # e.g. action=rejected for rejection_reason cases
    form = apply_value(form, case["field"], case["value"], lambda v: v)
    # Keep every OTHER field valid: a reject / send-back decision needs its reason (BR-2b).
    reason_for = {"rejected": "rejection_reason", "sent_back": "sent_back_reason"}
    needed = reason_for.get(form.get("action"))
    if needed and case["field"] != needed:
        form[needed] = valid_value(op, needed)
    r = api("hod_it").post(f"/requisition/{req.pk}/hod-approval/", data=form)
    req.refresh_from_db()
    if case["expected"] == "valid":
        assert r.status_code == 302 and r.headers["Location"] == "/requisition/hod/"
        assert req.status == form["action"] and req.hod_approver == users["hod_it"]
    else:
        assert r.status_code == 200                    # form re-rendered with an error
        assert req.status == "pending_hod" and req.hod_approver is None


# --------------------------------------------------------------------------- issueItems (WF2)
@pytest.fixture
def issue_ctx(users, make_item, make_req):
    """Line A: requested 4, stock 10 (limit = requested).  Line B: requested 6, stock 4 (limit = stock)."""
    item_a, item_b = make_item(stock=10), make_item(stock=4)
    req_a = make_req(users["user_it"], status="authorized", lines=[(item_a, 4)], hod_approver=users["hod_it"])
    req_b = make_req(users["user_it"], status="authorized", lines=[(item_b, 6)], hod_approver=users["hod_it"])
    other = make_req(users["user_it"], status="authorized", lines=[(make_item(stock=10), 1)])
    return {"a": req_a, "b": req_b, "other_line": other.items.get().pk}


@pytest.mark.parametrize("case", params("issueItems"))
def test_API_issue_generated(api, issue_ctx, case):
    op = "issueItems"
    value = case["value"]
    req = issue_ctx["a"]
    if isinstance(value, dict) and value.get("ref") == "item.quantity_total":
        req = issue_ctx["b"]                           # the stock-limited line
    line = req.items.get()
    item = line.item
    stock_before = item.quantity_total
    refs = {"line.quantity_requested": line.quantity_requested, "item.quantity_total": stock_before,
            "own_line": line.pk, "other_requisition_line": issue_ctx["other_line"], "unknown_line": 999_999}

    def resolve(v):
        if isinstance(v, dict) and "offset" in v:
            return refs[v["ref"]] + v["offset"]
        if isinstance(v, dict) and "ref" in v:
            return refs[v["ref"]]
        return v

    form = {"items-TOTAL_FORMS": valid_value(op, "items-TOTAL_FORMS"),
            "items-INITIAL_FORMS": valid_value(op, "items-INITIAL_FORMS"),
            "items-MIN_NUM_FORMS": 0, "items-MAX_NUM_FORMS": 1000,
            "items-0-id": line.pk, "items-0-requisition": req.pk,
            "items-0-quantity_issued": valid_value(op, "items-0-quantity_issued"),
            "items-0-notes": valid_value(op, "items-0-notes")}
    form = apply_value(form, case["field"], value, resolve)
    r = api("admin").post(f"/requisition/{req.pk}/issue/", data=form)
    req.refresh_from_db()
    line.refresh_from_db()
    item.refresh_from_db()
    outward = Transaction.objects.filter(transaction_type="outward", reference=req.requisition_number)
    if case["expected"] == "valid":
        qty = int(form["items-0-quantity_issued"])
        assert r.status_code == 302 and r.headers["Location"] == "/requisition/admin/"
        assert req.status == "issued" and line.quantity_issued == qty               # read-back
        assert item.quantity_total == stock_before - qty                            # BR-4
        assert outward.count() == (1 if qty > 0 else 0)
    else:
        assert r.status_code == 200 and "Please correct the errors" in r.text
        assert req.status == "authorized" and item.quantity_total == stock_before   # nothing persisted
        assert not outward.exists()


# --------------------------------------------------------------------------- read endpoints
@pytest.mark.parametrize("case", params("itemSuggestions") + params("itemDetails"))
def test_API_item_lookup_generated(api, make_item, case):
    make_item(code="ST001", description="Blue pen")
    make_item(code="HK001", description="Floor cleaner", item_type="housekeeping")
    make_item(code="BOOK01", description="Notebook A5")   # matches the generator's valid 'q' value ("ok")
    url = "/requisition/api/items/" if case["operation"] == "itemSuggestions" else "/inventory/api/item-details/"
    q = {} if case["value"] == "__missing__" else {case["field"]: case["value"]}
    r = api("user_it").get(url, params=q)
    # Filters never reject a request: an "invalid" filter value must simply match nothing.
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    if case["expected"] == "invalid":
        assert rows == []
    elif case["field"] == "type" and case["value"] != "__missing__":
        assert rows and all(row["item_type"] == case["value"] for row in rows)
