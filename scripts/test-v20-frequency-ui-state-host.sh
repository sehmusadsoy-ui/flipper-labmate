#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root/src" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1])
menu=(root/"labmate_input_menu.c").read_text()
session=(root/"labmate_capture_session.c").read_text()
input_code=(root/"labmate_input_measure.c").read_text()
freq=menu[menu.index("case LabMateToolFrequency:"):menu.index("case LabMateToolPulse:")]
assert "labmate_frequency_ui_live(" in freq
assert "app->capture_owner ==" in freq
mode=session[session.index("if(app->screen == LabMateScreenFrequency) {"):]
mode=mode[:mode.index("if(app->screen == LabMateScreenPulse) {")]
assert "labmate_frequency_ui_live(" in mode
pulse=session[session.index("if(app->screen == LabMateScreenPulse) {"):]
pulse=pulse[:pulse.index("labmate_monitor_gpio_release(app, app->gpio_index);\n\n    /* Preserve")]
assert "labmate_pulse_ui_live(" in pulse
assert "app->capture_owner == LabMateCapturePulse" in pulse
assert "labmate_frequency_ui_live(" in input_code
print("V20 FREQUENCY/PULSE MENU, MODE, RETRY: SOURCE LINK PASS")
PY
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer -I"$root/src" \
    "$root/tests/test_v20_frequency_ui_state.c" \
    "$root/src/labmate_frequency_ui_state.c" -o "$tmp/frequi-$cc"
  "$tmp/frequi-$cc"
done
echo "V20 FREQUENCY UI HOST PASS GCC+Clang | NO DEVICE CLAIM"
