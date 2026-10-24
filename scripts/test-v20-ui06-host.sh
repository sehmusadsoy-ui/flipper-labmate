#!/bin/sh
# UI-06: real shared Canvas primitives + migrated Frequency/Pulse regression.
# Host compiler only: no E11 SDK, Flipper device, flash, or microSD writes.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-ui06.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
  command -v "$cc" >/dev/null 2>&1 || { echo "Missing $cc" >&2; exit 2; }
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/tests/host_stubs" -I"$root/src" \
    "$root/tests/test_labmate_ui_keylabels.c" \
    "$root/src/labmate_ui_primitives.c" -o "$tmp/ui06-$cc"
  "$tmp/ui06-$cc"
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" "$root/tests/test_v20_ui06_layout.c" -o "$tmp/layout-$cc"
  "$tmp/layout-$cc"
done
# Run the migrated Frequency/Pulse screen bodies with the exact real footer.
sh "$root/scripts/test-v20-ui05d-host.sh"
echo "UI-06 HOST GATE PASS: real shared footer + Frequency/Pulse regressions"
