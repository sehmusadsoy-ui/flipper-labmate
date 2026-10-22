#!/bin/sh
# Offline host entry point for the COMPLETE local v2.0 checkout.
# Run source-linked Phase 2L first; only then execute Phase 3A Doctor.
# No GitHub Actions, FAP installation, USB, GPIO or microSD operations.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test -s "$root/scripts/test-v20-phase2l-integration-host.sh" || {
    echo 'V20 OFFLINE NO-GO: missing Phase 2L orchestrator' >&2
    exit 2
}
test -s "$root/scripts/test-v20-phase3a-doctor-host.sh" || {
    echo 'V20 OFFLINE NO-GO: missing Phase 3A runner' >&2
    exit 2
}
sh "$root/scripts/test-v20-phase2l-integration-host.sh" || {
    echo 'V20 OFFLINE FAIL: Phase 2L 22-suite integration' >&2
    exit 1
}
sh "$root/scripts/test-v20-phase3a-doctor-host.sh" || {
    echo 'V20 OFFLINE FAIL: Phase 3A Signal Doctor' >&2
    exit 1
}
test -s "$root/scripts/test-v20-phase3b-doctor-panel-host.sh" || {
    echo 'V20 OFFLINE NO-GO: Phase 3B missing' >&2
    exit 2
}
sh "$root/scripts/test-v20-phase3b-doctor-panel-host.sh" || {
    echo 'V20 OFFLINE FAIL: Phase 3B Doctor panel' >&2
    exit 1
}
test -s "$root/scripts/test-v20-phase3c-pulse-host.sh" || {
    echo 'V20 OFFLINE NO-GO: Phase 3C missing' >&2
    exit 2
}
sh "$root/scripts/test-v20-phase3c-pulse-host.sh" || {
    echo 'V20 OFFLINE FAIL: Phase 3C Pulse STOP policy' >&2
    exit 1
}
test -s "$root/scripts/test-v20-phase3d-frequency-host.sh" || {
    echo 'V20 OFFLINE NO-GO: Phase 3D Frequency policy missing' >&2
    exit 2
}
sh "$root/scripts/test-v20-phase3d-frequency-host.sh" || {
    echo 'V20 OFFLINE FAIL: Phase 3D Frequency policy' >&2
    exit 1
}
test -s "$root/scripts/test-v20-phase3d-frequency-wiring-host.sh" || {
    echo 'V20 OFFLINE NO-GO: Phase3D Frequency wiring audit missing' >&2
    exit 2
}
sh "$root/scripts/test-v20-phase3d-frequency-wiring-host.sh" || {
    echo 'V20 OFFLINE FAIL: Phase3D Frequency native wiring audit' >&2
    exit 1
}
for phase in ultimate-root-grid ultimate-menu-renderer level-witness signal-stats doctor-advice scope-period-stats scope-diagnostics dashboard; do
    test -s "$root/scripts/test-v20-$phase-host.sh" || {
        echo "V20 OFFLINE NO-GO: missing v2.0 Ultimate $phase suite" >&2
        exit 2
    }
    sh "$root/scripts/test-v20-$phase-host.sh" || {
        echo "V20 OFFLINE FAIL: v2.0 Ultimate $phase" >&2
        exit 1
    }
done
echo 'V20 OFFLINE HOST PASS: Phase 2L + Phase 3A/3B/3C/3D + Dashboard + Stats + Doctor Advice (NOT SDK/FAP OR DEVICE)'
