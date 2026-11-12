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
    "src/labmate_input_measure.c",
    "src/labmate_capture_session.c",
    "src/labmate_capture_core.c",
    "src/labmate_event_counter.c",
    "src/labmate_frequency_capture.c",
    "src/labmate_frequency_tim2.c",
    "src/labmate_pulse_capture.c",
    "src/labmate_scope_native.c",
)
changed = git("diff", "--name-only", base, "--", *inputs).decode().strip()
check(not changed, "Native/input source changed unexpectedly: " + changed)
# Keep the approved menu byte-for-byte except for the reviewed failed-release
# fix. Include working-tree changes so uncommitted safety edits are not hidden.
menu_original = git("show", base + ":src/labmate_input_menu.c").decode()
menu_old = (
    "                        labmate_onewire_hw_stop(&app->thermometer);\n"
    "                        labmate_onewire_hw_init(&app->thermometer);"
)
menu_new = "                        labmate_onewire_hw_reenter(&app->thermometer);"
check(menu_original.count(menu_old) == 1, "OneWire menu baseline changed")
check(read("src/labmate_input_menu.c") == menu_original.replace(menu_old, menu_new),
      "Menu changed beyond the reviewed OneWire failed-release fix")
# The persistence audit found that an EXIST collision still leaves an
# attempted-open handle. Permit only its reviewed close-before-retry block;
# compare index + working tree bytes, never only committed HEAD.
logger_original = git("show", base + ":src/labmate_logger_storage.c").decode()
logger_anchor = "        if(storage_file_get_error(app->logger_file) != FSE_EXIST) break;\n"
logger_close = (
    "        /* A failed CREATE_NEW still owns an attempted-open handle.\n"
    "         * Close it before trying the next ID; never reuse or truncate\n"
    "         * the competing writer's file. */\n"
    "        if(!storage_file_close(app->logger_file)) {\n"
    "            storage_file_free(app->logger_file);\n"
    "            app->logger_file = NULL;\n"
    "            break;\n"
    "        }\n"
)
check(logger_original.count(logger_anchor) == 1, "Logger retry baseline changed")
check(read("src/labmate_logger_storage.c") == logger_original.replace(
          logger_anchor, logger_anchor + logger_close),
      "Logger changed beyond the reviewed close-before-retry fix")
original = git("show", base + ":src/labmate_ui_screens.c").decode()
current = read("src/labmate_ui_screens.c")
for name in (
    "draw_menu", "draw_gpio", "draw_counter",
    "draw_pulse", "draw_pulse_stats", "draw_generator",
):
    check(function(original, name) == function(current, name),
          "Approved renderer changed: " + name)
# 2026-11-12 review: Frequency keeps its approved geometry. Permit only two
# reviewed text-state fixes: an explicit "Over range" state above the uint32
# millihertz limit, and Stable/Drifting judged on recent readings instead of
# session Min/Max. Coordinates, fonts and every draw call stay byte-identical.
freq_hero_old = (
    '        ui_kit_center_text(canvas, 31, "No signal", NULL);\n'
)
freq_hero_new = (
    '        ui_kit_center_text(\n'
    '            canvas, 31, app->frequency_over_range ? "Over range" : "No signal", NULL);\n'
)
freq_drift_old = (
    '    const bool drifting = app->frequency_stats_valid &&\n'
    '                          app->frequency_min_millihz > 0U &&\n'
    '                          app->frequency_max_millihz - app->frequency_min_millihz >\n'
    '                              app->frequency_min_millihz / 20U;\n'
    '    const char* status = alert ? "Alert" : app->capture_blocked ? "Busy" :\n'
    '                         app->hold ? "Held" : !app->frequency_valid ? "No signal" :\n'
    '                         drifting ? "Drifting" : "Stable";\n'
)
freq_drift_new = (
    '    /* Drift is judged on the last ~3 s of valid readings, not on session\n'
    '     * Min/Max: one earlier frequency change must not pin "Drifting". */\n'
    '    uint32_t recent_min = UINT32_MAX;\n'
    '    uint32_t recent_max = 0U;\n'
    '    const uint8_t recent_count =\n'
    '        app->ui_frequency_recent_count <= 32U ? app->ui_frequency_recent_count : 32U;\n'
    '    for(uint8_t i = 0U; i < recent_count; ++i) {\n'
    '        const uint32_t sample = app->ui_frequency_recent[i];\n'
    '        if(sample < recent_min) recent_min = sample;\n'
    '        if(sample > recent_max) recent_max = sample;\n'
    '    }\n'
    '    const bool drifting = recent_count >= 2U && recent_min > 0U &&\n'
    '                          recent_max - recent_min > recent_min / 20U;\n'
    '    const char* status = alert ? "Alert" : app->capture_blocked ? "Busy" :\n'
    '                         app->hold ? "Held" :\n'
    '                         app->frequency_over_range ? "Over range" :\n'
    '                         !app->frequency_valid ? "No signal" :\n'
    '                         drifting ? "Drifting" : "Stable";\n'
)
freq_original = function(original, "draw_frequency")
check(freq_original.count(freq_hero_old) == 1 and
      freq_original.count(freq_drift_old) == 1,
      "Frequency renderer baseline changed")
check(function(current, "draw_frequency") ==
          freq_original.replace(freq_hero_old, freq_hero_new)
                       .replace(freq_drift_old, freq_drift_new),
      "Frequency renderer changed beyond the reviewed state-text fixes")

migrated = (
    "draw_alerts", "draw_button", "draw_logger", "draw_history",
    "draw_history_detail", "draw_profiles",
)
for name in migrated:
    body = function(current, name)
    header = "ui_kit_pixel_header(" if name == "draw_button" else "labmate_pixel_header(canvas,"
    check(header in body, "Pixel header absent in " + name)
    if name == "draw_button":
        check("UiKitInstrumentError" in body and
              "UiKitInstrumentBusy" in body and
              "UiKitInstrumentStopped" in body and
              "UiKitKeyDown" in body and "button_session_started" in body,
              "Button Step 2 state/key contract missing")
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
    expected_header = (
        'ui_kit_pixel_header(canvas, "I2C explorer"' if
        filename == "labmate_i2c_ui.c" else
        'ui_kit_pixel_header(canvas, "1-Wire temp"' if
        filename == "labmate_onewire_ui.c" else
        "labmate_comm_ui_header(")
    check(expected_header in body,
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
