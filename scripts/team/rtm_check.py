#!/usr/bin/env python
"""Requirements coverage from the traceability matrix (docs/07_rtm.csv) and the JUnit results.

A requirement is COVERED when at least one linked test exists in the results and passed.
(An xfail(strict) test that 'passes' by failing as expected counts as executed but NOT as
evidence that the requirement holds; it is reported in the 'defect' column instead.)

    python scripts/team/rtm_check.py reports/tmp/junit-unit.xml reports/tmp/junit-api.xml reports/tmp/junit-e2e.xml
"""
import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(paths):
    results = {}
    for p in paths:
        for tc in ET.parse(p).getroot().iter("testcase"):
            name = tc.get("name", "")
            skipped = tc.find("skipped")
            failed = tc.find("failure") is not None or tc.find("error") is not None
            xfail = skipped is not None and "xfail" in (skipped.get("type", "") + skipped.get("message", "")).lower()
            # Playwright test.fail(): reported without <failure> but with a property named "fail"
            xfail = xfail or any(pr.get("name") == "fail" for pr in tc.iter("property"))
            results[name] = "fail" if failed else ("xfail" if xfail or skipped is not None else "pass")
    return results


def main(paths):
    res = load(paths)
    rows = list(csv.DictReader((ROOT / "docs/07_rtm.csv").open()))
    out = ["| Req | Linked tests found | Passed | Expected-fail (open defect) | Covered | Defects |", "|---|---|---|---|---|---|"]
    covered = 0
    for r in rows:
        links = [t.strip() for col in ("unit_tests", "api_tests", "e2e_tests") for t in r[col].split(";") if t.strip()]
        found = {name: st for link in links for name, st in res.items() if link in name}
        passed = sum(1 for st in found.values() if st == "pass")
        xf = sum(1 for st in found.values() if st == "xfail")
        ok = passed > 0
        covered += ok
        out.append(f"| {r['req_id']} | {len(found)} | {passed} | {xf} | {'yes' if ok else '**NO**'} | {r['defects'] or '-'} |")
    pct = 100.0 * covered / len(rows)
    out.append("")
    out.append(f"**Requirements coverage: {covered}/{len(rows)} = {pct:.0f} %** (requirement covered = at least one linked test executed and passed)")
    text = "\n".join(out)
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports/rtm_coverage.md").write_text(text + "\n")
    print(text)
    return 0 if covered == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
