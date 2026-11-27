#!/usr/bin/env python
"""Measure black-box API coverage criteria (Martin-Lopez, Segura & Ruiz-Cortes, 2019) by
comparing the calls recorded during the API test run with tests/team/datagen/openapi.yaml.

    python tests/team/api/coverage_report.py [--min 100]

Input criteria : paths, operations, parameters/fields, parameter values (enums), request content types
Output criteria: status-code classes, status codes, response body properties, response content types
Writes reports/api_coverage.md and exits 1 if any criterion is below --min (default 100).
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SPEC = yaml.safe_load((ROOT / "tests/team/datagen/openapi.yaml").read_text())
CALLS = [json.loads(line) for line in (ROOT / "reports/tmp/api_calls.jsonl").read_text().splitlines() if line]
OUT = ROOT / "reports/api_coverage.md"


def deref(node):
    while isinstance(node, dict) and "$ref" in node:
        cur = SPEC
        for p in node["$ref"].lstrip("#/").split("/"):
            cur = cur[p]
        node = cur
    return node


def top_fields(op):
    """Top-level request fields and enum values declared for an operation."""
    fields, enums, ctypes = set(), set(), set()
    for ctype, media in op.get("requestBody", {}).get("content", {}).items():
        ctypes.add(ctype)
        for name, sch in deref(media["schema"]).get("properties", {}).items():
            fields.add(name)
            for v in deref(sch).get("enum", []):
                enums.add((name, v))
    for prm in op.get("parameters", []):
        prm = deref(prm)
        if prm["in"] == "query":
            fields.add(prm["name"])
            for v in prm["schema"].get("enum", []):
                enums.add((prm["name"], v))
    return fields, enums, ctypes


def response_props(resp):
    for media in resp.get("content", {}).values():
        sch = deref(media["schema"])
        if sch.get("type") == "array":
            sch = deref(sch["items"])
        return set(sch.get("properties", {}))
    return set()


def main(argv):
    minimum = float(argv[argv.index("--min") + 1]) if "--min" in argv else 100.0
    want = {k: set() for k in ("paths", "operations", "parameters", "values", "req_ctypes",
                               "status_classes", "status_codes", "body_props", "resp_ctypes")}
    got = {k: set() for k in want}

    for path, ops in SPEC["paths"].items():
        want["paths"].add(path)
        for method, op in ops.items():
            key = (method.upper(), path)
            want["operations"].add(key)
            fields, enums, ctypes = top_fields(op)
            want["parameters"] |= {(key, f) for f in fields}
            want["values"] |= {(key, f, v) for f, v in enums}
            want["req_ctypes"] |= {(key, c) for c in ctypes}
            for code, resp in op["responses"].items():
                want["status_codes"].add((key, code))
                want["status_classes"].add((key, code[0] + "xx"))
                want["body_props"] |= {(key, code, p) for p in response_props(resp)}
                for c in resp.get("content", {}):
                    want["resp_ctypes"].add((key, code, c))

    blocked = set()   # documented responses the baseline cannot return because of an open defect
    for path, ops in SPEC["paths"].items():
        for method, op in ops.items():
            for code, resp in op["responses"].items():
                if "x-observed" in resp or "x-expected-instead" in resp:
                    blocked.add(((method.upper(), path), code))
    for c in CALLS:
        key = (c["method"], c["path"])
        if key not in want["operations"] and c["status"] == 405:
            # a method the path does not define: credit the documented 405 of that path's operations
            for m in SPEC["paths"].get(c["path"], {}):
                if "405" in SPEC["paths"][c["path"]][m]["responses"]:
                    got["status_codes"].add(((m.upper(), c["path"]), "405"))
            continue
        if key not in want["operations"]:
            continue
        code = str(c["status"])
        got["paths"].add(c["path"])
        got["operations"].add(key)
        got["parameters"] |= {(key, f) for f in c["fields"] + c["params"]}
        got["values"] |= {(key, f, v) for f, v in c["values"].items()}
        if c["request_content_type"]:
            got["req_ctypes"].add((key, c["request_content_type"]))
        got["status_codes"].add((key, code))
        got["status_classes"].add((key, code[0] + "xx"))
        got["body_props"] |= {(key, code, p) for p in c["response_keys"]}
        got["resp_ctypes"].add((key, code, c["response_content_type"]))

    names = {"paths": "Path coverage", "operations": "Operation coverage", "parameters": "Parameter coverage",
             "values": "Parameter-value coverage (enums)", "req_ctypes": "Request content-type coverage",
             "status_classes": "Status-code class coverage", "status_codes": "Status-code coverage",
             "body_props": "Response body-property coverage", "resp_ctypes": "Response content-type coverage"}
    rows, failed = [], []
    for k, label in names.items():
        w = want[k]
        hit = w & got[k]
        miss = w - got[k]
        if k == "status_codes":
            blocked_miss = {m for m in miss if m in blocked}
        elif k in ("status_classes", "body_props", "resp_ctypes"):
            blocked_miss = {m for m in miss if any(b[0] == m[0] and (len(m) < 3 and b[1][0] == m[1][0] or len(m) >= 3 and b[1] == m[1]) for b in blocked)}
        else:
            blocked_miss = set()
        reachable = len(w) - len(blocked_miss)
        pct = 100.0 * len(hit) / reachable if reachable else 100.0
        missing = sorted(map(str, miss - blocked_miss))[:8]
        blk = "; ".join(sorted(map(str, blocked_miss))) or "-"
        rows.append(f"| {label} | {len(hit)}/{reachable} (+{len(blocked_miss)} blocked) | {pct:.1f}% | {'; '.join(missing) or '-'} | {blk} |")
        if pct < minimum:
            failed.append(label)
    note = ("'Blocked' = an expected response documented in the spec that the baseline cannot return because "
            "of an open defect (e.g. 403 for a non-Admin issue - F3). The tests for it exist and are xfail(strict); "
            "the criterion becomes coverable when the defect is fixed.")
    text = "\n".join([f"# API coverage criteria ({len(CALLS)} recorded calls)", "",
                      "| Criterion | Covered / reachable | % of reachable | Not covered | Blocked by an open defect (documented in x-observed) |", "|---|---|---|---|---|", *rows, "", note, ""])
    OUT.write_text(text)
    print(text)
    if failed:
        print(f"BELOW {minimum}%: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
