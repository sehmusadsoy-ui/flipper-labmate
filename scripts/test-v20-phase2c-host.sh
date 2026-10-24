#!/bin/sh
# Phase 2C source-matched host gates; never touches Flipper or firmware.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-phase2c.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" "$root/src/labmate_snapshot.c" \
    "$root/src/labmate_snapshot_bridge.c" \
    "$root/tests/test_v20_phase2c_pins.c" -o "$tmp/pins-$cc"
  "$tmp/pins-$cc"
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" "$root/src/labmate_snapshot.c" \
    "$root/src/labmate_snapshot_bridge.c" \
    "$root/src/labmate_dashboard_store.c" \
    "$root/src/labmate_evidence_session.c" \
    "$root/tests/test_v20_evidence_session.c" -o "$tmp/lifecycle-$cc"
  "$tmp/lifecycle-$cc"
done
