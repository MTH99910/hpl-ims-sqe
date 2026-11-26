#!/usr/bin/env bash
# Runs the 4 comparable k6 runs (1 VU x2, 5 VUs x2) on the same build, machine and starting data.
set -euo pipefail
cd "$(dirname "$0")/../../.."
K6=${K6:-k6}
OUT=tests/team/perf/results
mkdir -p "$OUT"
{ echo "# Environment"; date -Iseconds; uname -a; echo "commit: $(git rev-parse HEAD)";
  lscpu | grep -E 'Model name|^CPU\(s\)'; free -h | head -2; .venv/bin/python --version;
  .venv/bin/python -c 'import django; print("Django", django.get_version())'; .venv/bin/gunicorn --version; $K6 version; } > "$OUT/env.txt"
for vus in 1 5; do
  for run in 1 2; do
    cp tests/team/data/golden.sqlite3 tests/team/data/perf.sqlite3          # identical starting data
    TEAM_DB=$PWD/tests/team/data/perf.sqlite3 MODE=perf PORT=8020 scripts/team/run_server.sh > "$OUT/server-${vus}vu-run${run}.log" 2>&1 &
    SERVER=$!
    for i in $(seq 1 40); do curl -sf -o /dev/null http://127.0.0.1:8020/login/ && break; sleep 0.5; done
    PK=$(TEAM_DB=$PWD/tests/team/data/perf.sqlite3 DJANGO_SETTINGS_MODULE=tests.team.settings_test .venv/bin/python -c \
         "import django; django.setup(); from requisition.models import Requisition as R; print(R.objects.get(purpose='Pens for new IT interns batch').pk)")
    set +e
    $K6 run -q -e BASE_URL=http://127.0.0.1:8020 -e VUS=$vus -e PK=$PK \
        --summary-export "$OUT/summary-${vus}vu-run${run}.json" --out json="$OUT/raw-${vus}vu-run${run}.json" \
        tests/team/perf/approval_screen.js 2>&1 | tee "$OUT/console-${vus}vu-run${run}.txt"
    echo "k6 exit code: ${PIPESTATUS[0]}" >> "$OUT/console-${vus}vu-run${run}.txt"
    set -e
    kill $SERVER; wait $SERVER 2>/dev/null || true
    gzip -f "$OUT/raw-${vus}vu-run${run}.json"
  done
done
