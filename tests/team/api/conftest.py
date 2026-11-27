"""API test harness: real HTTP (requests) against pytest-django's live server.

* Every field value sent comes from tests/team/datagen/generated/cases.json (generator output).
  Only the *context* - which user is logged in, which requisition/state/stock is seeded -
  comes from fixtures.
* Every request/response is appended to reports/tmp/api_calls.jsonl so that
  coverage_report.py can measure the API coverage criteria against the spec.
"""
import json
import re
from pathlib import Path

import pytest
import requests

ROOT = Path(__file__).resolve().parents[3]
CASES = json.loads((ROOT / "tests/team/datagen/generated/cases.json").read_text())["cases"]
CALL_LOG = ROOT / "reports/tmp/api_calls.jsonl"
PASSWORD = "Test@12345"


def cases_for(operation, **filters):
    out = [c for c in CASES if c["operation"] == operation]
    for k, v in filters.items():
        out = [c for c in out if c[k] == v]
    return out


def valid_value(operation, field):
    """The generator's first valid representative for a field (used to build base payloads)."""
    for c in cases_for(operation, field=field):
        if c["expected"] == "valid" and c["technique"] == "EP":
            return c["value"]
    raise KeyError((operation, field))


def case_id(c):
    return c["id"]


@pytest.fixture(autouse=True)
def _transactional(transactional_db):
    """live_server needs committed data visible to the server thread."""


@pytest.fixture(scope="session", autouse=True)
def _reset_call_log():
    CALL_LOG.parent.mkdir(parents=True, exist_ok=True)
    CALL_LOG.write_text("")


def _template_path(url, base):
    path = url[len(base):].split("?")[0]
    return re.sub(r"/\d+/", "/{pk}/", path)


class ApiClient(requests.Session):
    """requests.Session that logs in through the real login form and records every call."""

    def __init__(self, base, username=None):
        super().__init__()
        self.base = base
        if username:
            self.get(f"{base}/login/")
            r = self.post(f"{base}/login/", data={"username": username, "password": PASSWORD},
                          allow_redirects=False)
            assert r.status_code == 302, f"login failed for {username}"

    def get(self, url, **kwargs):
        # requests.Session.get() forces allow_redirects=True; keep the endpoint's own status instead
        kwargs.setdefault("allow_redirects", False)
        return super().get(url, **kwargs)

    def request(self, method, url, *args, **kwargs):
        if not url.startswith("http"):
            url = self.base + url
        kwargs.setdefault("allow_redirects", False)
        token = self.cookies.get("csrftoken")
        if method.upper() == "POST" and token:
            headers = kwargs.setdefault("headers", {})
            headers.setdefault("X-CSRFToken", token)
            if isinstance(kwargs.get("data"), dict):
                kwargs["data"] = {**kwargs["data"], "csrfmiddlewaretoken": token}
        resp = super().request(method, url, *args, **kwargs)
        body_keys = []
        if resp.headers.get("Content-Type", "").startswith("application/json"):
            try:
                body = resp.json()
                body_keys = sorted(body.keys()) if isinstance(body, dict) else (
                    sorted(body[0].keys()) if body and isinstance(body[0], dict) else [])
            except ValueError:
                pass
        sent = kwargs.get("json") if kwargs.get("json") is not None else kwargs.get("data")
        params = sorted((kwargs.get("params") or {}).keys())
        req_ct = "application/json" if kwargs.get("json") is not None else (
            kwargs.get("headers", {}).get("Content-Type") or
            ("application/x-www-form-urlencoded" if isinstance(kwargs.get("data"), dict) else None))
        with CALL_LOG.open("a") as fh:
            fh.write(json.dumps({
                "method": method.upper(), "path": _template_path(url, self.base), "status": resp.status_code,
                "request_content_type": req_ct, "response_content_type": resp.headers.get("Content-Type", "").split(";")[0],
                "fields": sorted(sent.keys()) if isinstance(sent, dict) else [], "params": params,
                "values": {**({k: v for k, v in sent.items() if isinstance(v, (str, int))} if isinstance(sent, dict) else {}),
                           **{k: v for k, v in (kwargs.get("params") or {}).items() if isinstance(v, (str, int))}},
                "response_keys": body_keys,
            }) + "\n")
        return resp


@pytest.fixture
def api(live_server, users):
    """api('hod_it') -> logged-in ApiClient;  api() -> anonymous client."""
    def _make(username=None):
        return ApiClient(live_server.url, username)
    return _make


def apply_value(payload, field, value, resolve):
    """Set (or remove) one possibly-nested field ('items[0].qty') in a payload dict."""
    target, key = payload, field
    m = re.match(r"^(\w+)\[0\]\.(\w+)$", field)
    if m:
        target, key = payload[m.group(1)][0], m.group(2)
    if value == "__missing__":
        target.pop(key, None)
    else:
        target[key] = resolve(value)
    return payload
