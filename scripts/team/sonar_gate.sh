#!/usr/bin/env bash
# Prepare a fresh SonarQube (CI service container): wait until UP, replace the default admin
# password, create an analysis token (.sonar_token) and a custom quality gate on OVERALL code.
#
# Why overall-code conditions: every CI run analyses a brand-new Community container, so there is
# no previous analysis and "new code" conditions would always be empty (the gate could never fail).
#
# Thresholds (docs/14_ci_gate.md) = measured baseline, so any regression fails the gate:
#   coverage < 95 %          measured 95.9 % (100 % of feasible code; the rest is justified dead code)
#   bugs > 1                 upstream has exactly 1 (unreachable `return context`, views.py:404)
#   vulnerabilities > 19     upstream: 9x S3752 (any HTTP method) + 9x S2245 (seed RNG) + 1x S4507 (DEBUG)
#   duplicated lines > 3 %   measured 1.2 %
#   reliability / security rating worse than C (3)
set -euo pipefail
HOST=${SONAR_HOST:-http://localhost:9000}
NEWPASS=${SONAR_NEW_PASSWORD:-Ci-$(date +%s)-Gate!}
for i in $(seq 1 120); do
  status=$(curl -s "$HOST/api/system/status" | python -c 'import sys,json; print(json.load(sys.stdin).get("status",""))' 2>/dev/null || echo "")
  [ "$status" = "UP" ] && break
  sleep 5
done
[ "$status" = "UP" ] || { echo "SonarQube did not start"; exit 1; }
curl -sf -u admin:admin -X POST "$HOST/api/users/change_password" \
     --data-urlencode "login=admin" --data-urlencode "previousPassword=admin" --data-urlencode "password=$NEWPASS"
AUTH="admin:$NEWPASS"
curl -sf -u "$AUTH" -X POST "$HOST/api/user_tokens/generate" -d "name=ci-$(date +%s)" -d "type=GLOBAL_ANALYSIS_TOKEN" \
  | python -c 'import sys,json; open(".sonar_token","w").write(json.load(sys.stdin)["token"])'
curl -sf -u "$AUTH" -X POST "$HOST/api/qualitygates/create" -d "name=SQE gate" > /dev/null
add() { curl -sf -u "$AUTH" -X POST "$HOST/api/qualitygates/create_condition" \
          -d "gateName=SQE gate" -d "metric=$1" -d "op=$2" -d "error=$3" > /dev/null; echo "condition: $1 $2 $3"; }
add coverage LT 95
add bugs GT 1
add vulnerabilities GT 19
add duplicated_lines_density GT 3
add reliability_rating GT 3
add security_rating GT 3
curl -sf -u "$AUTH" -X POST "$HOST/api/qualitygates/set_as_default" -d "name=SQE gate"
echo "SonarQube ready: token in .sonar_token, default gate 'SQE gate'"
