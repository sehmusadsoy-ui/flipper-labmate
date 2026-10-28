#!/bin/sh
# Historical filename, NEW carousel/three-row list contract. Host only.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
# Check the production draw_menu() body, not a disconnected illustration.
python3 - "$root/src/labmate_ui_screens.c" <<'PY'
from pathlib import Path
import sys
source=Path(sys.argv[1]).read_text()
begin=source.index("void draw_menu(Canvas* canvas, LabMateApp* app) {")
end=source.index("\nvoid draw_gpio(",begin)
body=source[begin:end]
for text in (
  "ui_kit_brand(canvas)",
  "ui_kit_carousel_card(canvas, 11, 18, 18, 18, false)",
  "ui_kit_carousel_card(canvas, 48, 10, 32, 27, true)",
  "ui_kit_carousel_card(canvas, 99, 18, 18, 18, false)",
  "ui_kit_icon(canvas, labmate_menu_icon_for_group(prev), 14, 21, 12",
  "canvas, labmate_menu_icon_for_group(selected),",
  "ui_kit_center_text(canvas, 46,",
  "ui_kit_center_text(canvas, 55,",
  "labmate_nav_first_visible(selected, count, 3U)",
  "ui_kit_pill(canvas, 2, pill_y, 124, 14)",
  "ui_kit_list_row(canvas,",
):
    assert text in body, "root contract missing: "+text
for banned in ("labmate_menu_tile_", "ui_footer_triple(", "ui_draw_header("):
    assert banned not in body, "obsolete root rendering: "+banned
print("E11 CURRENT DRAW_MENU SOURCE CONTRACT PASS")
PY
for cc in gcc clang; do
    command -v "$cc" >/dev/null 2>&1 || { echo "MISSING $cc" >&2; exit 2; }
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
        -fsanitize=undefined -fno-omit-frame-pointer \
        -I"$root/src" "$root/tests/test_v20_ultimate_root_grid.c" \
        "$root/src/labmate_navigation.c" -o "$tmp/menu-$cc"
    "$tmp/menu-$cc"
done
echo "E11 ROOT MENU CONTRACT GCC+Clang PASS | FAP/DEVICE NOT TESTED"
