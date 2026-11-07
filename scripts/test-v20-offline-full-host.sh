#!/bin/sh
# Compatibility entry point, CURRENT supported E11 software scope only.
# Original entry point and assertion mapping are retained in tests/historical
# and V20_E11_CURRENT_ACCEPTANCE_COVERAGE.md; no retired feature is fabricated.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec sh "$root/scripts/test-v20-e11-current-software-host.sh"
