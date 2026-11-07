#!/bin/sh
# Canonical CURRENT supported E11 software acceptance; no install/device writes.
# Historical omissions are declared, not silently counted as passing tests.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python3 "$root/tests/test_v20_coverage_inventory.py"
sh "$root/scripts/test-v20-e11-final-ui-predevice-host.sh"
sh "$root/scripts/test-v20-persistence-closure-host.sh"
python3 "$root/scripts/audit-v20-e11-software-contract.py"
sh "$root/scripts/test-v20-frequency-ui-state-host.sh"
sh "$root/scripts/test-v20-pulse-ui-state-host.sh"
sh "$root/scripts/test-v20-ultimate-menu-renderer-host.sh"
sh "$root/scripts/test-v20-scope-diagnostics-host.sh"
echo 'CURRENT SUPPORTED E11 SOFTWARE HOST ACCEPTANCE PASS (GCC+Clang)'
echo 'RETIRED: GPIO LevelWitness; Scope MAD; former grid UI. See coverage ledger.'
echo 'OPEN OUTSIDE HOST: runtime loader/OOM, real SD/fault recovery, contention, physical/electrical validation.'
