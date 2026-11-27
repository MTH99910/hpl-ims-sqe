#!/usr/bin/env python
"""Test-data generator: OpenAPI spec -> equivalence classes + 3-point boundary values.

    python tests/team/datagen/generator.py            # writes generated/cases.json + cases.md
    python tests/team/datagen/generator.py --check    # exit 1 if generated files are stale

For every input of every operation's request body / query parameters it emits cases:

  EP  valid classes   : one representative per valid class (each enum value, a normal value, ...)
  EP  invalid classes : missing-required, wrong type, outside enum, below minimum, too short ...
                        - each invalid case changes exactly ONE field; all others stay valid
  BVA (3-point)       : for every limit L: L-1, L, L+1   (minimum, maximum, minLength, maxLength,
                        minItems, and data-dependent maxima declared with x-maximum-ref)

A data-dependent limit cannot be known when the spec is read, so it is emitted symbolically
as {"ref": "<name>", "offset": -1|0|+1} and resolved by the test against the seeded record.
"""
import hashlib
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SPEC = HERE / "openapi.yaml"
OUT = HERE / "generated"


def deref(spec, node):
    while isinstance(node, dict) and "$ref" in node:
        path = node["$ref"].lstrip("#/").split("/")
        node = spec
        for p in path:
            node = node[p]
    return node


def sample_valid(schema):
    """A representative valid value for a schema (used as the 'all other fields valid' base)."""
    if "enum" in schema:
        return schema["enum"][0]
    if "default" in schema:
        return schema["default"]
    t = schema.get("type")
    if t == "integer":
        return schema.get("minimum", 1)
    if t == "string":
        n = schema.get("minLength", 1)
        return ("Valid text " * 5)[: max(n + 5, 12)].strip() if n > 1 else "ok"
    if t == "array":
        return [sample_valid(schema["items"]) for _ in range(schema.get("minItems", 1))]
    if t == "object":
        return {k: sample_valid(v) for k, v in schema.get("properties", {}).items()}
    return None


def field_cases(name, schema, required, form=False):
    """Yield (technique, class_name, value, expected) for one field.

    form=True: application/x-www-form-urlencoded - every value travels as text, so a
    'not-string' class does not exist there.
    """
    t = schema.get("type")
    if "x-ref-domain" in schema:
        # Keys referencing other records are partitioned by what they point at; numeric
        # boundaries of a primary key carry no meaning, so no BVA is generated (documented).
        for cls, exp in schema["x-ref-domain"].items():
            yield "EP", f"{exp}:{cls}", {"ref": cls}, exp
        yield "EP", "invalid:not-integer", "abc", "invalid"
        if required:
            yield "EP", "invalid:missing", "__missing__", "invalid"
        return
    # ---- EP valid
    if "enum" in schema:
        for v in schema["enum"]:
            yield "EP", f"valid:enum={v}", v, "valid"
        yield "EP", "invalid:outside-enum", "__not_in_enum__", "invalid"
    elif t == "integer":
        yield "EP", "valid:in-range", sample_valid(schema) + (1 if "minimum" in schema else 0), "valid"
        yield "EP", "invalid:not-integer", "abc", "invalid"
        yield "EP", "invalid:decimal", 1.5, "invalid"
    elif t == "string":
        yield "EP", "valid:normal", sample_valid(schema), "valid"
        if schema.get("x-no-limit"):
            yield "EP", "valid:very-long (no documented limit)", "L" * 5000, "valid"
        if schema.get("minLength", 0) >= 1:
            yield "EP", "invalid:empty", "", "invalid"
        if schema.get("x-trim") and "minLength" in schema:
            yield "EP", "invalid:whitespace-padded-too-short", "  " + "a" * (schema["minLength"] - 1) + "  ", "invalid"
        if not form:
            yield "EP", "invalid:not-string", 12345, "invalid"
    elif t == "array":
        yield "EP", "valid:non-empty", {"array_len": max(1, schema.get("minItems", 1))}, "valid"
        yield "EP", "invalid:not-array", "not-a-list", "invalid"
    if required:
        yield "EP", "invalid:missing", "__missing__", "invalid"

    # ---- BVA (3-point) on every declared limit
    if "minimum" in schema:
        m = schema["minimum"]
        for v, exp in ((m - 1, "invalid"), (m, "valid"), (m + 1, "valid")):
            yield "BVA", f"minimum={m}:{v - m:+d}", v, exp
    if "maximum" in schema:
        m = schema["maximum"]
        for v, exp in ((m - 1, "valid"), (m, "valid"), (m + 1, "invalid")):
            yield "BVA", f"maximum={m}:{v - m:+d}", v, exp
    for ref in schema.get("x-maximum-ref", []):
        for off, exp in ((-1, "valid"), (0, "valid"), (1, "invalid")):
            yield "BVA", f"maximum-ref={ref}:{off:+d}", {"ref": ref, "offset": off}, exp
    if "minLength" in schema:
        m = schema["minLength"]
        for n, exp in ((m - 1, "invalid"), (m, "valid"), (m + 1, "valid")):
            yield "BVA", f"minLength={m}:{n - m:+d}", "p" * n, exp
    if "maxLength" in schema:
        m = schema["maxLength"]
        for n, exp in ((m - 1, "valid"), (m, "valid"), (m + 1, "invalid")):
            yield "BVA", f"maxLength={m}:{n - m:+d}", "p" * n, exp
    if "minItems" in schema:
        m = schema["minItems"]
        for n, exp in ((m - 1, "invalid"), (m, "valid"), (m + 1, "valid")):
            yield "BVA", f"minItems={m}:{n - m:+d}", {"array_len": n}, exp


def walk(schema, spec, prefix="", required=()):
    """Flatten object properties (and the first element of arrays of objects) into dotted paths."""
    schema = deref(spec, schema)
    for name, sub in schema.get("properties", {}).items():
        sub = deref(spec, sub)
        path = f"{prefix}{name}"
        yield path, sub, name in required
        if sub.get("type") == "array" and deref(spec, sub["items"]).get("type") == "object":
            item = deref(spec, sub["items"])
            yield from walk(item, spec, f"{path}[0].", item.get("required", ()))


def generate(spec):
    cases = []
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            inputs = []
            body = op.get("requestBody", {}).get("content", {})
            for ctype, media in body.items():
                schema = deref(spec, media["schema"])
                inputs += [("body", ctype, p, s, r) for p, s, r in walk(schema, spec, "", schema.get("required", ()))]
            for prm in op.get("parameters", []):
                prm = deref(spec, prm)
                if prm["in"] != "path":
                    inputs.append(("query", None, prm["name"], prm["schema"], prm.get("required", False)))
            for location, ctype, field, schema, required in inputs:
                form = ctype == "application/x-www-form-urlencoded"
                for n, (tech, cls, value, expected) in enumerate(field_cases(field, schema, required, form)):
                    cases.append({
                        "context": schema.get("x-required-if", {}),
                        "id": f"{op['operationId']}:{field}:{tech}:{n:02d}",
                        "operation": op["operationId"], "method": method.upper(), "path": path,
                        "location": location, "content_type": ctype, "field": field,
                        "technique": tech, "class": cls, "value": value, "expected": expected,
                    })
    return cases


def render_md(cases, digest):
    lines = [f"# Generated test data (spec sha256 {digest[:12]})", "",
             f"{len(cases)} cases. EP = equivalence partitioning, BVA = 3-point boundary value analysis.", "",
             "| Operation | Field | Technique | Class | Value | Expected |", "|---|---|---|---|---|---|"]
    for c in cases:
        v = json.dumps(c["value"])
        v = v if len(v) <= 40 else v[:37] + "..."
        lines.append(f"| {c['operation']} | `{c['field']}` | {c['technique']} | {c['class']} | `{v}` | {c['expected']} |")
    return "\n".join(lines) + "\n"


def main(argv):
    raw = SPEC.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    cases = generate(yaml.safe_load(raw))
    payload = json.dumps({"spec_sha256": digest, "count": len(cases), "cases": cases}, indent=1, sort_keys=True) + "\n"
    md = render_md(cases, digest)
    if "--check" in argv:
        current = (OUT / "cases.json").read_text() if (OUT / "cases.json").exists() else ""
        if current != payload:
            print("generated/cases.json is STALE - run tests/team/datagen/generator.py")
            return 1
        print(f"generated data up to date ({len(cases)} cases, spec {digest[:12]})")
        return 0
    OUT.mkdir(exist_ok=True)
    (OUT / "cases.json").write_text(payload)
    (OUT / "cases.md").write_text(md)
    by = {}
    for c in cases:
        by[c["technique"]] = by.get(c["technique"], 0) + 1
    print(f"wrote {len(cases)} cases ({', '.join(f'{k} {v}' for k, v in sorted(by.items()))}) from spec {digest[:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
