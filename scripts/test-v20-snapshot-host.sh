#!/bin/sh
# Pure standard-C snapshot gate: no device, SDK, SD, clock, GPIO or IRQ.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-snapshot.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
  command -v "$cc" >/dev/null 2>&1 || { echo "Missing $cc" >&2; exit 2; }
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" "$root/src/labmate_snapshot.c" \
    "$root/tests/test_v20_snapshot.c" -o "$tmp/test-$cc"
  "$tmp/test-$cc"
done
