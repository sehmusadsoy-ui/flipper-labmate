#!/bin/sh
# Read-only host-only bridge; requires genuine producer evidence before any VALID.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-phase2b.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" "$root/src/labmate_snapshot.c" \
    "$root/src/labmate_snapshot_bridge.c" "$root/src/labmate_dashboard_store.c" \
    "$root/tests/test_v20_snapshot_bridge.c" -o "$tmp/test-$cc"
  "$tmp/test-$cc"
done
