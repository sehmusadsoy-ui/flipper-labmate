#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root/src/labmate_ui_screens.c" "$tmp/menu.inc" <<'PY'
from pathlib import Path
import sys
source=Path(sys.argv[1]).read_text()
start=source.index("void draw_menu(Canvas* canvas, LabMateApp* app) {")
end=source.index("\nvoid draw_gpio(",start)
Path(sys.argv[2]).write_text(source[start:end])
PY
for cc in gcc clang; do
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
      -fsanitize=address,undefined -fno-omit-frame-pointer \
      -I"$root/src" -I"$tmp" \
      "$root/tests/test_v20_ultimate_menu_renderer.c" \
      "$root/src/labmate_navigation.c" -o "$tmp/render-$cc"
    "$tmp/render-$cc"
done
echo "ULTIMATE SOURCE-LINKED MENU RENDER PASS GCC+Clang | DEVICE NOT TESTED"
