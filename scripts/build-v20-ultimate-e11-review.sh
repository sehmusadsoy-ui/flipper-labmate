#!/bin/bash
# LabMate Ultimate v2.0DEV review — complete HOST + native E11 FAP.
# ONE invocation. No device/firmware/microSD write, no Stable/tag mutation.
set -Eeuo pipefail
APP="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${LABMATE_E11_WORK:-$HOME/labmate-v20-ultimate-review-20261022}"
export LABMATE_E11_WORK="$WORK"

test ! -e "$WORK" && test ! -L "$WORK" || {
    echo "NO-GO: review workspace already exists. Never overwrite." >&2
    exit 2
}
test -f "$APP/src/labmate_dashboard_screen.c"
test -f "$APP/src/labmate_doctor_advice.c"
test -f "$APP/src/labmate_signal_stats.c"
test -f "$APP/tests/test_v20_dashboard_sealed.c"
test -f "$APP/tests/test_v20_doctor_advice.c"
test -f "$APP/tests/test_v20_signal_stats.c"
grep -Fqx '#define LABMATE_VERSION_TEXT "v2.0DEV"' "$APP/src/labmate_internal.h"
grep -Fq 'fap_version="2.0"' "$APP/application.fam"
grep -Fq 'name="LabMate Ultimate"' "$APP/application.fam"
echo "V20 ULTIMATE REQUIRED FEATURES / VERSION: SOURCE PRESENT"

# This old-named script is an established fail-closed implementation:
# full 22 suites + Phase 3A-D + current Ultimate tests; pinned SDK clone,
# E11 native compilation, APPCHK, ELF/API review; zero device installation.
bash "$APP/scripts/build-v20-phase3b-e11-isolated.sh"

SOURCE_FAP="$WORK/momentum-src/build/f7-firmware-C/.extapps/labmate.fap"
test -s "$SOURCE_FAP"
REVIEW_FAP="$WORK/LabMate-Ultimate-v2.0DEV-E11-REVIEW.fap"
test ! -e "$REVIEW_FAP"
cp "$SOURCE_FAP" "$REVIEW_FAP"
cmp "$SOURCE_FAP" "$REVIEW_FAP"

# Document the EXACT binary/source data; the source may be a ZIP without .git.
{
    echo "LabMate Ultimate v2.0DEV — HOST / E11 SDK BUILD REVIEW"
    echo "Source path: $APP"
    echo "E11 workspace: $WORK"
    echo "FAP size: $(stat -c %s "$REVIEW_FAP")"
    echo "FAP SHA256: $(sha256sum "$REVIEW_FAP" | awk '{print $1}')"
    echo "FAP MD5: $(md5sum "$REVIEW_FAP" | awk '{print $1}')"
    echo "Candidate is NOT device/physical QA approved."
    echo "NO DEVICE WRITE / NO FLASH / NO INSTALL"
    printf '\nReviewed source-file Git blob IDs (offline):\n'
    for path in application.fam src/labmate_internal.h \
        src/labmate_dashboard_screen.c src/labmate_doctor_screen.c \
        src/labmate_doctor_advice.c src/labmate_signal_stats.c; do
        git hash-object "$APP/$path" | awk -v path="$path" '{print $1, path}'
    done
} > "$WORK/ULTIMATE_REVIEW_PROVENANCE.txt"
cat "$WORK/ULTIMATE_REVIEW_PROVENANCE.txt"
echo "V20 ULTIMATE E11 HOST+FAP REVIEW: PASS | NO DEVICE WRITES"
