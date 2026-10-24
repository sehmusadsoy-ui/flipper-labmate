#!/bin/sh
# UI-05B Button and Threshold renderer safety, host only.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-ui05b.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM

for name in button alerts; do
  awk -v name="$name" '
    $0 ~ ("^void draw_" name "[(]") {copy=1}
    copy {print; if($0=="}") exit}
  ' "$root/src/labmate_ui_screens.c" > "$tmp/draw_${name}_body.inc"
  test -s "$tmp/draw_${name}_body.inc"
done

for cc in gcc clang; do
  command -v "$cc" >/dev/null 2>&1 || {
    echo "Missing host compiler: $cc" >&2; exit 2;
  }
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -Isrc -I"$tmp" \
    "$root/tests/test_v20_ui05b_button_threshold.c" \
    "$root/src/labmate_threshold.c" -o "$tmp/ui05b-$cc"
  "$tmp/ui05b-$cc"
done
