#!/usr/bin/env python
"""Mutation score gate.

score = killed / (killed + survived - equivalent)
Equivalent mutants are the ones analysed and justified in tests/team/mutation/equivalent.json
(matched by file, line and operator, so the list survives re-initialising the session).
Exit 1 if the score is below --min, if any mutant is still pending, or if the baseline was broken
(every mutant 'killed' by a crashing test command - caught by requiring >= 1 survivor-free run
of the unmutated suite via `cosmic-ray baseline` in CI).
"""
import json
import sys
from pathlib import Path

from cosmic_ray.work_db import WorkDB, use_db
from cosmic_ray.work_item import TestOutcome, WorkerOutcome

EQUIV = Path(__file__).with_name("equivalent.json")


def main(argv):
    db_path = argv[0]
    minimum = float(argv[argv.index("--min") + 1]) if "--min" in argv else 80.0
    equivalent = {(e["file"], e["line"], e["operator"]) for e in json.loads(EQUIV.read_text())["equivalent"]}
    killed = survived = equiv = pending = 0
    survivors = []
    with use_db(db_path, WorkDB.Mode.open) as db:
        pending = db.num_work_items - db.num_results
        for item, res in db.completed_work_items:
            if res.worker_outcome == WorkerOutcome.SKIPPED:
                continue
            m = item.mutations[0]
            key = (str(m.module_path), m.start_pos[0], m.operator_name)
            if res.test_outcome == TestOutcome.SURVIVED:
                if key in equivalent:
                    equiv += 1
                else:
                    survived += 1
                    survivors.append(key)
            else:
                killed += 1
    denom = killed + survived
    score = 100.0 * killed / denom if denom else 0.0
    print(f"killed={killed} survived(non-equivalent)={survived} equivalent={equiv} pending={pending}")
    print(f"MUTATION SCORE = {killed}/{denom} = {score:.1f}%  (threshold {minimum}%)")
    for s in survivors:
        print("  surviving:", *s)
    if pending:
        print("FAIL: mutants still pending")
        return 1
    return 0 if score >= minimum else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
