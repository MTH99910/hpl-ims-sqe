"""White-box tests for the supporting views of the Requisition module and the in-scope
core/inventory endpoints (login, notifications, item lookup APIs).
"""
import json

import pytest
from django.contrib.messages import get_messages

from core.models import Notification
from requisition.models import Requisition, RequisitionLineItem


def msgs(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


def post_json(client, url, payload):
    body = payload if isinstance(payload, str) else json.dumps(payload)
    return client.post(url, body, content_type="application/json")


# =========================================================================== dashboards
class TestDashboards:
    def test_UT80_initiator_dashboard_counts(self, client_for, users, make_req):
        u = users["user_it"]
        for s in ["pending_hod", "authorized", "issued", "sent_back"]:
            make_req(u, status=s)
        make_req(users["user_hr"], status="pending_hod")
        ctx = client_for("user_it").get("/requisition/initiator/").context
        assert (ctx["pending_count"], ctx["completed_count"], ctx["sent_back_count"]) == (2, 1, 1)
        assert len(ctx["my_requisitions"]) == 4

    def test_UT81_hod_dashboard_lists_own_department_pending_only(self, client_for, users, make_req):
        mine = make_req(users["user_it"], status="pending_hod")
        make_req(users["user_hr"], status="pending_hod")
        make_req(users["user_it"], status="authorized", hod_approver=users["hod_it"])
        ctx = client_for("hod_it").get("/requisition/hod/").context
        assert list(ctx["pending_approvals"]) == [mine] and ctx["approval_count"] == 1
        assert len(ctx["recent_approvals"]) == 1

    def test_UT82_hod_without_department_sees_empty_queue(self, client_for, users, make_req):
        make_req(users["user_it"], status="pending_hod")
        ctx = client_for("hod_nodept").get("/requisition/hod/").context
        assert (ctx["pending_approvals"], ctx["approval_count"], ctx["recent_approvals"]) == ([], 0, [])

    def test_UT83_admin_dashboard_lists_authorized(self, client_for, users, make_req):
        auth = make_req(users["user_it"], status="authorized")
        make_req(users["user_it"], status="issued")
        ctx = client_for("admin").get("/requisition/admin/").context
        assert list(ctx["pending_issues"]) == [auth] and ctx["pending_count"] == 1
        assert len(ctx["recent_issues"]) == 1
        assert (ctx["total_requisitions"], ctx["today_requisitions"]) == (2, 2)


# =========================================================================== list / detail / print
class TestListDetailPrint:
    @pytest.fixture
    def reqs(self, users, make_req):
        return {"it_p": make_req(users["user_it"], status="pending_hod"),
                "it_i": make_req(users["user_it"], status="issued"),
                "hr_p": make_req(users["user_hr"], status="pending_hod")}

    @pytest.mark.parametrize("who,expected", [
        ("hod_it", {"it_p", "it_i"}), ("user_it", {"it_p", "it_i"}),
        ("admin", {"it_p", "it_i", "hr_p"}), ("hod_nodept", {"it_p", "it_i", "hr_p"}),
    ])
    def test_UT84_list_role_scoping(self, client_for, reqs, who, expected):
        got = set(client_for(who).get("/requisition/").context["requisitions"])
        assert got == {reqs[k] for k in expected}

    def test_UT85_list_filters_status_and_dates(self, client_for, reqs):
        c = client_for("admin")
        assert set(c.get("/requisition/?status=issued").context["requisitions"]) == {reqs["it_i"]}
        assert len(c.get("/requisition/?date_from=2000-01-01&date_to=2999-01-01").context["requisitions"]) == 3
        assert len(c.get("/requisition/?date_from=2999-01-01").context["requisitions"]) == 0
        assert c.get("/requisition/").context["filter_form"] is not None

    @pytest.mark.parametrize("who,key,code", [
        ("user_it", "it_p", 200), ("user_it", "hr_p", 404), ("hod_it", "it_p", 200),
        ("hod_it", "hr_p", 404), ("admin", "hr_p", 200),
    ])
    def test_UT86_detail_role_scoping(self, client_for, reqs, who, key, code):
        r = client_for(who).get(f"/requisition/{reqs[key].pk}/")
        assert r.status_code == code
        if code == 200:
            assert list(r.context["line_items"]) == list(reqs[key].items.all())

    def test_UT87_print_view(self, client_for, reqs):
        r = client_for("admin").get(f"/requisition/{reqs['it_p'].pk}/print/")
        assert r.status_code == 200 and "line_items" in r.context


# =========================================================================== create (UI form)
class TestCreateView:
    def form(self, item=None, qty=2, purpose="Pens for the new interns batch", delete=False):
        data = {"purpose": purpose, "notes": "", "items-TOTAL_FORMS": 1, "items-INITIAL_FORMS": 0}
        if item is not None:
            data.update({"items-0-item": item.pk, "items-0-quantity_requested": qty, "items-0-uom": "pcs"})
            if delete:
                data["items-0-DELETE"] = "on"
        return data

    def test_UT88_get_shows_empty_formset(self, client_for):
        r = client_for("user_it").get("/requisition/create/")
        assert r.status_code == 200 and r.context["title"] == "Create Requisition"
        assert r.context["line_items_formset"].total_form_count() == 0

    def test_UT89_valid_create(self, client_for, users, make_item):
        item = make_item(stock=10)
        r = client_for("user_it").post("/requisition/create/", self.form(item))
        req = Requisition.objects.get()
        assert r.status_code == 302 and req.status == "pending_hod" and req.initiator == users["user_it"]
        assert req.items.get().quantity_requested == 2

    def test_UT90_invalid_line_rerenders_with_message(self, client_for, make_item):
        item = make_item(stock=1)
        r = client_for("user_it").post("/requisition/create/", self.form(item, qty=5))
        assert r.status_code == 200 and not Requisition.objects.exists()
        assert msgs(r)[0].startswith("Please correct the errors in the items form: quantity_requested:")

    def test_UT91_non_form_error_reported(self, client_for, make_item):
        data = self.form(make_item())
        data["items-TOTAL_FORMS"] = 2001  # > absolute_max (max_num 1000 + 1000) -> non-form error
        r = client_for("user_it").post("/requisition/create/", data)
        assert r.status_code == 200 and "Please submit at most" in msgs(r)[0]

    def test_UT92_no_items_rejected(self, client_for, make_item):
        r = client_for("user_it").post("/requisition/create/", self.form(make_item(), delete=True))
        assert msgs(r) == ["Please add at least one item to the requisition."]
        assert not Requisition.objects.exists()

    def test_UT93_invalid_main_form_not_saved(self, client_for, make_item):
        r = client_for("user_it").post("/requisition/create/", self.form(make_item(), purpose=""))
        assert r.status_code == 200 and not Requisition.objects.exists()


# =========================================================================== update (UI form)
class TestUpdateView:
    def test_UT94_get_resubmission_context(self, client_for, users, make_item, make_req):
        req = make_req(users["user_it"], status="sent_back", lines=[(make_item(), 2)], sent_back_reason="Fix")
        ctx = client_for("user_it").get(f"/requisition/{req.pk}/update/").context
        assert (ctx["title"], ctx["is_resubmission"], ctx["sent_back_reason"]) == ("Resubmit Requisition", True, "Fix")
        assert json.loads(ctx["existing_items_json"])[0]["quantity_requested"] == 2

    def test_UT95a_get_update_with_items(self, client_for, users, make_item, make_req):
        req = make_req(users["user_it"], status="pending_hod", lines=[(make_item(), 1)])
        ctx = client_for("user_it").get(f"/requisition/{req.pk}/update/").context
        assert (ctx["title"], ctx["is_resubmission"]) == ("Update Requisition", False)
        assert ctx["line_items_formset"].total_form_count() == 1

    @pytest.mark.defect
    @pytest.mark.xfail(strict=True, reason="F15: update page crashes for a requisition with no line items")
    def test_UT95b_get_update_without_items(self, client_for, users, make_req):
        req = make_req(users["user_it"], status="pending_hod")
        c = client_for("user_it")
        c.raise_request_exception = False
        assert c.get(f"/requisition/{req.pk}/update/").status_code == 200

    def test_UT96_other_users_requisition_404(self, client_for, users, make_req):
        req = make_req(users["user_hr"])
        assert client_for("user_it").get(f"/requisition/{req.pk}/update/").status_code == 404

    @pytest.mark.defect
    @pytest.mark.xfail(strict=True, reason="F14: UI update POST reads cleaned_data of an unbound formset")
    def test_UT97_ui_update_post_saves(self, client_for, users, make_item, make_req):
        item = make_item(stock=10)
        req = make_req(users["user_it"], status="pending_hod", lines=[(item, 2)])
        c = client_for("user_it")
        c.raise_request_exception = False
        r = c.post(f"/requisition/{req.pk}/update/", {
            "purpose": "Updated purpose text", "notes": "", "items-TOTAL_FORMS": 1, "items-INITIAL_FORMS": 1,
            "items-0-item": item.pk, "items-0-quantity_requested": 3, "items-0-uom": "pcs"})
        assert r.status_code == 302


# =========================================================================== cancel
class TestCancel:
    @pytest.mark.parametrize("status,ok", [("draft", True), ("pending_hod", True), ("sent_back", False),
                                           ("authorized", False), ("issued", False)])
    def test_UT98_cancel_allowed_only_before_hod_action(self, client_for, users, make_req, status, ok):
        req = make_req(users["user_it"], status=status)
        r = client_for("user_it").get(f"/requisition/{req.pk}/cancel/")
        req.refresh_from_db()
        assert (req.status == "cancelled") is ok
        assert r.url == ("/requisition/" if ok else f"/requisition/{req.pk}/")

    def test_UT99_cannot_cancel_others(self, client_for, users, make_req):
        req = make_req(users["user_hr"])
        assert client_for("user_it").get(f"/requisition/{req.pk}/cancel/").status_code == 404


# =========================================================================== JSON APIs
class TestCreateAPI:
    url = "/requisition/api/create/"

    def test_UT100_get_not_allowed(self, client_for):
        assert client_for("user_it").get(self.url).status_code == 405

    def test_UT101_valid_create_notifies_department_hods(self, client_for, users, make_item):
        item = make_item()
        r = post_json(client_for("user_it"), self.url, {"purpose": "Pens for interns batch",
                                                        "items": [{"id": item.pk, "qty": 2, "notes": "n"}]})
        body = r.json()
        assert r.status_code == 200 and body["success"] is True
        req = Requisition.objects.get(pk=body["requisition_id"])
        assert body["requisition_number"] == req.requisition_number and req.status == "pending_hod"
        assert [n.user.username for n in Notification.objects.all()] == ["hod_it"]
        assert req.items.get().uom == "pcs"

    def test_UT102_initiator_without_department(self, client_for, make_item):
        r = post_json(client_for("admin"), self.url, {"purpose": "Restock for the store",
                                                      "items": [{"id": make_item().pk, "qty": 1}]})
        assert r.status_code == 200 and Requisition.objects.get().department == "Unknown"
        assert not Notification.objects.exists()

    @pytest.mark.parametrize("payload,error", [
        ({"items": [{"id": 1, "qty": 1}]}, "Purpose is required"),
        ({"purpose": "short", "items": [{"id": 1, "qty": 1}]}, "Purpose must be at least 10 characters"),
        ({"purpose": "Valid purpose text"}, "At least one item is required"),
        ({"purpose": "Valid purpose text", "items": [{"qty": 1}]}, "Item 1: Item ID is required"),
        ({"purpose": "Valid purpose text", "items": [{"id": 1, "qty": 0}]}, "Item 1: Quantity must be at least 1"),
    ])
    def test_UT103_validation_errors(self, client_for, payload, error):
        r = post_json(client_for("user_it"), self.url, payload)
        assert (r.status_code, r.json()["error"]) == (400, error)
        assert not Requisition.objects.exists()

    def test_UT104_malformed_json(self, client_for):
        r = post_json(client_for("user_it"), self.url, "{not json")
        assert r.status_code == 400 and r.json()["error"].startswith("Invalid JSON")

    @pytest.mark.defect
    @pytest.mark.xfail(strict=True, reason="F6: unknown item id -> 500 and an orphan requisition is left")
    def test_UT105_unknown_item_rejected_cleanly(self, client_for):
        r = post_json(client_for("user_it"), self.url, {"purpose": "Valid purpose text", "items": [{"id": 999, "qty": 1}]})
        assert r.status_code == 400
        assert not Requisition.objects.exists()

    def test_UT106_unknown_item_observed_behaviour(self, client_for):
        """Observed (baseline) behaviour, kept so the except-branch is covered: 500 + orphan row."""
        r = post_json(client_for("user_it"), self.url, {"purpose": "Valid purpose text", "items": [{"id": 999, "qty": 1}]})
        assert r.status_code == 500 and r.json()["error"].startswith("Server error:")
        assert Requisition.objects.count() == 1 and not RequisitionLineItem.objects.exists()


class TestUpdateAPI:
    def url(self, req):
        return f"/requisition/{req.pk}/api/update/"

    def test_UT107_get_not_allowed(self, client_for, users, make_req):
        assert client_for("user_it").get(self.url(make_req(users["user_it"]))).status_code == 405

    def test_UT108_resubmission_resets_and_notifies(self, client_for, users, make_item, make_req):
        old, new = make_item(), make_item()
        req = make_req(users["user_it"], status="sent_back", lines=[(old, 1)], sent_back_reason="x",
                       hod_approver=users["hod_it"])
        r = post_json(client_for("user_it"), self.url(req), {"purpose": "Revised purpose text",
                                                             "items": [{"id": new.pk, "qty": 3}]})
        assert "resubmitted for HOD approval" in r.json()["message"]
        req.refresh_from_db()
        assert (req.status, req.sent_back_reason, req.hod_approver) == ("pending_hod", None, None)
        assert list(req.items.values_list("item", "quantity_requested")) == [(new.pk, 3)]
        assert Notification.objects.get().user == users["hod_it"]

    def test_UT109_plain_update_keeps_status(self, client_for, users, make_item, make_req):
        req = make_req(users["user_it"], status="pending_hod", lines=[(make_item(), 1)])
        r = post_json(client_for("user_it"), self.url(req), {"purpose": "Revised purpose text",
                                                             "items": [{"id": make_item().pk, "qty": 2}]})
        assert r.json()["message"].endswith("updated successfully!")
        req.refresh_from_db()
        assert req.status == "pending_hod" and not Notification.objects.exists()

    def test_UT110_resubmit_without_department_sends_no_notification(self, client_for, users, make_item, make_req):
        req = make_req(users["admin"], status="sent_back", lines=[(make_item(), 1)])
        post_json(client_for("admin"), self.url(req), {"purpose": "Revised purpose text",
                                                       "items": [{"id": make_item().pk, "qty": 2}]})
        req.refresh_from_db()
        assert req.status == "pending_hod" and not Notification.objects.exists()

    @pytest.mark.parametrize("status", ["authorized", "issued", "rejected", "cancelled"])
    def test_UT111_not_editable_states(self, client_for, users, make_req, status):
        req = make_req(users["user_it"], status=status)
        r = post_json(client_for("user_it"), self.url(req), {"purpose": "Revised purpose text", "items": []})
        assert (r.status_code, r.json()["error"]) == (400, "This requisition cannot be modified")

    @pytest.mark.parametrize("payload,error", [
        ({"items": [{"id": 1, "qty": 1}]}, "Purpose is required"),
        ({"purpose": "short", "items": [{"id": 1, "qty": 1}]}, "Purpose must be at least 10 characters"),
        ({"purpose": "Valid purpose text", "items": []}, "At least one item is required"),
        ({"purpose": "Valid purpose text", "items": [{"qty": 1}]}, "Item 1: Item ID is required"),
        ({"purpose": "Valid purpose text", "items": [{"id": 1, "qty": 0}]}, "Item 1: Quantity must be at least 1"),
    ])
    def test_UT112_validation_errors(self, client_for, users, make_req, payload, error):
        req = make_req(users["user_it"])
        r = post_json(client_for("user_it"), self.url(req), payload)
        assert (r.status_code, r.json()["error"]) == (400, error)

    def test_UT113_malformed_json_and_server_error(self, client_for, users, make_req):
        req = make_req(users["user_it"])
        c = client_for("user_it")
        assert post_json(c, self.url(req), "{bad").json()["error"].startswith("Invalid JSON")
        r = post_json(c, self.url(req), {"purpose": "Valid purpose text", "items": [{"id": 999, "qty": 1}]})
        assert r.status_code == 500

    def test_UT114_others_requisition_404(self, client_for, users, make_req):
        req = make_req(users["user_hr"])
        r = post_json(client_for("user_it"), self.url(req), {"purpose": "x"})
        assert r.status_code == 500  # Http404 is swallowed by the broad except -> observed 500 (F6 family)


class TestItemSuggestionsAPI:
    def test_UT115_search_type_filter_and_active_only(self, client_for, make_item):
        make_item(code="ST001", description="Blue pen")
        make_item(code="HK001", description="Floor cleaner", item_type="housekeeping")
        make_item(code="ST999", description="Old pen", active=False)
        c = client_for("user_it")
        assert [i["material_code"] for i in c.get("/requisition/api/items/").json()] == ["HK001", "ST001"]
        assert [i["material_code"] for i in c.get("/requisition/api/items/?q=pen").json()] == ["ST001"]
        assert [i["material_code"] for i in c.get("/requisition/api/items/?type=housekeeping").json()] == ["HK001"]
        row = c.get("/requisition/api/items/?q=ST001").json()[0]
        assert (row["quantity_total"], row["location"]) == (10, "N/A")


# =========================================================================== core + inventory endpoints
class TestLoginLogout:
    @pytest.mark.parametrize("who,target", [
        ("superadmin", "/super-admin/"), ("admin", "/requisition/admin/"),
        ("hod_it", "/requisition/hod/"), ("user_it", "/dashboard/"),
    ])
    def test_UT116_role_based_redirect(self, client, users, who, target):
        r = client.post("/login/", {"username": who, "password": "Test@12345"})
        assert (r.status_code, r.url) == (302, target)

    def test_UT117_invalid_credentials(self, client, users):
        r = client.post("/login/", {"username": "admin", "password": "wrong"})
        assert r.status_code == 200 and "Invalid username or password" in msgs(r)[0]

    def test_UT118_get_login_page_and_logout(self, client, users):
        assert client.get("/login/").status_code == 200
        client.force_login(users["admin"])
        r = client.get("/logout/")
        assert r.url == "/login/" and "_auth_user_id" not in client.session


class TestNotificationsAPI:
    def test_UT119_list_read_and_read_all(self, client_for, users):
        mine = [Notification.objects.create(user=users["user_it"], notification_type="requisition_issued",
                                            title=f"T{i}", message="m", link="/x") for i in range(2)]
        other = Notification.objects.create(user=users["user_hr"], notification_type="requisition_issued",
                                            title="X", message="m")
        c = client_for("user_it")
        assert c.get("/notifications/").status_code == 200
        body = c.get("/api/notifications/").json()
        assert body["unread_count"] == 2 and body["notifications"][0]["icon"] == "bi-box-seam text-success"
        assert c.get(f"/api/notifications/{mine[0].pk}/read/").json() == {"success": True}
        assert c.get(f"/api/notifications/{other.pk}/read/").status_code == 404
        c.get("/api/notifications/read-all/")
        assert not Notification.objects.filter(user=users["user_it"], is_read=False).exists()


class TestItemDetailsAPI:
    def test_UT120_search_by_code(self, client_for, make_item):
        make_item(code="ST001"), make_item(code="HK001")
        data = client_for("user_it").get("/inventory/api/item-details/?q=ST").json()
        assert [d["material_code"] for d in data] == ["ST001"]

    @pytest.mark.defect
    @pytest.mark.xfail(strict=True, reason="F5: filtering by type after slicing raises TypeError (500)")
    def test_UT121_type_filter(self, client_for, make_item):
        make_item(code="ST001")
        c = client_for("user_it")
        c.raise_request_exception = False
        assert c.get("/inventory/api/item-details/?q=ST&type=stationery").status_code == 200


def test_UT122_create_notification_helper(users):
    from core.views import create_notification
    create_notification(users["admin"], "requisition_issued", "Title", "Message", "/link")
    n = Notification.objects.get()
    assert (n.title, n.link) == ("Title", "/link")
