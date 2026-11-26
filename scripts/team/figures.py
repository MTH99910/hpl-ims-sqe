#!/usr/bin/env python
"""Generate the report figures from the project data (no hand-drawn numbers):
  docs/figures/risk_matrix.png   - 5x5 likelihood x impact matrix (docs/06_risk_register.md values)
  docs/figures/fishbone_F13.png, fishbone_F3.png - Ishikawa diagrams (docs/09_rca.md causes)
  docs/figures/pareto.png        - defects per category from GitHub Issues (gh CLI)
"""
import json
import subprocess
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIG = ROOT / "docs/figures"
FIG.mkdir(parents=True, exist_ok=True)

RISKS = {"PR-1": (5, 5), "PR-2": (4, 5), "PR-3": (4, 5), "PR-4": (4, 4), "PR-5": (3, 5), "PR-6": (4, 3),
         "PR-7": (3, 3), "PR-8": (3, 3), "PR-9": (2, 3), "PR-10": (2, 2),
         "PJ-1": (5, 4), "PJ-2": (4, 3), "PJ-3": (2, 4), "PJ-4": (5, 5)}


def risk_matrix():
    fig, ax = plt.subplots(figsize=(7, 6))
    for l in range(1, 6):
        for i in range(1, 6):
            s = l * i
            color = "#e57373" if s >= 15 else ("#ffd54f" if s >= 8 else "#81c784")
            ax.add_patch(plt.Rectangle((i - 0.5, l - 0.5), 1, 1, color=color, ec="white"))
            ax.text(i + 0.38, l - 0.38, str(s), fontsize=7, ha="right", va="bottom", color="#555")
    cells = {}
    for rid, (l, i) in RISKS.items():
        cells.setdefault((l, i), []).append(rid)
    for (l, i), ids in cells.items():
        ax.text(i, l, "\n".join(ids), ha="center", va="center", fontsize=8, weight="bold")
    ax.set_xlim(0.5, 5.5), ax.set_ylim(0.5, 5.5)
    ax.set_xticks(range(1, 6)), ax.set_yticks(range(1, 6))
    ax.set_xlabel("Impact"), ax.set_ylabel("Likelihood")
    ax.set_title("Risk matrix (score = L x I; red >= 15, amber 8-14, green <= 7)")
    fig.tight_layout()
    fig.savefig(FIG / "risk_matrix.png", dpi=150)


def fishbone(name, effect, causes):
    fig, ax = plt.subplots(figsize=(16, 6))
    ax.axis("off")
    ax.annotate("", xy=(14.4, 0), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", lw=2.5))
    ax.text(14.5, 0, effect, va="center", fontsize=10, weight="bold", wrap=True,
            bbox=dict(boxstyle="round", fc="#fff3e0", ec="#e65100"))
    cats = list(causes)
    for k, cat in enumerate(cats):
        x = 2.5 + (k // 2) * 4.6
        up = k % 2 == 0
        y = 2.2 if up else -2.2
        ax.plot([x, x + 1.2], [y, 0], color="#37474f", lw=1.5)
        ax.text(x - 0.1, y + (0.25 if up else -0.35), cat, fontsize=9, weight="bold", ha="left")
        for j, c in enumerate(causes[cat]):
            yy = y * (1 - (j + 1) * 0.28)
            xx = x + 1.2 * (1 - yy / y) if y else x
            ax.plot([xx - 1.1, xx], [yy, yy], color="#90a4ae", lw=0.8)
            ax.text(xx - 1.12, yy, c, fontsize=7, ha="right", va="center")
    ax.set_xlim(-1.5, 17.5), ax.set_ylim(-3, 3)
    fig.tight_layout()
    fig.savefig(FIG / f"fishbone_{name}.png", dpi=150)


def pareto():
    raw = subprocess.run(["gh", "issue", "list", "-R", "MTH99910/hpl-ims-sqe", "--state", "all", "--limit", "200",
                          "--json", "number,labels"], capture_output=True, text=True, check=True).stdout
    counts = Counter()
    for issue in json.loads(raw):
        for lab in issue["labels"]:
            if lab["name"].startswith("cat:"):
                counts[lab["name"][4:]] += 1
    items = counts.most_common()
    total = sum(v for _, v in items)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar([k for k, _ in items], [v for _, v in items], color="#5c6bc0")
    ax2 = ax.twinx()
    cum, acc = [], 0
    for _, v in items:
        acc += v
        cum.append(100 * acc / total)
    ax2.plot([k for k, _ in items], cum, color="#e53935", marker="o")
    ax2.axhline(80, color="#e53935", ls="--", lw=0.8)
    ax2.set_ylim(0, 105), ax2.set_ylabel("cumulative %")
    ax.set_ylabel("defects"), ax.set_title(f"Pareto of {total} logged defects by category")
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    fig.tight_layout()
    fig.savefig(FIG / "pareto.png", dpi=150)
    (FIG / "pareto.json").write_text(json.dumps({"total": total, "categories": items, "cumulative_pct": cum}, indent=1))


if __name__ == "__main__":
    risk_matrix()
    fishbone("F13", "F13: issued but\nstock not deducted", {
        "Requirements/Docs": ["no criterion for 'accept defaults'", "README: 'automatically deducts'"],
        "Design": ["stock posting depends on what\nthe formset chose to save", "message not derived from outcome"],
        "Code": ["self.initial = requested", "formset.save() skips unchanged"],
        "Process/Review": ["2-commit history, no review", "no definition of done"],
        "Tools/Tests": ["no automated tests upstream", "manual tests edit the number"],
        "Environment": ["(no contributing factor)"],
    })
    fishbone("F3", "F3: any logged-in\nuser can issue", {
        "Requirements/Docs": ["roles only in prose", "no access matrix"],
        "Design": ["authorisation in templates", "no single policy point"],
        "Code": ["AdminRequiredMixin unused", "admin branch in HOD view (F4)"],
        "Process/Review": ["no security review"],
        "Tools/Tests": ["no access tests", "static analysis cannot know roles"],
        "Environment": ["DEBUG on - 403/404 never exercised"],
    })
    pareto()
    print("figures written to", FIG)
