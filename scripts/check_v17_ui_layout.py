#!/usr/bin/env python3
"""128x64 Canvas layout regression checks for LabMate v1.7 final UI polish (including Records).

Static, conservative glyph bounds only: each secondary char is budgeted at
6 px and primary numeric glyph at 9 px. On-device inspection is still
mandatory; these tests never touch Flipper GPIO, timers or files.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
UI = (SRC / "labmate_ui_screens.c").read_text(encoding="utf-8")
NAV = (SRC / "labmate_navigation.c").read_text(encoding="utf-8")
APP = "\n".join((SRC / filename).read_text(encoding="utf-8") for filename in (
    "labmate.c", "labmate_input.c", "labmate_capture_session.c",
    "labmate_deferred.c", "labmate_view.c", "labmate_input_menu.c",
    "labmate_input_profiles.c", "labmate_input_history.c",
    "labmate_input_measure.c", "labmate_input_output.c"))
PRIMITIVES = (SRC / "labmate_ui_primitives.c").read_text(encoding="utf-8")
PRIMITIVES_H = (SRC / "labmate_ui_primitives.h").read_text(encoding="utf-8")
WIDTH = 128
GLYPH = 6


def fits(text: str, x: int = 3, width: int = WIDTH) -> bool:
    return x + GLYPH * len(text) <= width


# 2 x 62px footer cells, each with its own framed physical key.
assert "void ui_footer_pair(" in PRIMITIVES and "void ui_footer_pair(" in PRIMITIVES_H
assert 'canvas_draw_frame(canvas, x, 54, key_width, 10)' in PRIMITIVES
assert 'ui_footer_action(canvas, 2, left_key, left_action);' in PRIMITIVES
assert 'ui_footer_action(canvas, 66, right_key, right_action);' in PRIMITIVES
footer_pairs = re.findall(
    r'ui_footer_pair\(canvas,\s*"([^"]+)",\s*"([^"]+)",'
    r'\s*"([^"]+)",\s*"([^"]+)"\)', UI,
)
assert len(footer_pairs) >= 8, "Expected context-specific pairs in 4 instruments"
for left_key, left_action, right_key, right_action in footer_pairs:
    for key, action in ((left_key, left_action), (right_key, right_action)):
        width = len(key) * GLYPH + 6 + 3 + len(action) * GLYPH
        assert width <= 60, f"Footer overlaps adjacent cell: {key} {action}"
        assert key.isalpha() and action.isalpha(), "Avoid cryptic glyph/arrow footers"
# Dynamic Button STOP/START strings share equal/smaller widths.
for fragment in ('"DOWN", "MAIN"', '"DOWN", "MORE"',
                 'app->button_active ? "STOP" : "START"'):
    assert fragment in UI, f"Missing Button footer mode: {fragment}"

# Stable version text fits the same badge used by RC1; do not alter UI layout.
assert 'ui_badge(canvas, 70, 1, 56, LABMATE_VERSION_TEXT, false);' in UI
assert len("v1.8") * GLYPH + 8 <= 56

# Entire help guide and its safety/credit page must remain readable.
pages = re.findall(
    r'\[LabMateTool\w+\]\s*=\s*\{\s*"([^"]+)",\s*"([^"]+)",'
    r'\s*"([^"]+)",\s*"([^"]+)",\s*\}', UI,
)
assert len(pages) == 12, f"Expected 12 About tool guides; got {len(pages)}"
assert '"PWM Studio"' in NAV, "Menu must display PWM Studio"
assert '"Signal Generator"' not in NAV, "Obsolete menu label returned"
assert '"PWM STUDIO"' in UI, "About tool guide must say PWM STUDIO"
assert '"SIGNAL GENERATOR"' not in UI, "Obsolete About label returned"
for page in pages:
    for line in page:
        assert fits(line), f"About text would exceed 128px: {line}"
for text in ('"SauronLAB / Sehmus"', '"3.3V GPIO ONLY"',
             '"flipper-labmate"'):
    assert text in UI

# Four redesigned instruments: body hierarchy and dynamic badges intact.
for text in (
    '"PB3 / TIM2 / RISE"', '"COUNT"', '"TIME"',
    '"PC1 / PULLUP"', '"CONTACT"', '"PRESSES"', '"RELEASES"',
    '"BOUNCE us"', '"SETTLE ms"', '"HOLD ms"', '"BOUNCE N"',
    '"SOURCE"', '"LIMIT"', '"ALERT LATCHED"', '"WAITING FOR INPUT"',
    '"DISARMED"', '"OUTPUT FREQ"', '"UP DOWN: DUTY"',
):
    assert text in UI, f"Missing visible metric or status: {text}"

# Numeric columns must not intersect the 80px Counter divider.
assert 4 + 7 * 9 < 80, "Primary count text would intersect timer"
assert 4 + 11 * GLYPH < 80, "Secondary count text would intersect timer"
assert 86 + 6 * GLYPH < 128, "Longest formatted timer overflows"
assert 3 + 20 * GLYPH <= 127, "Full uint64 count overflows LCD"
assert 'if(count_len > 11U)' in UI, "Long counter display needs full-width fallback"
assert 'strlen(time_text) <= 4U ? FontPrimary : FontSecondary' in UI
assert 'app->counter_elapsed_seconds' in UI

# Button counters must not cross the centre divider; source+DB need gap.
assert 67 + 10 * GLYPH <= 127, "Button uint32 overflows right column"
assert 3 + len("PC1 / PULLUP") * GLYPH < 125 - len("DB 50 ms") * GLYPH
for label in ("RELEASES", "SETTLE ms", "BOUNCE N"):
    assert 67 + len(label) * GLYPH <= 127, f"Button column overflows: {label}"

# Threshold sources and maximum limits must leave a visible label gap.
for value in ("1000000 edges", "50000 Hz", "1000 ms", "95 %"):
    assert WIDTH - GLYPH * len(value) > 3 + GLYPH * len("LIMIT")
assert WIDTH - GLYPH * len("BUTTON SETTLE") > 3 + GLYPH * len("SOURCE")
for status in ("ALERT LATCHED", "WAITING FOR INPUT", "LIMIT REACHED"):
    assert fits(status, x=6)
for requirement in (
    'app->threshold.source == LabMateAlertFrequency',
    'app->threshold.source == LabMateAlertPulseDuty',
    'app->threshold.source == LabMateAlertCounter',
    'app->threshold.source == LabMateAlertButtonSettle',
):
    assert requirement in UI

# Records UI must preserve read-only history and all profile slots, while
# using the same controls and 128px width rules as the rest of LabMate.
for display in (
    'void draw_logger(Canvas* canvas, LabMateApp* app)',
    'void draw_history(Canvas* canvas, LabMateApp* app)',
    'void draw_history_detail(Canvas* canvas, LabMateApp* app)',
    'void draw_profiles(Canvas* canvas, LabMateApp* app)',
    '"CAPTURE BLOCKED"', '"SD WRITE ERROR"', '"SAVING TO SD"',
    '"REC %lu ROWS"', '"READY / 1 SEC SAMPLE"',
    '"NO SAVED LOGS"', '"SCANNING SD..."', '"SD READ ERROR"',
    '"READ ONLY"', '"FILE"', '"MODE"', '"ROWS"',
    '"EMPTY"', '"LOADED"', '"DELETED"', '"PRESET"',
):
    assert display in UI, f"Missing Records UI feature: {display}"
assert 'ui_badge(canvas, 77, 1, 49, state, false);' in UI
assert 7 * GLYPH + 4 <= 49, "Profile status badge must fit DELETED"

for literal in (
    "FREQ / PB3 HIGH", "FREQ / PC1 LOW", "PULSE / PC1",
    "999ms / 100.0%", "4294.967kHz",
):
    # Value in the right-aligned LIVE field; MODE and LIVE labels use x=3.
    label = "LIVE" if ("ms /" in literal or "kHz" in literal) else "MODE"
    assert 125 - GLYPH * len(literal) >= 3 + GLYPH * len(label), (
        f"Record field overlaps {label}: {literal}"
    )
assert 122 - GLYPH * len("PC1 / 50000Hz") > 5 + GLYPH * len("S1")
assert 122 - GLYPH * len("log_65535.csv") > 5 + GLYPH * len("32")
assert 125 - GLYPH * len("log_65535.csv") > 3 + GLYPH * len("FILE")
assert 'app->profile_selected == i' in UI
assert 'idx == app->history_selected' in UI
assert 'app->profile_action == 2U ? "DELETE" : "SAVE"' in UI
assert '"BACK", "NO"' in UI
assert 'ui_footer_pair(canvas, "LR", action, "OK", blocked ? "BLOCK" : "SELECT");' in UI
assert '"LR", "MODE", "OK"' in UI
assert 'app->history_delete_mode ? "DELETE" : "OPEN"' in UI
assert 'app->history_delete_confirm' in UI
assert '"DELETE THIS FILE?"' in UI
assert '"CANNOT UNDO"' in UI
assert '"OK", "DELETE", "BACK", "NO"' in UI
assert '"FAIL"' in UI and '"DONE"' in UI
assert '"OK", "STOP", "BACK", "SAVE"' in UI
assert '"LR", "SOURCE", "OK", "RECORD"' in UI

# Profiles: current action must stay explicit during PWM RUN, and every
# operation/confirmation must refuse to alter RAM/SD while tools are active.
for literal in (
    '"OVERWRITE S%u?"', '"SAVE TO S%u?"', '"DELETE S%u?"',
    '"CANNOT UNDO"', '"REPLACES SAVED DATA"', '"NEW PROFILE"',
    'app->generator_running', '"PWM ON"',
    'blocked ? "BLOCK" : "SELECT"',
):
    assert literal in UI, f"Profiles safety screen missing {literal}"
assert APP.count('app->profile_notice = app->generator_running ? 4U : 8U;') == 2, (
    "Both profile actions and final SAVE/DELETE confirmation must check PWM/capture/logger"
)
assert APP.count('app->capture_owner != LabMateCaptureNone ||') >= 2
assert APP.count('app->logger_recording) {') >= 2

# The application still owns the actual input events; drawing never performs
# IRQ, storage or PWM work. Screen switching remains presentation-only.
assert "app->button_details_view = !app->button_details_view;" in APP
assert "app->about_page = labmate_nav_wrap(" in APP
assert 'canvas_draw_line(canvas, 0, 52, 127, 52);' in PRIMITIVES

for tool in ("Gpio", "Frequency", "Pulse", "Generator", "Logger",
             "History", "About", "Profiles", "Counter", "Button", "Alerts", "Uart"):
    assert f"case LabMateTool{tool}:" in PRIMITIVES, f"Missing icon {tool}"

print(f"LabMate v1.7 final UI polish PASS: {len(footer_pairs)} context footers, "
      f"{len(pages)} help pages, 12 unique tool icons")
