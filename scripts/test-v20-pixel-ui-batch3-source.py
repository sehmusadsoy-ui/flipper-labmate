#!/usr/bin/env python3
"""Static UI-only contract; host-native E11 render tests are still required."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
d = (root / "src/labmate_dashboard_screen.c").read_text()
scope = (root / "src/labmate_scope_ui.h").read_text()
assert "labmate_pixel_header(c," in d
assert 'UiKitKeyUpDown, "Source", UiKitKeyOk, "Stats"' in d
assert 'UiKitKeyLeftRight, "Page", UiKitKeyOk, "List"' in d
assert 'UiKitKeyLeftRight, "Page", UiKitKeyOk, "More"' in d
assert "ui_draw_header(" not in d and "ui_badge(" not in d
assert "ui_footer_pair(" not in d
assert "labmate_dashboard_store_read_measurement(" in d
assert "labmate_snapshot_v1_can_display_measurement(" in d
assert '"SEALED ONLY"' in d and '"HISTORICAL ONLY"' in d
assert "canvas_draw_line(c, 7, 2, 4, 5)" in scope
assert "FontSecondary, 12, 9, title" in scope
assert 'FontSecondary, 105, 9, "PC1"' in scope
assert "labmate_scope_ui_footer(" in scope
for s in (d,scope):
    for unsafe in ("furi_hal_gpio_", "storage_file_write(", "furi_hal_resource_lease_"):
        assert unsafe not in s, unsafe
print("E11 PIXEL BATCH3 SOURCE REVIEW PASS: Dashboard + Scope header; NATIVE PENDING")
