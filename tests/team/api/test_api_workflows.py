"""Workflow-level API tests over real HTTP: state transitions (BR-3), role decision tables
(BR-2 / DT-1, issue permission / DT-4), repeated requests, cross-workflow read-back, and the
method / authentication / content-type coverage of every operation.

Field values still come from the generator (valid_value); fixtures only choose the role and
the seeded state.
"""
import pytest

from core.models import Notification
from inventory.models import Transaction
from requisition.models import Requisition
from tests.team.api.conftest import valid_value

HOD = "hodDecision"
ISSUE = "issueItems"


def decision(action, **extra):
    form = {"action": action, "status": valid_value(HOD, "status"), "notes": valid_value(HOD, "notes"),
            "rejection_reason": "", "sent_back_reason": ""}
    if action == "rejected":
        form["rejection_reason"] = valid_value(HOD, "rejection_reason")
    if action == "sent_back":
        form["sent_back_reason"] = valid_value(HOD, "sent_back_reason")
    form.update(extra)
    return form


def issue_form(req, qty=None, notes=None):
    line = req.items.get()
    return {"items-TOTAL_FORMS": valid_value(ISSUE, "items-TOTAL_FORMS"),
            "items-INITIAL_FORMS": valid_value(ISSUE, "items-INITIAL_FORMS"),
            "items-MIN_NUM_FORMS": 0, "items-MAX_NUM_FORMS": 1000,
            "items-0-id": line.pk, "items-0-requisition": req.pk,
            "items-0-quantity_issued": valid_value(ISSUE, "items-0-quantity_issued") if qty is None else qty,
            "items-0-notes": valid_value(ISSUE, "items-0-notes") if notes is None else notes}


def outward(req):
    return Transaction.objects.filter(transaction_type="outward", reference=req.requisition_number)


@pytest.fixture
def seed(users, make_item, make_req):
    item = make_item(stock=10, code="ST001")

    def _req(status, initiator="user_it", qty=4, **extra):
        return make_req(users[initiator], status=status, lines=[(item, qty)], **extra)
    _req.item = item
    return _req


# =========================================================================== BR-3 state transitions
VALID_TRANSITIONS = [
    # (from, actor, request, to)
    ("pending_hod", "hod_it", "approve", "authorized"),
    ("pending_hod", "hod_it", "send_back", "sent_back"),
    ("pending_hod", "hod_it", "reject", "rejected"),
    ("pending_hod", "user_it", "cancel", "cancelled"),
    ("draft", "user_it", "cancel", "cancelled"),
    ("sent_back", "user_it", "resubmit", "pending_hod"),
    ("authorized", "admin", "issue", "issued"),
]
INVALID_TRANSITIONS = [
    ("draft", "hod_it", "approve", None),
    ("pending_hod", "admin", "issue", None),
    ("sent_back", "hod_it", "approve", None),
    ("sent_back", "user_it", "cancel", None),
    ("authorized", "hod_it", "approve", None),
    ("authorized", "user_it", "cancel", None),
    ("rejected", "admin", "issue", None),
    ("rejected", "user_it", "resubmit", None),
    ("issued", "admin", "issue", None),
    ("cancelled", "hod_it", "approve", None),
    ("cancelled", "admin", "issue", None),
]


def perform(client, req, request, create_item):
    if request == "approve":
        return client.post(f"/requisition/{req.pk}/hod-approval/", data=decision("authorized"))
    if request == "send_back":
        return client.post(f"/requisition/{req.pk}/hod-approval/", data=decision("sent_back"))
    if request == "reject":
        return client.post(f"/requisition/{req.pk}/hod-approval/", data=decision("rejected"))
    if request == "cancel":
        return client.get(f"/requisition/{req.pk}/cancel/")
    if request == "resubmit":
        return client.post(f"/requisition/{req.pk}/api/update/", json={
            "purpose": valid_value("updateRequisition", "purpose"),
            "items": [{"id": create_item.pk, "qty": valid_value("updateRequisition", "items[0].qty")}]})
    if request == "issue":
        return client.post(f"/requisition/{req.pk}/issue/", data=issue_form(req, qty=3))
    raise ValueError(request)


@pytest.mark.parametrize("start,actor,request_,end", VALID_TRANSITIONS,
                         ids=[f"{a}--{r}-->{b}" for a, _, r, b in VALID_TRANSITIONS])
def test_API_ST_valid_transition(api, seed, start, actor, request_, end):
    req = seed(start)
    r = perform(api(actor), req, request_, seed.item)
    assert r.status_code in (200, 302)
    req.refresh_from_db()
    assert req.status == end


@pytest.mark.parametrize("start,actor,request_,_", INVALID_TRANSITIONS,
                         ids=[f"{a}--{r}-X" for a, _, r, _ in INVALID_TRANSITIONS])
def test_API_ST_invalid_transition_refused(api, seed, start, actor, request_, _):
    req = seed(start)
    stock = seed.item.quantity_total
    perform(api(actor), req, request_, seed.item)
    req.refresh_from_db()
    seed.item.refresh_from_db()
    assert req.status == start                       # state unchanged
    assert seed.item.quantity_total == stock and not outward(req).exists()


@pytest.mark.defect
@pytest.mark.xfail(strict=True, reason="F4: Admin can move issued -> authorized through the HOD view")
def test_API_ST_issued_cannot_be_reauthorized_by_admin(api, seed):
    req = seed("issued")
    api("admin").post(f"/requisition/{req.pk}/hod-approval/", data=decision("authorized", status="issued"))
    req.refresh_from_db()
    assert req.status == "issued"


# =========================================================================== DT-1 approval authority (BR-2)
DT1 = [
    # rule, user, initiator dept, status, expected GET code
    ("R1 hod+dept+same+pending", "hod_it", "user_it", "pending_hod", 200),
    ("R2 hod+dept+other dept", "hod_hr", "user_it", "pending_hod", 404),
    ("R3 hod+no dept", "hod_nodept", "user_it", "pending_hod", 404),
    ("R4 hod+same dept+not pending", "hod_it", "user_it", "authorized", 404),
    ("R5 initiator", "user_it", "user_it", "pending_hod", 404),
    ("R6 super admin", "superadmin", "user_it", "pending_hod", 404),
]


@pytest.mark.parametrize("rule,user,initiator,status,code", DT1, ids=[r[0] for r in DT1])
def test_API_DT1_approval_authority(api, seed, rule, user, initiator, status, code):
    req = seed(status, initiator=initiator)
    assert api(user).get(f"/requisition/{req.pk}/hod-approval/").status_code == code


@pytest.mark.defect
@pytest.mark.xfail(strict=True, reason="F4: Admin is allowed into the HOD approval view")
def test_API_DT1_R7_admin_cannot_approve(api, seed):
    req = seed("pending_hod")
    api("admin").post(f"/requisition/{req.pk}/hod-approval/", data=decision("authorized"))
    req.refresh_from_db()
    assert req.status == "pending_hod"


# =========================================================================== DT-4 issue permission
@pytest.mark.parametrize("who", ["admin"])
def test_API_DT4_admin_may_issue(api, seed, who):
    req = seed("authorized")
    r = api(who).post(f"/requisition/{req.pk}/issue/", data=issue_form(req, qty=3))
    assert r.status_code == 302


@pytest.mark.defect
@pytest.mark.xfail(strict=True, reason="F3: IssueItemsView has no Admin role check")
@pytest.mark.parametrize("who", ["hod_it", "user_it", "superadmin"])
def test_API_DT4_non_admin_cannot_issue(api, seed, who):
    req = seed("authorized")
    api(who).post(f"/requisition/{req.pk}/issue/", data=issue_form(req, qty=3))
    req.refresh_from_db()
    assert req.status == "authorized" and not outward(req).exists()


# =========================================================================== repeated requests
def test_API_REP_repeat_issue_no_duplicate(api, seed):
    req = seed("authorized")
    c = api("admin")
    assert c.post(f"/requisition/{req.pk}/issue/", data=issue_form(req, qty=3)).status_code == 302
    assert c.post(f"/requisition/{req.pk}/issue/", data=issue_form(req, qty=3)).status_code == 404
    seed.item.refresh_from_db()
    assert outward(req).count() == 1 and seed.item.quantity_total == 7


def test_API_REP_repeat_approval_no_duplicate_notifications(api, seed):
    req = seed("pending_hod")
    c = api("hod_it")
    c.post(f"/requisition/{req.pk}/hod-approval/", data=decision("authorized"))
    count = Notification.objects.count()
    assert c.post(f"/requisition/{req.pk}/hod-approval/", data=decision("authorized")).status_code == 404
    assert Notification.objects.count() == count


def test_API_REP_double_create_gives_two_distinct_numbers(api, make_item):
    item = make_item()
    body = {"purpose": valid_value("createRequisition", "purpose"),
            "items": [{"id": item.pk, "qty": valid_value("createRequisition", "items[0].qty")}]}
    c = api("user_it")
    n1 = c.post("/requisition/api/create/", json=body).json()["requisition_number"]
    n2 = c.post("/requisition/api/create/", json=body).json()["requisition_number"]
    assert n1 != n2 and Requisition.objects.count() == 2   # no idempotency key: documented weakness


# =========================================================================== cross-workflow WF1 -> WF2
def test_API_X1_approve_then_issue_reads_back_shared_records(api, seed, users):
    req = seed("pending_hod")
    r1 = api("hod_it").post(f"/requisition/{req.pk}/hod-approval/", data=decision("authorized"))
    assert r1.status_code == 302
    req.refresh_from_db()
    assert req.status == "authorized"                                   # WF1 wrote the shared value
    seed.item.refresh_from_db()
    assert seed.item.quantity_total == 10                               # approval never moves stock
    admin = api("admin")
    assert admin.get("/requisition/admin/").status_code == 200
    r2 = admin.post(f"/requisition/{req.pk}/issue/", data=issue_form(req, qty=3))
    assert r2.status_code == 302                                        # WF2 accepted it because of WF1
    req.refresh_from_db()
    seed.item.refresh_from_db()
    assert (req.status, req.hod_approver, req.issuer) == ("issued", users["hod_it"], users["admin"])
    assert seed.item.quantity_total == 7 and outward(req).get().balance_after == 7
    stock_api = api("user_it").get("/requisition/api/items/", params={"q": "ST001"}).json()[0]
    assert stock_api["quantity_total"] == 7                             # read-back through the API


def test_API_X2_rejected_requisition_cannot_be_issued(api, seed):
    req = seed("pending_hod")
    api("hod_it").post(f"/requisition/{req.pk}/hod-approval/", data=decision("rejected"))
    assert api("admin").post(f"/requisition/{req.pk}/issue/", data=issue_form(req, qty=3)).status_code == 404
    seed.item.refresh_from_db()
    assert seed.item.quantity_total == 10


def test_API_X3_send_back_resubmit_approve_issue(api, seed):
    req = seed("pending_hod")
    api("hod_it").post(f"/requisition/{req.pk}/hod-approval/", data=decision("sent_back"))
    perform(api("user_it"), req, "resubmit", seed.item)
    req.refresh_from_db()
    assert req.status == "pending_hod"
    api("hod_it").post(f"/requisition/{req.pk}/hod-approval/", data=decision("authorized"))
    api("admin").post(f"/requisition/{req.pk}/issue/", data=issue_form(req, qty=1))
    req.refresh_from_db()
    assert req.status == "issued"


@pytest.mark.defect
@pytest.mark.xfail(strict=True, reason="F13: issuing the unchanged pre-filled quantity deducts no stock")
def test_API_X4_issue_with_prefilled_defaults_deducts_stock(api, seed):
    req = seed("authorized")
    api("admin").post(f"/requisition/{req.pk}/issue/", data=issue_form(req, qty=4, notes=""))
    seed.item.refresh_from_db()
    assert seed.item.quantity_total == 6 and outward(req).count() == 1


def test_API_X5_rule_rejection_reads_back_unchanged_records(api, seed):
    req = seed("authorized")
    r = api("admin").post(f"/requisition/{req.pk}/issue/", data=issue_form(req, qty=11))
    assert r.status_code == 200 and "Cannot issue more than requested (4)." in r.text
    req.refresh_from_db()
    seed.item.refresh_from_db()
    assert req.status == "authorized" and seed.item.quantity_total == 10 and not outward(req).exists()
    assert not Notification.objects.filter(notification_type="requisition_issued").exists()


# =========================================================================== method / auth / content type
@pytest.mark.parametrize("path", ["/requisition/api/create/", "/requisition/{pk}/api/update/"])
def test_API_M1_get_on_post_only_endpoint_405(api, seed, path):
    req = seed("pending_hod")
    assert api("user_it").get(path.format(pk=req.pk)).status_code == 405


@pytest.mark.parametrize("method,path", [
    ("POST", "/requisition/api/create/"), ("GET", "/requisition/api/items/"),
    ("GET", "/inventory/api/item-details/"), ("GET", "/api/notifications/"),
    ("GET", "/requisition/{pk}/hod-approval/"), ("POST", "/requisition/{pk}/issue/"),
])
def test_API_M2_anonymous_redirected_to_login(api, seed, method, path):
    """Observed: 302 to the HTML login page even for JSON endpoints (weakness A5, expected 401)."""
    req = seed("authorized")
    anon = api()
    anon.get("/login/")                     # obtain a CSRF cookie like a browser would
    r = anon.request(method, path.format(pk=req.pk))
    assert r.status_code == 302 and r.headers["Location"].startswith("/login/")


def test_API_M3_malformed_json_and_wrong_content_type(api):
    c = api("user_it")
    r = c.post("/requisition/api/create/", data="{broken", headers={"Content-Type": "application/json"})
    assert r.status_code == 400 and r.json()["error"].startswith("Invalid JSON")
    r = c.post("/requisition/api/create/", data={"purpose": "x"})     # form-encoded instead of JSON
    assert r.status_code == 400 and r.json()["success"] is False


def test_API_M4_missing_csrf_token_rejected(live_server, users):
    import requests
    s = requests.Session()
    s.get(f"{live_server.url}/login/")
    r = s.post(f"{live_server.url}/login/", data={"username": "admin", "password": "Test@12345"},
               allow_redirects=False)
    assert r.status_code == 403                                         # CSRF protection active


def test_API_M5_login_success_and_failure(api, users):
    c = api()
    c.get("/login/")
    assert c.post("/login/", data={"username": "admin", "password": "wrong"}).status_code == 200
    assert c.post("/login/", data={"username": "admin", "password": "Test@12345"}).status_code == 302


def test_API_M6_detail_and_notifications_read_back(api, seed):
    req = seed("pending_hod")
    api("hod_it").post(f"/requisition/{req.pk}/hod-approval/", data=decision("authorized"))
    assert api("user_it").get(f"/requisition/{req.pk}/").status_code == 200
    assert api("user_hr").get(f"/requisition/{req.pk}/").status_code == 404
    body = api("user_it").get("/api/notifications/").json()
    assert body["unread_count"] == 1
    assert body["notifications"][0]["title"] == f"Requisition Approved: {req.requisition_number}"


def test_API_M7_issue_screen_get(api, seed):
    req = seed("authorized")
    assert api("admin").get(f"/requisition/{req.pk}/issue/").status_code == 200
    pending = seed("pending_hod")
    assert api("admin").get(f"/requisition/{pending.pk}/issue/").status_code == 404


@pytest.mark.defect
@pytest.mark.xfail(strict=True, reason="F3: the issue screen is served to non-Admin users")
def test_API_M8_issue_screen_denied_to_hod(api, seed):
    req = seed("authorized")
    assert api("hod_it").get(f"/requisition/{req.pk}/issue/").status_code == 403
