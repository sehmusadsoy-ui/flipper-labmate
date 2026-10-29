#!/bin/sh
# E11 UI05: current Logger exact-source pixel regression (not legacy geometry).
# Host-only GCC/Clang + UBSan; no SD, GPIO, firmware, device or FAP writes.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root/src/labmate_ui_screens.c" "$tmp/logger_e11_current.inc" <<'PY'
from pathlib import Path
import sys
source=Path(sys.argv[1]).read_text()
signature="void draw_logger(Canvas* canvas, LabMateApp* app) {"
assert source.count(signature)==1, "unique current Logger renderer required"
start=source.index(signature)
level=0
for index in range(source.index("{",start),len(source)):
    if source[index]=="{": level+=1
    elif source[index]=="}":
        level-=1
        if level==0: break
else:
    raise AssertionError("unclosed Logger renderer")
body=source[start:index+1]
for required in ("labmate_pixel_header(", "labmate_pixel_keys(",
                 "ui_kit_text(", "LoggerPulse", "logger_busy_stopping",
                 "logger_recording", "logger_rows", "pulse_cycles_to_us("):
    assert required in body, ("Logger missing current contract",required)
for unsafe in ("furi_hal_gpio_", "storage_file_write(",
               "furi_hal_resource_lease_", "labmate_capture_start(",
               "logger_start(", "logger_stop("):
    assert unsafe not in body, ("unexpected side effect in draw",unsafe)
Path(sys.argv[2]).write_text(body+"\n")
print("E11 UI05 exact current Logger renderer extraction PASS")
PY
for cc in gcc clang; do
    command -v "$cc" >/dev/null 2>&1 || { echo "missing compiler: $cc" >&2; exit 2; }
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
      -fsanitize=undefined -fno-omit-frame-pointer \
      -I"$root/tests/pixel_stubs" -I"$root/src" -I"$tmp" \
      "$root/tests/test_v20_ui05_pixel.c" -o "$tmp/logger-$cc"
    "$tmp/logger-$cc"
done
echo "E11 UI05 CURRENT LOGGER GCC+CLANG HOST PASS | DEVICE/SD UNTESTED"
