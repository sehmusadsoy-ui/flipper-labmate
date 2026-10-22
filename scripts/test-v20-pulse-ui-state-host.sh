#!/bin/sh
# Host: real pure-C resume policy; verify exact app-thread callsite.
# This does NOT attempt USB, IRQ, firmware or device state changes.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root/src/labmate_input_measure.c" <<'PY'
from pathlib import Path
import sys
code=Path(sys.argv[1]).read_text()
start=code.index('if(app->screen == LabMateScreenPulse) {',code.index('event.key == InputKeyOk'))
end=code.index('} else {',start)
resume=code[start:end]
assert 'labmate_pulse_capture_start(app);' in resume
assert 'app->hold = !labmate_pulse_ui_live(' in resume
assert 'app->pulse_irq_active' in resume
assert 'app->capture_owner == LabMateCapturePulse' in resume
assert 'app->capture_blocked' in resume
assert 'app->capture_release_fault' in resume
assert 'app->hold = false;' not in resume
print('V20 PULSE RESUME SOURCE LINK PASS')
PY
for cc in gcc clang; do
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
      -fsanitize=address,undefined -fno-omit-frame-pointer \
      -I"$root/src" "$root/tests/test_v20_pulse_ui_state.c" \
      "$root/src/labmate_pulse_ui_state.c" -o "$tmp/pulseui-$cc"
    "$tmp/pulseui-$cc"
done
echo "V20 PULSE RESUME HOST PASS GCC+Clang | DEVICE NOT TESTED"
