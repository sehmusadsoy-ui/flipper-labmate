#!/bin/bash
# Owner-side only: isolated E11-patched Momentum FAP compile, NEVER flash/install.
set -Eeuo pipefail
APP="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="${LABMATE_E11_BASE:-$HOME/labmate-build/momentum-src}"
WORK="${LABMATE_E11_WORK:-$HOME/labmate-v20-phase3b-build-20261021}"
SDK="$WORK/momentum-src"
PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"

test -d "$BASE/.git" || { echo "NO-GO: existing E11 SDK Git metadata missing"; exit 2; }
test -r "$APP/src/labmate_doctor_screen.c" || { echo "NO-GO: Phase3B UI missing"; exit 2; }
test -r "$APP/src/labmate_doctor_panel.c" || { echo "NO-GO: Phase3B model missing"; exit 2; }
test -r "$APP/src/labmate_doctor.c" || { echo "NO-GO: Signal Doctor core missing"; exit 2; }
test -r "$APP/src/labmate_doctor_frequency_bridge.c" || {
    echo "NO-GO: Phase3D Frequency adapter missing"
    exit 2
}
test -r "$APP/labmate_10px.png" || { echo "NO-GO: app icon missing"; exit 2; }
test "$(git -C "$BASE" rev-parse HEAD)" = "$PIN" || {
    echo "NO-GO: wrong Momentum base"; exit 2;
}
# Firmware export, patched native marker and version are checked before any copy.
python3 - "$BASE" "$APP" <<'PY'
import csv, sys
from pathlib import Path
base, app = map(Path, sys.argv[1:])
with (base / "targets/f7/api_symbols.csv").open(newline="") as f:
    exports = {r[2] for r in csv.reader(f) if len(r)>=3 and r[0]=="Function" and r[1]=="+"}
required = {"furi_hal_resource_lease_try_acquire",
            "furi_hal_resource_lease_release",
            "furi_hal_gpio_try_add_int_callback"}
assert required <= exports, "NO-GO: E11 SDK exports missing"
assert '#define FURI_HAL_RESOURCE_LEASE_API_V1 1' in (base / "targets/f7/furi_hal/furi_hal_resources.h").read_text(), "NO-GO: patched E11 resource HAL missing"
assert 'fap_version="2.0"' in (app / "application.fam").read_text(), "NO-GO: expected v2.0DEV manifest changed"
assert '#define LABMATE_VERSION_TEXT "v2.0DEV"' in (app / "src/labmate_internal.h").read_text(), "NO-GO: unexpected development version"
print("PHASE3B PINNED E11 SOURCE PREFLIGHT: PASS")
PY

# The locally downloaded ZIP must satisfy ALL host suites before E11 staging.
sh "$APP/scripts/test-v20-offline-full-host.sh"
if [ -e "$WORK" ] || [ -L "$WORK" ]; then
    echo "NO-GO: isolated target exists; refusing overwrite: $WORK" >&2
    exit 2
fi
mkdir "$WORK"
cp -a "$BASE" "$SDK"
test "$(git -C "$SDK" rev-parse --show-toplevel)" = "$SDK"
test "$(git -C "$SDK" rev-parse HEAD)" = "$PIN"
# Keep replaced content inside the isolated build workspace for audit.
if [ -e "$SDK/applications_user/labmate" ]; then
    mv "$SDK/applications_user/labmate" "$WORK/previous-labmate"
fi
if [ -e "$SDK/build" ]; then
    mv "$SDK/build" "$WORK/previous-sdk-build"
fi
mkdir -p "$SDK/applications_user/labmate/src"
cp "$APP/application.fam" "$APP/labmate_10px.png" "$SDK/applications_user/labmate/"
cp -a "$APP/src/." "$SDK/applications_user/labmate/src/"
cd "$SDK"
FBT_GIT_SUBMODULE_SHALLOW=1 ./fbt fap_labmate 2>&1 | tee "$WORK/fbt-v20-phase3b.log"
FAP="$SDK/build/f7-firmware-C/.extapps/labmate.fap"
test -s "$FAP"
python3 "$APP/scripts/verify_v19_e11_sdk_fap.py" "$SDK" "$FAP"
sha256sum "$FAP"
echo "V20 CURRENT E11 FAP BUILD AND REVIEW PASS | BUILD ONLY | NO FLASH"
