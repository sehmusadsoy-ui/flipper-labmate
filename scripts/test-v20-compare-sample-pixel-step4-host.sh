#!/bin/sh
# GCC/Clang source-linked Compare + Samples test, host-only.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root/src/labmate_scope_pair_view.c" <<'PY'
from pathlib import Path
import sys
s=Path(sys.argv[1]).read_text()
for required in ("ui_kit_pixel_header(", "ui_kit_scope_page_dots(",
                 "ui_kit_next_cue(", "labmate_scope_pair_view_draw(",
                 "p->delta.frequency_delta_millihz", "generation_b <= p->generation_a"):
    assert required in s,required
for forbidden in ("furi_hal_gpio_","storage_file_write(",
                  "furi_hal_resource_lease_", "labmate_scope_native_start("):
    assert forbidden not in s,forbidden
assert s.count("ui_kit_pulse_line_dotted(")==1
print("E11 COMPARE/SAMPLE STEP4 PASSIVE SOURCE CONTRACT PASS")
PY
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=undefined -fno-omit-frame-pointer \
    -I"$root/tests/pixel_stubs" -I"$root/src" \
    "$root/tests/test_v20_compare_sample_pixel_step4.c" \
    "$root/src/labmate_scope_pair_view.c" \
    "$root/src/labmate_scope_pair.c" \
    "$root/src/labmate_scope_compare.c" \
    -o "$tmp/compare-$cc"
  "$tmp/compare-$cc"
done
echo "E11 COMPARE/SAMPLE STEP4 GCC+CLANG HOST PASS | DEVICE TEST PENDING"
