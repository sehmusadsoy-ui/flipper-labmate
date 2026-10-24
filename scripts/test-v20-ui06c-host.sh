#!/bin/sh
# Source-only host test. No Flipper, E11 SDK, firmware, GPIO or SD writes.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-ui06c.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
  command -v "$cc" >/dev/null 2>&1 || { echo "Missing host compiler $cc" >&2; exit 2; }
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" "$root/tests/test_v20_ui06c_status.c" -o "$tmp/ui06c-$cc"
  "$tmp/ui06c-$cc"
done
# Keep actual real draw_gpio() tested using the same production status header.
sh "$root/scripts/test-v20-ui05e-host.sh"
printf '%s\n' 'UI-06C HOST PASS: pure status contract and real GPIO renderer gates'
