#!/bin/sh
# Read-only producer-publication acceptance gate; no hardware or release actions.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-phase2e.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
  command -v "$cc" >/dev/null 2>&1 || { echo "missing compiler: $cc" >&2; exit 2; }
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" "$root/src/labmate_publication_gate.c" \
    "$root/src/labmate_snapshot.c" "$root/src/labmate_snapshot_bridge.c" \
    "$root/tests/test_v20_publication_gate.c" -o "$tmp/producer-$cc"
  "$tmp/producer-$cc"
done
