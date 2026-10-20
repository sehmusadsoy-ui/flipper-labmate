#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-ui03.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for name in onewire uart; do
  file="$root/src/labmate_${name}_ui.c"
  awk "/^void draw_${name}[(]/,0" "$file" > "$tmp/labmate_${name}_ui_body.inc"
  test -s "$tmp/labmate_${name}_ui_body.inc"
done
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=undefined -fno-omit-frame-pointer \
    -I"$tmp" "$root/tests/test_v20_ui03_comm.c" -o "$tmp/ui03-$cc"
  "$tmp/ui03-$cc"
done
