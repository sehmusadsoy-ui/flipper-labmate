#!/bin/sh
# Compatible reviewed host suites only. NOT obsolete UI/full device acceptance.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
echo "E11 reviewed compatible host regressions"
sh "$root/scripts/test-v20-e11-pixel-ui-host.sh"
sh "$root/scripts/test-v20-ui05b-host.sh"
sh "$root/scripts/test-v20-ui04-host.sh"
sh "$root/scripts/test-v20-ui05-host.sh"
sh "$root/scripts/test-v20-ui05d-host.sh"
sh "$root/scripts/test-v20-ui06-host.sh"
sh "$root/scripts/test-v20-e11-comm-current-host.sh"
sh "$root/scripts/test-v20-ui06c-host.sh"
for phase in 2b 2c 2d 2e 2f 2g 2h 2i 2j 2k; do
    sh "$root/scripts/test-v20-phase$phase-host.sh"
done
for suite in dashboard snapshot signal-stats doctor-advice scope-period-stats; do
    sh "$root/scripts/test-v20-$suite-host.sh"
done
echo "E11 REVIEWED PRE-DEVICE HOST PASS: 8 UI/safety + 10 core + 5 evidence suites"
echo "PENDING: zero unmigrated old UI runners; physical pixel raster, resource contention, SD and device gates."
