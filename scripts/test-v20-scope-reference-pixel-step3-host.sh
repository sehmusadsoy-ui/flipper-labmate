#!/bin/sh
# Source-linked E11 Step3 Canvas host gates. No device, GPIO or firmware.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1])
for file in ("src/labmate_scope_display.c","src/labmate_scope_reference_view.c"):
    text=(root/file).read_text()
    for unsafe in ("furi_hal_gpio_","storage_file_write(",
                   "furi_hal_resource_lease_", "labmate_scope_native_start("):
        assert unsafe not in text,(file,unsafe)
scope=(root/"src/labmate_scope_display.c").read_text()
ref=(root/"src/labmate_scope_reference_view.c").read_text()
for term in ("ui_kit_pixel_header(", "ui_kit_scope_page_dots(", "ui_kit_pulse_line_dotted(",
             "labmate_scope_display_draw(", "scope_complete("):
    assert term in scope,term
for term in ("ui_kit_state_chip_compact(", "ui_kit_scope_page_dots(",
             "labmate_scope_tolerance_evaluate(", "LabMateScopeVerdictNoSignal"):
    assert term in ref,term
print("SCOPE+REFERENCE STEP3 PASSIVE SOURCE CONTRACT PASS")
PY
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=undefined -fno-omit-frame-pointer \
    -I"$root/tests/pixel_stubs" -I"$root/src" \
    "$root/tests/test_v20_scope_reference_pixel_step3.c" \
    "$root/src/labmate_scope_display.c" \
    "$root/src/labmate_scope_reference_view.c" \
    "$root/src/labmate_scope_plot.c" \
    "$root/src/labmate_scope_tolerance.c" \
    "$root/src/labmate_scope_compare.c" \
    -o "$tmp/scope-$cc"
  "$tmp/scope-$cc"
done
echo "SCOPE+REFERENCE STEP3 GCC+CLANG HOST PASS | PHYSICAL ACCEPTANCE PENDING"
