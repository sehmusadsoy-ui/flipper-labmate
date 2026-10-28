#!/bin/sh
# E11 pixel GPIO state/labels test with exact source renderer only.
# Signal trace raster test is separate; no E11 device, SDK or pin writes.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root/src/labmate_ui_screens.c" "$tmp/draw_gpio.inc" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text()
tag="void draw_gpio(Canvas* canvas, LabMateApp* app) {"
assert s.count(tag)==1
i=s.index(tag)
start=s.index("{",i)
depth=0
for k in range(start,len(s)):
    if s[k]=="{":depth+=1
    if s[k]=="}":
        depth-=1
        if depth==0:break
else:raise AssertionError("unbalanced renderer")
Path(sys.argv[2]).write_text(s[i:k+1]+"\n")
print("E11 EXACT GPIO PRODUCTION DRAW BODY EXTRACTION PASS")
PY
for cc in gcc clang; do
    command -v "$cc" >/dev/null 2>&1 || exit 2
    "$cc" -std=c11 -O1 -Wall -Wextra -Werror -pedantic \
      -fsanitize=undefined -fno-omit-frame-pointer \
      -I"$root/tests/pixel_stubs" -I"$root/src" -I"$tmp" \
      "$root/tests/test_v20_ui05e_gpio.c" -o "$tmp/gpio-$cc"
    "$tmp/gpio-$cc"
done
echo "E11 GPIO SCREEN HOST GCC+Clang PASS | TRACE/DEVICE ACCEPTANCE SEPARATE"
