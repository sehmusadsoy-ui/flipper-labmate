#!/bin/sh
# E11 UI04: compile the EXACT current Profiles/History/Log Detail renderers.
# Historical pre-pixel geometry fixture remains archived, not an acceptance gate.
# Pure host Canvas; no firmware, Flipper, filesystem, GPIO or FAP writes.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root/src/labmate_ui_screens.c" "$tmp" <<'PY'
from pathlib import Path
import sys
source = Path(sys.argv[1]).read_text()
output = Path(sys.argv[2])
required = {
    "profiles": ("labmate_pixel_header(", "labmate_pixel_keys(", "ui_kit_confirmation(", "profile_busy"),
    "history": ("labmate_pixel_header(", "labmate_pixel_keys(", "ui_kit_confirmation(", "history_delete_confirm"),
    "history_detail": ("labmate_pixel_header(", "ui_kit_key_hint(", "READ ONLY", "history_rows"),
}
for name, tokens in required.items():
    signature = f"void draw_{name}(Canvas* canvas, LabMateApp* app) {{"
    assert source.count(signature) == 1, f"missing or duplicate {name} renderer"
    start = source.index(signature)
    depth = 0
    for index in range(source.index("{", start), len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                break
    else:
        raise AssertionError(f"unterminated draw_{name}")
    body = source[start:index + 1]
    for token in tokens:
        assert token in body, (name, token)
    for unsafe in ("furi_hal_gpio_", "storage_file_write(", "furi_hal_resource_lease_",
                   "labmate_capture_start(", "labmate_generator_start("):
        assert unsafe not in body, (name, unsafe)
    (output / f"draw_{name}_e11.inc").write_text(body + "\n")
print("E11 UI04 three exact-current production renderer bodies PASS")
PY
for cc in gcc clang; do
    command -v "$cc" >/dev/null 2>&1 || { echo "missing compiler: $cc" >&2; exit 2; }
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
      -fsanitize=undefined -fno-omit-frame-pointer \
      -I"$root/tests/pixel_stubs" -I"$root/src" -I"$tmp" \
      "$root/tests/test_v20_ui04_pixel.c" -o "$tmp/ui04-$cc"
    "$tmp/ui04-$cc"
done
echo "E11 UI04 CURRENT RECORDS GCC+CLANG HOST PASS | DEVICE UNTESTED"
