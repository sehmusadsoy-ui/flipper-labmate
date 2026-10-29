#!/bin/sh
# Exact-current COMM E11 renderer integration, no HAL/UART/I2C/1W hardware.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root" "$tmp" <<'PY'
from pathlib import Path
import sys
root,tmp=map(Path,sys.argv[1:])
for name in ("uart","i2c","onewire"):
    s=(root/"src"/("labmate_"+name+"_ui.c")).read_text()
    signature="void draw_"+name+"(Canvas* canvas, LabMateApp* app) {"
    assert s.count(signature)==1,(name,"renderer signature")
    start=s.index(signature);op=s.index("{",start)
    level=0
    for i in range(op,len(s)):
        if s[i]=="{":level+=1
        if s[i]=="}":
            level-=1
            if level==0:break
    else:raise AssertionError("renderer body missing bracket: "+name)
    body=s[start:i+1]
    if name == "i2c":
        assert 'ui_kit_pixel_header(canvas, "I2C explorer"' in body
        assert 'ui_kit_tag(canvas, 123U, 12U, "3.3 V")' in body
        assert 'ui_kit_key_hint(canvas, 4U,' in body
    else:
        assert "labmate_comm_ui_header(" in body and "labmate_comm_ui_keys(" in body
    for bad in ("furi_hal_gpio_","storage_file_write(",
                "furi_hal_resource_lease_", "labmate_capture_start("):
        assert bad not in body,(name,bad)
    (tmp/("comm_"+name+"_e11.inc")).write_text(body+"\n")
print("E11 CURRENT COMM THREE EXACT SOURCE BODIES PASS")
PY
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=undefined -fno-omit-frame-pointer \
    -I"$root/tests/pixel_stubs" -I"$root/src" -I"$tmp" \
    "$root/tests/test_v20_comm_e11_current.c" -o "$tmp/comm-$cc"
  "$tmp/comm-$cc"
done
echo "E11 COMM MIGRATED GCC/CLANG HOST PASS | DEVICE NOT TESTED"
