#!/usr/bin/env bash
# Exact GitHub-reviewed v2.0 E11 FAP, local WSL compile only (no device writes).
set -Eeuo pipefail
APP="$(cd -- "$(dirname -- "$0")/.." && pwd -P)"
SOURCE=98a3357dade93aacac83c04e01110804b3b3f7b0
SDKPIN=d3f89dfe2ef6b01839201598e9be1590cba80322
SHA=6dbe192ba7d1b0f2b05702c90cf68d791f041f75ed53a6b41135176b6ad4de5b
BASE="$HOME/labmate-build/momentum-src"
OUT="$HOME/.local/share/labmate-e11/labmate.fap"
git -C "$APP" merge-base --is-ancestor "$SOURCE" HEAD || { echo 'NO-GO: source ancestry differs'; exit 2; }
git -C "$APP" diff --quiet "$SOURCE" HEAD -- src application.fam labmate_10px.png || { echo 'NO-GO: compiled production source changed'; exit 2; }
test -z "$(git -C "$APP" status --porcelain)" || { echo 'NO-GO: dirty source checkout'; exit 2; }
test -d "$BASE/.git" && test -f "$BASE/fbt" || { echo "NO-GO: patched E11 SDK absent: $BASE"; exit 2; }
test "$(git -C "$BASE" rev-parse HEAD)" = "$SDKPIN" || { echo 'NO-GO: wrong Momentum base'; exit 2; }
python3 - "$BASE" <<'PY'
import csv,sys
from pathlib import Path
p=Path(sys.argv[1])
with (p/'targets/f7/api_symbols.csv').open() as f:
    symbols={r[2] for r in csv.reader(f) if len(r)>2 and r[0]=='Function' and r[1]=='+'}
assert {'furi_hal_resource_lease_try_acquire',
        'furi_hal_resource_lease_release',
        'furi_hal_gpio_try_add_int_callback'}<=symbols, 'NO-GO: E11 exports absent'
assert '#define FURI_HAL_RESOURCE_LEASE_API_V1 1' in (p/'targets/f7/furi_hal/furi_hal_resources.h').read_text()
print('PINNED E11 SDK PREFLIGHT PASS')
PY
sh "$APP/scripts/test-v20-e11-final-ui-predevice-host.sh"
mkdir -p "$HOME/.cache"
WORK="$(mktemp -d "$HOME/.cache/labmate-e11-build-XXXXXXXX")"
TMP=''
cleanup() {
  if [ -n "$TMP" ]; then rm -f -- "$TMP"; fi
  if [ -d "$WORK" ]; then rm -rf -- "$WORK"; fi
}
trap cleanup EXIT
SDK="$WORK/momentum-src"
cp -a "$BASE" "$SDK"
test "$(git -C "$SDK" rev-parse HEAD)" = "$SDKPIN"
if [ -e "$SDK/applications_user/labmate" ]; then mv "$SDK/applications_user/labmate" "$WORK/previous-labmate"; fi
if [ -e "$SDK/build" ]; then mv "$SDK/build" "$WORK/previous-build"; fi
mkdir -p "$SDK/applications_user/labmate/src"
cp "$APP/application.fam" "$APP/labmate_10px.png" "$SDK/applications_user/labmate/"
cp -a "$APP/src/." "$SDK/applications_user/labmate/src/"
(cd "$SDK" && FBT_GIT_SUBMODULE_SHALLOW=1 ./fbt fap_labmate)
FAP="$SDK/build/f7-firmware-C/.extapps/labmate.fap"
test -s "$FAP"
python3 "$APP/scripts/verify_v19_e11_sdk_fap.py" "$SDK" "$FAP"
ACTUAL="$(sha256sum "$FAP" | cut -d ' ' -f 1)"
BYTES="$(stat -c %s "$FAP")"
if [ "$ACTUAL" != "$SHA" ] || [ "$BYTES" -ne 174192 ]; then
  echo "NO-GO: local FAP differs from CI: $BYTES bytes / $ACTUAL" >&2
  exit 3
fi
mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp "$(dirname "$OUT")/.labmate-verified-XXXXXXXX")"
cp "$FAP" "$TMP"
cmp "$FAP" "$TMP"
mv -f -- "$TMP" "$OUT"
TMP=''
test "$(sha256sum "$OUT" | cut -d ' ' -f 1)" = "$SHA"
echo "EXACT E11 WSL FAP PASS: $BYTES bytes / $SHA"
echo "ONE LOCAL FAP: $OUT"
echo 'NO DEVICE WRITE / NO FIRMWARE FLASH'