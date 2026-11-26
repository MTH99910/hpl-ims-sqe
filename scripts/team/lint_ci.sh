#!/usr/bin/env bash
# Fail if any workflow contains a construct that would let a failing gate pass:
#   continue-on-error, "|| true", "set +e"   (comment lines are ignored)
set -euo pipefail
PATTERN='continue-on-error|\|\|[[:space:]]*true|set[[:space:]]+\+e'
hits=$(grep -RnE "$PATTERN" .github/workflows/ | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#' || :)
if [ -n "$hits" ]; then
  echo "$hits"
  echo "::error::escape hatch found in a workflow file"
  exit 1
fi
echo "no escape hatches in .github/workflows/"
