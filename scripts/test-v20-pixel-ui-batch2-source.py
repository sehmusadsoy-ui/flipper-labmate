#!/usr/bin/env python3
"""Source-level UI review. The native E11 build and physical UI QA are separate."""
from pathlib import Path
import re

root = Path(__file__).resolve().parent.parent
src = (root / "src/labmate_ui_screens.c").read_text()
kit = (root / "src/labmate_pixel_ui.h").read_text()
comm = (root / "src/labmate_comm_ui.h").read_text()
screens = (
    "draw_alerts", "draw_button", "draw_logger",
    "draw_history", "draw_history_detail", "draw_profiles",
)
for name in screens:
    m = re.search(r"\bvoid\s+" + name + r"\s*\(", src)
    assert m is not None, name
    start = src.index("{", m.end())
    nesting = 0
    end = None
    for i in range(start, len(src)):
        if src[i] == "{":
            nesting += 1
        elif src[i] == "}":
            nesting -= 1
            if nesting == 0:
                end = i
                break
    assert end is not None, name
    body = src[start:end]
    assert "labmate_pixel_header(canvas," in body, name
    assert "ui_draw_header(" not in body, name
    assert "ui_badge(" not in body, name
    assert "ui_footer_pair(" not in body, name
    for unsafe in (
        "furi_hal_gpio_", "furi_hal_resource_lease_",
        "storage_file_write(", "labmate_capture_stop_all(",
    ):
        assert unsafe not in body, (name, unsafe)
assert "ui_kit_key_hint(canvas, 4U" in kit
assert "ui_kit_key_hint(canvas, 66U" in kit
assert "labmate_pixel_ui.h" in comm
for token in ("labmate_comm_ui_header", "labmate_comm_ui_keys"):
    assert token in comm
for filename in ("labmate_uart_ui.c", "labmate_i2c_ui.c", "labmate_onewire_ui.c"):
    source = (root / "src" / filename).read_text()
    assert 'labmate_comm_ui.h' in source, filename
print("E11 PIXEL BATCH2 SOURCE REVIEW PASS: 6 screens + 3 comm screens; NATIVE TEST PENDING")
