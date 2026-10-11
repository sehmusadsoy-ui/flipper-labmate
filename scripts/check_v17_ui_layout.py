#!/usr/bin/env python3
"""128x64 compact-screen contract checks for LabMate v1.7.

Conservative secondary-font budget: 6 px per glyph at x=2 gives 21 glyphs.
This host-side check prevents common overflow regressions; real-device visual
inspection remains mandatory because glyph widths/fonts can differ.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = (ROOT / "labmate_ui_screens.c").read_text(encoding="utf-8")
APP = (ROOT / "labmate.c").read_text(encoding="utf-8")
WIDTH = 128
LEFT = 2
SECONDARY_GLYPH_MAX = 6


def fits(text: str) -> bool:
    return LEFT + len(text) * SECONDARY_GLYPH_MAX <= WIDTH


# The longest formatted numeric values, not only attractive sample values,
# must fit the 128px display. Counts can reach UINT32_MAX.
cases = {
    "Button contact": "PC1  <>DB:50 ms",
    "Button state": "CONTACT: SETTLING",
    "Button presses": "PRESS:4294967295",
    "Button releases": "RELEASE:4294967295",
    "Button bounce": "BOUNCE:4294967295 us",
    "Button settle": "SETTLE:4294967295 ms",
    "Button hold": "HOLD:4294967295 ms",
    "Button edges": "BOUNCE EDGES:65535",
    "Button run footer": "v PAGE OK STOP BK",
    "Button stop footer": "<>DB ^RST vPAGE OK",
    "Counter full uint64": "18446744073709551615",
    "Counter stopped footer": "OK RUN  ^RST BK EXIT",
    "Alert threshold edges": "AT >= 1000000 edges",
    "Alert threshold frequency": "AT >= 50000 Hz",
    "Alert source": "BUTTON SETTLE",
    "Alert tripped": "TRIPPED: CHECK INPUT",
    "Alert no sample": "NO LIVE SAMPLE",
    "Alert armed footer": "v ACK OK OFF BK EXIT",
    "Alert disarmed footer": "<> SRC ^v LIM OK ARM",
    "PWM editor step": "STEP:1000 BK:CANCEL",
    "PWM editor footer": "<>Hz ^vSTEP OK:SET",
}
for label, sample in cases.items():
    assert fits(sample), f"{label}: {len(sample)} chars would overflow at x={LEFT}: {sample}"

# These placeholders/phrases must agree with the formats above. Do not let a
# layout refactor accidentally drop an instrument metric or a control hint.
for required in (
    'ui_draw_header(canvas, "BUTTON")',
    '"PC1  <>DB:%u ms"',
    '"CONTACT: SETTLING"',
    '"PRESS:%lu"',
    '"RELEASE:%lu"',
    '"BOUNCE:%lu us"',
    '"SETTLE:%lu ms"',
    '"HOLD:%lu ms"',
    '"BOUNCE EDGES:%u"',
    '"AT >= %lu %s"',
    '"TRIPPED: CHECK INPUT"',
    '"NO LIVE SAMPLE"',
    '"STEP:%lu BK:CANCEL"',
    '"<>Hz ^vSTEP OK:SET"',
    'app->threshold.source == LabMateAlertFrequency',
    'app->threshold.source == LabMateAlertPulseDuty',
    'app->threshold.source == LabMateAlertCounter',
    'app->threshold.source == LabMateAlertButtonSettle',
):
    assert required in UI, f"missing UI layout contract: {required}"
assert "app->button_details_view = !app->button_details_view;" in APP
assert '"ALERT"' not in APP, "app renderer must not overlay an instrument header"
assert "canvas_draw_line(canvas, 0, 53, 127, 53);" in UI
print(f"v1.7 UI layout contract PASS: {len(cases)} worst-case labels checked")
