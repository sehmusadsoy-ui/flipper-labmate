#!/usr/bin/env bash
# One-command local, build-only visual UI fix for the already-paired E11
# Momentum source. No USB, COM, upload, install, flash or Flipper app launch.
set -Eeuo pipefail
export LC_ALL=C

root="$(cd -- "$(dirname -- "$0")/.." && pwd -P)"
sdk="$HOME/labmate-build/momentum-src"
if (( $# > 0 )); then sdk="$1"; fi
sdk="$(cd -- "$sdk" && pwd -P)"

die() { printf 'V19 SCOPE BUILD NO-GO: %s\n' "$*" >&2; exit 1; }

[[ -f "$sdk/fbt" && -d "$sdk/.git" ]] || die "expected existing matched E11 Momentum SDK missing"
[[ "$(git -C "$sdk" rev-parse HEAD)" == "d3f89dfe2ef6b01839201598e9be1590cba80322" ]] ||
  die "wrong E11 Momentum firmware SOURCE base; do not compile against an unknown SDK"
[[ "$(git -C "$root" rev-parse --abbrev-ref HEAD)" == "dev/v1.9-logic-scope" ]] ||
  die "wrong LabMate development branch"
git -C "$root" diff --quiet -- src/ application.fam ||
  die "uncommitted app source or application.fam modifications"
git -C "$root" diff --cached --quiet -- src/ application.fam ||
  die "uncommitted staged app source modifications"
for filename in labmate_scope_plot.c labmate_scope_plot.h \
  labmate_scope_display.c labmate_scope_display.h labmate_scope_bridge.c; do
  [[ -s "$root/src/$filename" ]] || die "missing visual module $filename"
done
grep -qF 'labmate_scope_plot_focus(' "$root/src/labmate_scope_bridge.c" ||
  die "unfixed old 64-edge display; fetch latest dev branch first"
grep -qF '#define LABMATE_SCOPE_PLOT_FOCUS_EDGES 13U' "$root/src/labmate_scope_plot.h" ||
  die "incorrect focus configuration"
grep -qFx '#define LABMATE_VERSION_TEXT "v1.9DEV"' "$root/src/labmate_internal.h" ||
  die "wrong version"
grep -qFx '    fap_version="1.9",' "$root/application.fam" ||
  die "wrong FAP version"

# Offline host tests FIRST, before changing the SDK's local app source files.
tmp="$(mktemp -d)"
trap 'rm -rf -- "$tmp"' EXIT
cc -std=c11 -Wall -Wextra -Werror -Wpedantic -O2 -I"$root/src" \
  "$root/src/labmate_scope_plot.c" "$root/tests/test_labmate_scope_plot.c" \
  -o "$tmp/plot"
"$tmp/plot"
cc -std=c11 -Wall -Wextra -Werror -Wpedantic -O2 -I"$root/src" \
  "$root/src/labmate_scope_plot.c" "$root/tests/test_labmate_scope_focus.c" \
  -o "$tmp/focus"
"$tmp/focus"
cc -std=c11 -Wall -Wextra -Werror -Wpedantic -O2 \
  -I"$root/tests/mock_v19" -I"$root/src" \
  "$root/src/labmate_scope_plot.c" "$root/src/labmate_scope_display.c" \
  "$root/tests/test_labmate_scope_display.c" \
  -o "$tmp/display"
"$tmp/display"
printf 'V19 SCOPE UI THREE STRICT HOST CHECKS PASS\n'

# Exactly the preexisting FAP-only SDK source staging used by verified E11
# local review builds. Do NOT build an updater or flash firmware.
target="$sdk/applications_user/labmate"
mkdir -p "$target/src"
cp -- "$root/application.fam" "$root/labmate_10px.png" "$target/"
cp -- "$root"/src/*.c "$root"/src/*.h "$target/src/"
cmp -s "$root/src/labmate_scope_plot.c" "$target/src/labmate_scope_plot.c" ||
  die "SDK plot source diverged during copy"
cmp -s "$root/src/labmate_scope_display.c" "$target/src/labmate_scope_display.c" ||
  die "SDK display source diverged during copy"
cmp -s "$root/src/labmate_scope_bridge.c" "$target/src/labmate_scope_bridge.c" ||
  die "SDK app bridge source diverged during copy"

(cd -- "$sdk" && ./fbt fap_labmate)
fap="$sdk/build/f7-firmware-C/.extapps/labmate.fap"
[[ -s "$fap" ]] || die "no linked FAP built"
python3 "$root/scripts/verify_v19_e11_sdk_fap.py" "$sdk" "$fap" ||
  die "SDK/ELF exported FAP requirements NOT matched"
printf '\nSCOPE_UI_FAP_BUILD_ONLY_PASS\nSOURCE_COMMIT: %s\nFAP_PATH: %s\n' \
  "$(git -C "$root" rev-parse HEAD)" "$fap"
sha256sum "$fap"
printf 'DEVICE_WRITES: ZERO | DEVICE_LAUNCH: NO | FIRMWARE_FLASH: NO\n'
printf 'STOP: preserve current working v1.9. New FAP requires separate backup-safe deployment step.\n'
