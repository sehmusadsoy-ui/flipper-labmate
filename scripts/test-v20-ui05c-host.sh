#!/bin/sh
# UI-05C: source-linked Counter display only; no firmware or storage writes.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-ui05c.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
awk '/^void draw_counter[(]/ {copy=1} copy {print; if($0=="}") exit}' \
  "$root/src/labmate_ui_screens.c" > "$tmp/draw_counter_body.inc"
test -s "$tmp/draw_counter_body.inc"
for cc in gcc clang; do
  command -v "$cc" >/dev/null 2>&1 || { echo "Missing $cc" >&2; exit 2; }
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" -I"$tmp" \
    "$root/tests/test_v20_ui05c_counter.c" \
    "$root/src/labmate_counter_math.c" -o "$tmp/ui05c-$cc"
  "$tmp/ui05c-$cc"
done
