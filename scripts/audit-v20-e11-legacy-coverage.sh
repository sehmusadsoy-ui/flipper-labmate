#!/bin/sh
# Diagnostic inventory ONLY: executes unmodified legacy host suites and
# distinguishes passing tests from obsolete source/layout expectations.
# Exit 0 to avoid treating known legacy tests as release gates.
# No FAP, SDK, device, GPIO, USB, microSD or firmware writes.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
pass=0
failed=0
for suite in \
  test-v20-ui01-host.sh \
  test-v20-ui02-host.sh \
  test-v20-ui03-host.sh \
  test-v20-ui04-host.sh \
  test-v20-ui05-host.sh \
  test-v20-ui05b-host.sh \
  test-v20-ui05c-host.sh \
  test-v20-ui05d-host.sh \
  test-v20-ui05e-host.sh \
  test-v20-ui06-host.sh \
  test-v20-ui06c-host.sh \
  test-v20-ultimate-root-grid-host.sh \
  test-v20-ultimate-menu-renderer-host.sh \
  test-v20-phase2b-host.sh \
  test-v20-phase2c-host.sh \
  test-v20-phase2d-host.sh \
  test-v20-phase2e-host.sh \
  test-v20-phase2f-host.sh \
  test-v20-phase2g-host.sh \
  test-v20-phase2h-host.sh \
  test-v20-phase2i-host.sh \
  test-v20-phase2j-host.sh \
  test-v20-phase2k-host.sh \
  test-v20-phase3a-doctor-host.sh \
  test-v20-phase3b-doctor-panel-host.sh \
  test-v20-dashboard-host.sh \
  test-v20-snapshot-host.sh \
  test-v20-signal-stats-host.sh \
  test-v20-doctor-advice-host.sh \
  test-v20-scope-period-stats-host.sh
do
    if test ! -f "$root/scripts/$suite"; then
        echo "MISSING $suite"
        failed=$((failed+1))
        continue
    fi
    if timeout 80 sh "$root/scripts/$suite" >"$tmp/output" 2>&1; then
        pass=$((pass+1))
        echo "PASS $suite"
    else
        code=$?
        failed=$((failed+1))
        echo "FAIL $suite exit=$code"
        tail -n 10 "$tmp/output" | sed 's/^/  /'
    fi
done
echo "LEGACY INVENTORY: PASS=$pass FAIL=$failed TOTAL=$((pass+failed))"
echo "DIAGNOSTIC ONLY: failures are not waived; update or retire obsolete"
echo "tests only after checking production semantics and safety."
