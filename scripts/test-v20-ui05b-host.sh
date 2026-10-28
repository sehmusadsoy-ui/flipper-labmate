#!/bin/sh
# E11 UI-05B migrated current pixel review. The old pre-pixel Button and
# Alert fixture is intentionally retained as historical source, NOT invoked.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root/src/labmate_ui_screens.c" "$tmp/draw_alerts_e11_current.inc" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text()
signature="void draw_alerts(Canvas* canvas, LabMateApp* app) {"
assert s.count(signature)==1, "Expected unique current Alerts renderer"
a=s.index(signature);opening=s.index("{",a);depth=0
for i in range(opening,len(s)):
    if s[i]=="{": depth+=1
    if s[i]=="}":
        depth-=1
        if depth==0:break
else: raise AssertionError("unterminated current draw_alerts")
body=s[a:i+1]
for required in ("labmate_pixel_header(", "ui_kit_panel(", "ui_kit_text(",
                 "UiKitKeyDown", "UiKitKeyOk", "threshold.latched"):
    assert required in body,required
for forbidden in ("furi_hal_gpio_", "storage_file_write(",
                  "furi_hal_resource_lease_", "labmate_capture_start("):
    assert forbidden not in body,forbidden
Path(sys.argv[2]).write_text(body+"\n")
print("E11 UI05B ALERTS EXACT BODY EXTRACT PASS")
PY
sh "$root/scripts/test-v20-button-pixel-step2-host.sh"
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=undefined -fno-omit-frame-pointer \
    -I"$root/tests/pixel_stubs" -I"$root/src" -I"$tmp" \
    "$root/tests/test_v20_ui05b_alerts_e11.c" \
    "$root/src/labmate_threshold.c" -o "$tmp/alerts-$cc"
  "$tmp/alerts-$cc"
done
echo "E11 UI05B CURRENT BUTTON + ALERTS GCC/CLANG PASS | DEVICE UNTESTED"
