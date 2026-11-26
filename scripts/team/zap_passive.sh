#!/usr/bin/env bash
# OWASP ZAP *passive* scan while Playwright drives both workflows through the ZAP proxy.
# Passive only: ZAP observes the traffic; no active attack, no spider, no fuzzing.
#   ZAP_HOME=/path/to/ZAP_2.16.1 scripts/team/zap_passive.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
ZAP_HOME=${ZAP_HOME:?set ZAP_HOME to the ZAP install directory}
PORT=${ZAP_PORT:-8090}
OUT=reports/security/zap
mkdir -p "$OUT"
"$ZAP_HOME/zap.sh" -daemon -port "$PORT" -dir "$PWD/reports/tmp/zap-home" \
  -config api.disablekey=true -config "connection.timeoutInSecs=60" > reports/tmp/zap-daemon.log 2>&1 &
ZAP_PID=$!
trap 'kill $ZAP_PID 2>/dev/null' EXIT
for i in $(seq 1 120); do curl -sf "http://127.0.0.1:$PORT/JSON/core/view/version/" > "$OUT/zap-version.json" && break; sleep 2; done
echo "ZAP $(cat "$OUT/zap-version.json")"
# Make sure no active scanning happens
curl -sf "http://127.0.0.1:$PORT/JSON/pscan/action/enableAllScanners/" > /dev/null
# Drive WF1 and WF2 (and the denied access checks) through the proxy
( cd tests/team/e2e && ZAP_PROXY="http://127.0.0.1:$PORT" npx playwright test \
    uc/uc01-hod-authorize.spec.ts uc/uc03-admin-issue-full.spec.ts uc/uc04-admin-issue-partial.spec.ts security \
    --reporter=line ) > "$OUT/playwright-through-zap.log" 2>&1
# Wait until the passive scanner has processed every recorded message
for i in $(seq 1 120); do
  left=$(curl -sf "http://127.0.0.1:$PORT/JSON/pscan/view/recordsToScan/" | python3 -c 'import sys,json; print(json.load(sys.stdin)["recordsToScan"])')
  [ "$left" = "0" ] && break; sleep 2
done
curl -sf "http://127.0.0.1:$PORT/JSON/core/view/numberOfMessages/?baseurl=" > "$OUT/messages.json"
curl -sf "http://127.0.0.1:$PORT/JSON/core/view/alerts/?baseurl=&start=0&count=9999" > "$OUT/zap-alerts.json"
curl -sf "http://127.0.0.1:$PORT/OTHER/core/other/htmlreport/" > "$OUT/zap-report.html"
curl -sf "http://127.0.0.1:$PORT/JSON/core/view/sites/" > "$OUT/sites.json"
echo "messages: $(cat "$OUT/messages.json")"
python3 - "$OUT/zap-alerts.json" <<'PY'
import json, sys, collections
alerts = json.load(open(sys.argv[1]))["alerts"]
c = collections.Counter((a["risk"], a["alert"]) for a in alerts)
for (risk, name), n in sorted(c.items(), key=lambda x: ["High", "Medium", "Low", "Informational"].index(x[0][0])):
    print(f"{risk:13} {n:4}  {name}")
PY
