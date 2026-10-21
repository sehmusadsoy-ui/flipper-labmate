#!/bin/sh
# Phase 2D: source-only freshness contract plus Phase 2C regression.
# No Flipper, firmware, GPIO, IRQ, timer, storage, or device writes.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-phase2d.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
sh "$root/scripts/test-v20-phase2c-host.sh"
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" "$root/src/labmate_snapshot.c" \
    "$root/src/labmate_snapshot_bridge.c" \
    "$root/src/labmate_dashboard_store.c" \
    "$root/src/labmate_evidence_session.c" \
    "$root/tests/test_v20_evidence_freshness.c" -o "$tmp/freshness-$cc"
  "$tmp/freshness-$cc"
done
