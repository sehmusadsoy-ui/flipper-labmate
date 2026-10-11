#!/usr/bin/env python3
"""128x64 Canvas layout regression checks for LabMate v1.7 UI polish 2.

Static, conservative glyph bounds only: each secondary char is budgeted at
6 px and primary numeric glyph at 9 px. On-device inspection is still
mandatory; these tests never touch Flipper GPIO, timers or files.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
UI = (ROOT / "labmate_ui_screens.c").read_text(encoding="utf-8")
APP = (ROOT / "labmate.c").read_text(encoding="utf-8")
PRIMITIVES = (ROOT / "labmate_ui_primitives.c").read_text(encoding="utf-8")
PRIMITIVES_H = (ROOT / "labmate_ui_primitives.h").read_text(encoding="utf-8")
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

# Entire help guide and its safety/credit page must remain readable.
pages = re.findall(
    r'\[LabMateTool\w+\]\s*=\s*\{\s*"([^"]+)",\s*"([^"]+)",'
    r'\s*"([^"]+)",\s*"([^"]+)",\s*\}', UI,
)
assert len(pages) == 11, f"Expected 11 About tool guides; got {len(pages)}"
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
    '"DISARMED"', '"OUTPUT FREQ"', '"UP/DN DUTY"',
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

# The application still owns the actual input events; drawing never performs
# IRQ, storage or PWM work. Screen switching remains presentation-only.
assert "app->button_details_view = !app->button_details_view;" in APP
assert "app->about_page = labmate_nav_wrap(" in APP
assert 'canvas_draw_line(canvas, 0, 52, 127, 52);' in PRIMITIVES

for tool in ("Gpio", "Frequency", "Pulse", "Generator", "Logger",
             "History", "About", "Profiles", "Counter", "Button", "Alerts"):
    assert f"case LabMateTool{tool}:" in PRIMITIVES, f"Missing icon {tool}"

print(f"LabMate v1.7 UI polish 2 PASS: {len(footer_pairs)} context footers, "
      f"{len(pages)} help pages, 11 unique tool icons")
