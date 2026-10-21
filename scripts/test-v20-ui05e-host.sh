#!/bin/sh
# Host-only GPIO geometry matrix; extracts the actual production draw_gpio body.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-ui05e.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
awk '/^void draw_gpio[(]/ {copy=1} copy {print; if($0=="}") exit}' \
  "$root/src/labmate_ui_screens.c" > "$tmp/draw_gpio.inc"
test -s "$tmp/draw_gpio.inc"
for cc in gcc clang; do
  command -v "$cc" >/dev/null 2>&1 || { echo "missing compiler: $cc" >&2; exit 2; }
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$tmp" "$root/tests/test_v20_ui05e_gpio.c" -o "$tmp/test-$cc"
  "$tmp/test-$cc"
done
