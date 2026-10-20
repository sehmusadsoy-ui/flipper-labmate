#!/bin/sh
# Test-only: no firmware/Flipper/SD writes. Extract the real Logger body.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-ui05.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
awk '/^void draw_logger\(/ {copy=1} copy {print; if($0=="}") exit}' \
  "$root/src/labmate_ui_screens.c" > "$tmp/logger_body.inc"
test -s "$tmp/logger_body.inc"
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$tmp" "$root/tests/test_v20_ui05_logger.c" -o "$tmp/ui05-$cc"
  "$tmp/ui05-$cc"
done
