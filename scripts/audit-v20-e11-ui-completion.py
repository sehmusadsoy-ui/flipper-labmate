#!/usr/bin/env python3
"""Fail-closed source review for the E11 UI-only pixel branch.

No device, firmware, SDK, USB, storage or GPIO operations. Native E11
compile and on-device visual acceptance are separate release gates.
"""
import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent.parent
base = "f3ef6aac9c31526eb21bcce6672cdfc8ae3fecf1"

def git(*args):
    return subprocess.check_output(["git", "-C", str(root), *args])

def read(path):
    return (root / path).read_text(encoding="utf-8")

def check(test, reason):
    if not test:
        raise AssertionError(reason)

def function(text, name):
    match = re.search(r"(?m)^(?:static\s+)?void " + re.escape(name) + r"\(", text)
    check(match is not None, name + " not found")
    begin = text.index("{", match.end())
    depth = 0
    for index in range(begin, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start():index+1]
    raise AssertionError(name + " unmatched braces")

# Source identity: compare the production files with the Counter Step 3
# ancestor, never with floating main / Stable.
git("merge-base", "--is-ancestor", base, "HEAD")
inputs = (
    "src/labmate_input.c",
    "src/labmate_input_menu.c",
    "src/labmate_input_measure.c",
    "src/labmate_capture_session.c",
    "src/labmate_capture_core.c",
    "src/labmate_event_counter.c",
    "src/labmate_frequency_capture.c",
    "src/labmate_frequency_tim2.c",
    "src/labmate_pulse_capture.c",
    "src/labmate_scope_native.c",
    "src/labmate_logger_storage.c",
)
changed = git("diff", "--name-only", base, "HEAD", "--", *inputs).decode().strip()
check(not changed, "Native/input source changed unexpectedly: " + changed)
original = git("show", base + ":src/labmate_ui_screens.c").decode()
current = read("src/labmate_ui_screens.c")
for name in (
    "draw_menu", "draw_gpio", "draw_counter", "draw_frequency",
    "draw_pulse", "draw_pulse_stats", "draw_generator",
):
    check(function(original, name) == function(current, name),
          "Approved renderer changed: " + name)

migrated = (
    "draw_alerts", "draw_button", "draw_logger", "draw_history",
    "draw_history_detail", "draw_profiles",
)
for name in migrated:
    body = function(current, name)
    check("labmate_pixel_header(canvas," in body,
          "Pixel header absent in " + name)
    for forbidden in (
        "ui_draw_header(", "ui_badge(", "ui_footer_pair(",
        "furi_hal_gpio_", "furi_hal_resource_lease_",
        "storage_file_write(", "labmate_capture_stop_all(",
    ):
        check(forbidden not in body, name + ": forbidden " + forbidden)

for filename in ("labmate_uart_ui.c", "labmate_i2c_ui.c",
                 "labmate_onewire_ui.c"):
    body = read("src/" + filename)
    check('#include "labmate_comm_ui.h"' in body,
          filename + " missing comm pixel shim")
    check("labmate_comm_ui_header(" in body,
          filename + " missing measured pixel header")
    for forbidden in ("ui_draw_header(", "ui_badge(",
                      "ui_footer_pair(", "furi_hal_gpio_"):
        check(forbidden not in body, filename + ": " + forbidden)

dashboard = read("src/labmate_dashboard_screen.c")
for token in (
    "labmate_pixel_header(c,", "UiKitKeyUpDown, \"Source\"",
    "labmate_dashboard_store_read_measurement(",
    "labmate_snapshot_v1_can_display_measurement(",
    '"SEALED ONLY"', '"HISTORICAL ONLY"',
):
    check(token in dashboard, "Dashboard: " + token)
scope = read("src/labmate_scope_ui.h")
for token in ("labmate_scope_ui_footer(", "FontSecondary, 12, 9, title",
              'FontSecondary, 105, 9, "PC1"'):
    check(token in scope, "Scope: " + token)
for token in ("furi_hal_gpio_", "storage_file_write("):
    check(token not in dashboard + scope, "New UI does I/O: " + token)

# Conservative 6-pixel ASCII glyph geometry, status-chip right aligned.
# Runtime canvas_string_width does the definitive width check.
scenarios = (
    ("Alerts", "ALRT"), ("Button", "BUSY"), ("Logger", "READY"),
    ("History", "255/255"), ("Log view", "WAIT"),
    ("Profiles", "DELETED"), ("Profiles", "PWM ON"),
    ("UART TX", "DROP"), ("I2C", "FW API"),
    ("1-Wire temp", "ERROR"), ("Stats", "2/2"),
    ("Evidence", "2/2"),
)
header = read("src/labmate_pixel_ui.h")
check("canvas_string_width(canvas, title) + 15U >= x" in header,
      "Title/status measured collision protection absent")
for title, status in scenarios:
    chip_x = 127 - (len(status) * 6 + 12)
    check(len(title) * 6 + 15 < chip_x,
          "Estimated collision: " + title + " / " + status)

print("E11 PIXEL UI SOURCE AUDIT PASS: 7 approved renderers, "
      "11 native/input files, 9 migrated screens, 12 chip layouts")
print("HOST SOURCE AUDIT ONLY; E11 FAP AND DEVICE TESTS PENDING")
