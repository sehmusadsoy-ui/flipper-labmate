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
# Previously the script copied the owner's older modified E11 SDK. A
# base-commit check cannot prove parity with GitHub CI's full patch chain.
# Recreate EXACT CI E11 SDK from local immutable Git objects, not the dirty
# working tree. No firmware download, no changes to owner's original SDK.
git clone --local --no-hardlinks --no-checkout "$BASE" "$SDK"
git -C "$SDK" checkout --detach "$SDKPIN"
test "$(git -C "$SDK" rev-parse HEAD)" = "$SDKPIN"
test -z "$(git -C "$SDK" status --porcelain)" || {
  echo 'NO-GO: canonical source clone is not clean' >&2; exit 2;
}
git -C "$APP" diff --quiet "$SOURCE" HEAD -- \
  .github/workflows/build-v20-e11-pixel-ui-native-review.yml || {
    echo 'NO-GO: exact CI source patch recipe was changed' >&2; exit 2;
  }
ln -s "$APP" "$WORK/labmate"
python3 - "$APP" "$WORK" <<'PY'
import sys
from pathlib import Path
app,work=map(Path,sys.argv[1:])
workflow=(app/'.github/workflows/build-v20-e11-pixel-ui-native-review.yml').read_text()
start='      - name: Reapply the previously audited E11 patch chain (SOURCE ONLY)\n'
end='      - name: Stage v2.0 working tree into native FAP source (no install)\n'
assert workflow.count(start)==1 and workflow.count(end)==1,'NO-GO: CI patch markers changed'
block=workflow.split(start,1)[1].split(end,1)[0]
marker='        run: |\n'
assert block.count(marker)==1,'NO-GO: CI Bash patch command block changed'
lines=block.split(marker,1)[1].splitlines()
assert all(not line.strip() or line.startswith('          ') for line in lines),'NO-GO: CI Bash indentation changed'
script='\n'.join(line[10:] if line.strip() else '' for line in lines)+'\n'
assert script.startswith('set -Eeuo pipefail\n'),'NO-GO: CI Bash strict mode missing'
assert script.count('python3 labmate/scripts/patch_momentum_')>=40,'NO-GO: incomplete E11 patch replay'
assert 'E11 SOURCE PATCH PARITY PASS' in script,'NO-GO: native parity marker absent'
assert 'git -C momentum-src diff --check' in script,'NO-GO: patch diff guard absent'
p=work/'exact-e11-ci-patch-replay.sh'
p.write_text(script)
print('EXACT E11 CI PATCH RECIPE REPLAY:',script.count('python3 labmate/scripts/patch_momentum_'),'patch calls')
PY
(cd "$WORK" && GITHUB_WORKSPACE="$WORK" bash exact-e11-ci-patch-replay.sh)
git -C "$SDK" diff --check
mkdir -p "$SDK/applications_user/labmate/src"
cp "$APP/application.fam" "$APP/labmate_10px.png" "$SDK/applications_user/labmate/"
cp "$APP"/src/*.c "$APP"/src/*.h "$SDK/applications_user/labmate/src/"
(cd "$SDK" && FBT_GIT_SUBMODULE_SHALLOW=1 ./fbt fap_labmate)
FAP="$SDK/build/f7-firmware-C/.extapps/labmate.fap"
test -s "$FAP"
python3 "$APP/scripts/verify_v19_e11_sdk_fap.py" "$SDK" "$FAP"
# FBT embeds a GNU debuglink CRC of its separate labmate_d.elf; the
# CRC may depend on absolute WSL build paths. Prove exact identity of
# EVERY OTHER BYTE against the CI artifact, rather than comparing CRC.
# Also check the local CRC against the actual debug ELF before accepting.
# The verifier fails closed for any .text/.rodata/reloc/symbol/ABI change.
python3 "$APP/scripts/verify_v20_e11_debuglink_parity.py" "$FAP" --check-local-debug-elf
ACTUAL="$(sha256sum "$FAP" | cut -d ' ' -f 1)"
BYTES="$(stat -c %s "$FAP")"
mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp "$(dirname "$OUT")/.labmate-verified-XXXXXXXX")"
cp "$FAP" "$TMP"
cmp "$FAP" "$TMP"
mv -f -- "$TMP" "$OUT"
TMP=''
# This full raw hash must match the byte-identical, just-verified local FAP,
# NOT the GitHub CI raw hash: the only allowed variance is the audited
# 4-byte GNU debuglink CRC already verified above.
if [ "$(sha256sum "$OUT" | cut -d ' ' -f 1)" != "$ACTUAL" ] || ! cmp -s -- "$FAP" "$OUT"; then
  echo 'NO-GO: final PC labmate.fap changed after CI content-parity validation' >&2
  exit 3
fi
# Re-check the final canonical PC file against the GitHub CI normalized
# digest, not only its copied raw digest. No writes to device in this step.
python3 "$APP/scripts/verify_v20_e11_debuglink_parity.py" "$OUT"
echo "EXACT E11 WSL FAP CONTENT PARITY PASS: $BYTES bytes / $ACTUAL"
echo "ONE LOCAL FAP: $OUT"
echo 'NO DEVICE WRITE / NO FIRMWARE FLASH'