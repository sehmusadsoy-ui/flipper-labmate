#!/usr/bin/env python3
"""128x64 passive UI layout contracts for LabMate v1.7.

These conservative checks use up to 6 pixels per secondary glyph; physical
display inspection is still required. None of this test touches GPIO or SD.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
UI = (ROOT / "labmate_ui_screens.c").read_text(encoding="utf-8")
APP = (ROOT / "labmate.c").read_text(encoding="utf-8")
ICONS = (ROOT / "labmate_ui_primitives.c").read_text(encoding="utf-8")
WIDTH = 128
GLYPH = 6

def fits(text: str, x: int = 3, width: int = WIDTH) -> bool:
    return x + GLYPH * len(text) <= width

# Full-width labels and contextual footers must fit the 128px screen.
examples = {
    "Button contact": "SETTLING",
    "Button status": "PC1 / PULLUP",
    "Button controls": "<>DB vMORE OK RUN",
    "Button active": "v MORE  OK STOP  BK",
    "Button details": "v LIVE  OK TOGGLE",
    "Button bounce label": "BOUNCE us",
    "Button settle label": "SETTLE ms",
    "Counter metadata": "PB3 / TIM2 / RISE",
    "Counter controls": "OK RUN ^RST BK EXIT",
    "Alert source": "BUTTON SETTLE",
    "Alert state": "WAITING FOR SAMPLE",
    "Alert trip": "TRIPPED / v ACK",
    "Alert disarmed": "<>SRC ^vLIM OK ARM",
    "PWM editor step": "STEP:1000 BK:CANCEL",
    "PWM editor controls": "<>Hz ^vSTEP OK:SET",
    "Help footer": "<> PAGE   BK MENU",
}
for name, text in examples.items():
    assert fits(text), f"{name} overflows full row: {text}"

# Two-column metric cells are 60px wide at x=3 and x=66; ten decimal
# digits fit exactly without sacrificing numerical range.
for name, value in {
    "Button uint32": "4294967295",
    "Button bounce edges": "65535",
}.items():
    assert len(value) * GLYPH <= 60, f"{name} exceeds column"
assert len("18446744073709551615") * GLYPH <= 124, "Full counter overflows"

# Right-column labels start at x=66. Full uint32 values are 10 digits.
for name in ("RELEASE", "SETTLE ms", "BOUNCE N"):
    assert 66 + GLYPH * len(name) <= 127, f"Button column overflow: {name}"
assert 3 + GLYPH * len("PC1 / PULLUP") < 125 - GLYPH * len("DB 50 ms")
assert 3 + GLYPH * len("EVENTS") < 125 - GLYPH * len("4294967295s")

# Right-aligned alert threshold must not overlap the x=3 limit label.
for value in ("1000000 edges", "50000 Hz", "1000 ms", "95 %"):
    assert WIDTH - GLYPH * len(value) > 3 + GLYPH * len("TRIP >=")

# Each help page has four compact lines; cover all 11 tool IDs once.
pages = re.findall(
    r'\[LabMateTool\w+\]\s*=\s*\{\s*"([^"]+)",\s*"([^"]+)",'
    r'\s*"([^"]+)",\s*"([^"]+)",\s*\}', UI
)
assert len(pages) == 11, f"Expected 11 About tool guides, got {len(pages)}"
for page in pages:
    for line in page:
        assert fits(line), f"Help line overflows 128px: {line}"

required = (
    'void draw_about(Canvas* canvas, LabMateApp* app)',
    '"SauronLAB / Sehmus"',
    '"3.3V GPIO ONLY"',
    '"flipper-labmate"',
    '"CONTACT"',
    '"SETTLING"',
    '"BOUNCE us"',
    '"SETTLE ms"',
    '"HOLD ms"',
    '"BOUNCE N"',
    '"PB3 / TIM2 / RISE"',
    '"EVENTS"',
    '"SOURCE"',
    '"TRIP >="',
    '"TRIPPED / v ACK"',
    '"WAITING FOR SAMPLE"',
    '"STEP:%lu BK:CANCEL"',
    '"<>Hz ^vSTEP OK:SET"',
    'app->threshold.source == LabMateAlertFrequency',
    'app->threshold.source == LabMateAlertPulseDuty',
    'app->threshold.source == LabMateAlertCounter',
    'app->threshold.source == LabMateAlertButtonSettle',
)
for item in required:
    assert item in UI, f"Missing UI contract: {item}"
for tool in (
    "Gpio", "Frequency", "Pulse", "Generator", "Logger", "History",
    "About", "Profiles", "Counter", "Button", "Alerts",
):
    assert f"case LabMateTool{tool}:" in ICONS, f"Icon mapping missing: {tool}"

assert "app->button_details_view = !app->button_details_view;" in APP
assert "app->about_page = labmate_nav_wrap(" in APP
assert "canvas_draw_line(canvas, 0, 53, 127, 53);" in UI
assert '"ALERT"' not in APP, "Renderer must not overlay instrument header"
print(f"LabMate v1.7 UI check PASS: {len(pages)} guide pages, "
      f"{len(examples)} width cases, 11 functional icons")
