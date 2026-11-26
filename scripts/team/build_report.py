#!/usr/bin/env python
"""Assemble the final PDF report from docs/*.md (single source of truth) and print it with Chromium.

    python scripts/team/build_report.py --out Project_<Roll1>_<Roll2>_<Section>.pdf \
        --set MEMBER_A_NAME="..." --set ROLL_A=23I-0001 --set MEMBER_B_NAME="..." --set ROLL_B=23I-0002 --set SECTION=A

Chapter order follows the course's required PDF content. CSV tables are rendered as tables,
figures in docs/figures/ are embedded. Requires the Playwright Chromium already used by the E2E tests.
"""
import argparse
import csv
import io
import re
import subprocess
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "docs"
CHAPTERS = [
    ("00_cover.md", None),
    ("01_test_basis.md", "1. System and scope"),
    ("UPSTREAM.md", None),
    ("02_setup.md", None),
    ("03_static_analysis.md", "2. Static analysis"),
    ("04_test_plan.md", "3. Test management"),
    ("05_estimation.md", None),
    ("06_risk_register.md", None),
    ("07_rtm.csv", None),
    ("rtm_coverage", None),
    ("11_unit_testing.md", "4. White-box unit testing"),
    ("12_api_findings.md", "5. API testing and test-data generation"),
    ("13_mutation.md", "6. Mutation testing and CI quality gate"),
    ("14_ci_gate.md", None),
    ("15_use_cases.md", "7. Use cases"),
    ("16_a11y_findings.md", "8. Usability and accessibility"),
    ("17_security.md", "9. Defensive security"),
    ("18_performance.md", "10. Performance and recovery"),
    ("09_rca.md", "11. Defects, root cause analysis and Pareto"),
    ("defects", None),
    ("weekly", "12. Monitoring"),
    ("10_completion_report.md", "13. Test completion report and release decision"),
    ("19_ai_use_record.md", "14. AI-use record"),
    ("tool_versions.md", "Appendix A — tool versions"),
    ("evidence", "Appendix B — evidence links"),
]
FIGS = {"06_risk_register.md": ["risk_matrix.png"],
        "09_rca.md": ["fishbone_F13.png", "fishbone_F3.png", "pareto.png"]}
CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 9.5pt; line-height: 1.38; color: #111; }
h1 { font-size: 17pt; border-bottom: 2px solid #333; padding-bottom: 4px; page-break-before: always; }
h1.first { page-break-before: avoid; }
h2 { font-size: 13pt; margin-top: 16px; } h3 { font-size: 11pt; }
table { border-collapse: collapse; width: 100%; margin: 6px 0 10px; font-size: 8.3pt; page-break-inside: auto; }
th, td { border: 1px solid #999; padding: 3px 5px; vertical-align: top; } th { background: #eee; }
tr { page-break-inside: avoid; }
code { font-size: 8.3pt; background: #f3f3f3; padding: 0 2px; } pre { background: #f6f6f6; padding: 6px; font-size: 8pt; white-space: pre-wrap; }
img { max-width: 100%; margin: 6px 0; } .part { font-size: 10pt; color: #555; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; }
"""


def md(text):
    return markdown.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])


def csv_table(path):
    rows = list(csv.reader(path.open()))
    head = "".join(f"<th>{h}</th>" for h in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{c.replace(';', '; ')}</td>" for c in r) + "</tr>" for r in rows[1:])
    return f"<h2>Traceability matrix</h2><table><tr>{head}</tr>{body}</table>"


def defects_table():
    import json
    raw = subprocess.run(["gh", "issue", "list", "-R", "MTH99910/hpl-ims-sqe", "--state", "all", "--limit", "200",
                          "--json", "number,title,state,labels"], capture_output=True, text=True, check=True).stdout
    rows = []
    for i in sorted(json.loads(raw), key=lambda x: x["number"]):
        labs = {l["name"].split(":")[0]: l["name"].split(":", 1)[1] for l in i["labels"] if ":" in l["name"]}
        rows.append(f"<tr><td>#{i['number']}</td><td>{i['title']}</td><td>{labs.get('severity','')}</td><td>{labs.get('priority','')}</td>"
                    f"<td>{labs.get('status','')} ({i['state'].lower()})</td><td>{labs.get('triage','')}</td><td>{labs.get('cat','')}</td></tr>")
    return ("<h2>Defect log (GitHub Issues)</h2><table><tr><th>#</th><th>Title</th><th>Severity</th><th>Priority</th>"
            "<th>Status</th><th>Triage</th><th>Category</th></tr>" + "".join(rows) + "</table>")


def evidence():
    items = [
        ("Repository", "https://github.com/MTH99910/hpl-ims-sqe"),
        ("CI runs", "https://github.com/MTH99910/hpl-ims-sqe/actions"),
        ("Pull requests (fix PRs, blocked PR, a11y fix, regeneration demo)", "https://github.com/MTH99910/hpl-ims-sqe/pulls?q=is%3Apr"),
        ("Defects", "https://github.com/MTH99910/hpl-ims-sqe/issues"),
    ]
    files = ["reports/playwright/index.html", "reports/coverage/index.html", "reports/api_coverage.md", "reports/rtm_coverage.md",
             "reports/mutation/", "reports/security/", "reports/a11y/before/", "reports/a11y/after/", "reports/screenshots/",
             "tests/team/perf/results/", "docs/figures/"]
    out = "".join(f"<li>{t}: <a href='{u}'>{u}</a></li>" for t, u in items)
    out += "".join(f"<li><code>{f}</code> (in the repository / zip)</li>" for f in files)
    return f"<ul>{out}</ul>"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--set", action="append", default=[])
    a = ap.parse_args()
    values = dict(s.split("=", 1) for s in a.set)
    parts, first, missing = [], True, []
    for name, title in CHAPTERS:
        if title:
            parts.append(f"<p class='part'>{title}</p>")
        if name == "rtm_coverage":
            p = ROOT / "reports/rtm_coverage.md"
            if p.exists():
                parts.append("<h2>Requirements coverage</h2>" + md(p.read_text()))
            continue
        if name == "defects":
            parts.append(defects_table()); continue
        if name == "weekly":
            for w in sorted((D / "weekly").glob("*.md")):
                parts.append(md(w.read_text()))
            continue
        if name == "evidence":
            parts.append(evidence()); continue
        path = D / name
        if not path.exists():
            missing.append(name); continue
        if name.endswith(".csv"):
            parts.append(csv_table(path)); continue
        text = path.read_text()
        for k, v in values.items():
            text = text.replace("{{" + k + "}}", v)
        html = md(text)
        if first:
            html = html.replace("<h1>", "<h1 class='first'>", 1); first = False
        for fig in FIGS.get(name, []):
            html += f"<img src='file://{D / 'figures' / fig}'>"
        parts.append(html)
    left = re.findall(r"\{\{[A-Z_]+\}\}", "".join(parts))
    if left:
        print("WARNING: unfilled placeholders:", sorted(set(left)))
    if missing:
        print("WARNING: missing chapters:", missing)
    html_path = ROOT / "reports/tmp/report.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(parts)}</body></html>")
    js = (f"const {{chromium}}=require('@playwright/test');(async()=>{{const b=await chromium.launch({{channel:'chromium'}});"
          f"const p=await b.newPage();await p.goto('file://{html_path}');await p.pdf({{path:'{Path(a.out).resolve()}',format:'A4',"
          f"printBackground:true,displayHeaderFooter:true,headerTemplate:'<span></span>',footerTemplate:"
          f"'<div style=\"font-size:7pt;width:100%;text-align:center\">SE3002 SQE - HPL IMS Requisition - page <span class=pageNumber></span>/<span class=totalPages></span></div>',"
          f"margin:{{top:\"16mm\",bottom:\"16mm\",left:\"14mm\",right:\"14mm\"}}}});await b.close();}})();")
    subprocess.run(["node", "-e", js], cwd=ROOT / "tests/team/e2e", check=True)
    print("PDF written:", Path(a.out).resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
