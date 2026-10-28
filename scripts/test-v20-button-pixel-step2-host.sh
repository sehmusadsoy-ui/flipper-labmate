#!/bin/sh
# Extract exact production Button renderer; compile it with strict host Canvas.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root/src/labmate_ui_screens.c" "$tmp/draw_button_exact.inc" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text()
anchor="void draw_button(Canvas* canvas, LabMateApp* app) {"
assert s.count(anchor)==1
start=s.index(anchor)
op=s.index("{",start)
level=0
for i in range(op,len(s)):
    if s[i]=="{":level+=1
    if s[i]=="}":
        level-=1
        if not level:break
else:raise AssertionError("unbalanced draw_button")
body=s[start:i+1]
for forbidden in ("furi_hal_gpio_", "furi_hal_resource_lease_",
                  "storage_file_write(", "labmate_capture_start(",
                  "labmate_button_capture_start(", "labmate_button_capture_stop("):
    assert forbidden not in body,forbidden
for needed in ("ui_kit_pixel_header(", "ui_kit_stat_row(", "UiKitKeyDown",
               "button_session_started", "button_stats.pending",
               "capture_release_fault", "capture_blocked", "button_stats.releases"):
    assert needed in body,needed
Path(sys.argv[2]).write_text(body+"\n")
print("BUTTON STEP2 EXACT PRODUCTION DRAW CONTRACT PASS")
PY
for cc in gcc clang; do
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
        -fsanitize=undefined -fno-omit-frame-pointer \
        -I"$root/tests/pixel_stubs" -I"$root/src" -I"$tmp" \
        "$root/tests/test_v20_button_pixel_step2.c" -o "$tmp/button-$cc"
    "$tmp/button-$cc"
done
echo "BUTTON STEP2 E11 GCC+CLANG HOST PASS | NATIVE/PHYSICAL GATE SEPARATE"
