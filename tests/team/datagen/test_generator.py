"""Self-tests for the test-data generator (tests/team/datagen/generator.py)."""
import json

import yaml

from tests.team.datagen import generator as g


def spec_with(field_schema, required=True):
    return {"paths": {"/x/": {"post": {"operationId": "op", "requestBody": {"content": {
        "application/json": {"schema": {"type": "object", "required": ["f"] if required else [],
                                        "properties": {"f": field_schema}}}}}}}}}


def cases(field_schema, required=True):
    return {c["class"]: c for c in g.generate(spec_with(field_schema, required))}


def test_GEN01_three_point_bva_on_minimum():
    c = cases({"type": "integer", "minimum": 1})
    assert [(c[k]["value"], c[k]["expected"]) for k in ("minimum=1:-1", "minimum=1:+0", "minimum=1:+1")] == \
        [(0, "invalid"), (1, "valid"), (2, "valid")]


def test_GEN02_three_point_bva_on_maximum_and_length():
    c = cases({"type": "integer", "maximum": 50})
    assert [c[f"maximum=50:{o}"]["value"] for o in ("-1", "+0", "+1")] == [49, 50, 51]
    assert c["maximum=50:+1"]["expected"] == "invalid"
    c = cases({"type": "string", "minLength": 10})
    assert [len(c[f"minLength=10:{o}"]["value"]) for o in ("-1", "+0", "+1")] == [9, 10, 11]


def test_GEN03_enum_gives_one_valid_class_per_value_and_one_invalid():
    c = cases({"type": "string", "enum": ["a", "b"]})
    assert c["valid:enum=a"]["expected"] == c["valid:enum=b"]["expected"] == "valid"
    assert c["invalid:outside-enum"]["expected"] == "invalid"


def test_GEN04_data_dependent_maximum_is_symbolic():
    c = cases({"type": "integer", "minimum": 0, "x-maximum-ref": ["line.quantity_requested"]})
    assert c["maximum-ref=line.quantity_requested:+1"]["value"] == {"ref": "line.quantity_requested", "offset": 1}


def test_GEN05_required_field_gets_missing_class_optional_does_not():
    assert "invalid:missing" in cases({"type": "string"}, required=True)
    assert "invalid:missing" not in cases({"type": "string"}, required=False)


def test_GEN06_reference_keys_are_partitioned_without_bva():
    c = cases({"type": "integer", "x-ref-domain": {"own": "valid", "other": "invalid"}})
    assert c["valid:own"]["value"] == {"ref": "own"} and c["invalid:other"]["expected"] == "invalid"
    assert not any(k.startswith("minimum") for k in c)


def test_GEN07_committed_output_matches_the_spec():
    """generated/cases.json must be regenerated whenever openapi.yaml changes (CI also runs --check)."""
    raw = g.SPEC.read_bytes()
    committed = json.loads((g.OUT / "cases.json").read_text())
    assert committed["cases"] == g.generate(yaml.safe_load(raw))
