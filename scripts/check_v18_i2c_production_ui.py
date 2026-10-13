#!/usr/bin/env python3
"""Verify I2C Explorer is reached from the actual labmate.fap, NOT a demo.

This gate is intentionally NOT an acceptance of a real I2C hardware scan.
Momentum's I2C3 bus lock is non-bounded; no GPIO, HAL I2C or fake
discovered-device list is allowed until an independently reviewed fix.
"""
from pathlib import Path

src = Path(__file__).resolve().parents[1] / "src"
read = lambda p: (src / p).read_text()
app = read("labmate.c")
nav_h = read("labmate_navigation.h")
nav_c = read("labmate_navigation.c")
input_menu = read("labmate_input_menu.c")
input_router = read("labmate_input.c")
view = read("labmate_view.c")
ui = read("labmate_ui_screens.c")
ui_h = read("labmate_ui_screens.h")
icons = read("labmate_ui_primitives.c")
model = read("labmate_i2c_control.c")

assert "LabMateToolI2c" in nav_h
assert '"I2C Explorer"' in nav_c
assert "{LabMateToolUart, LabMateToolI2c," in nav_c
assert "case LabMateToolI2c:" in input_menu
assert "app->screen = LabMateScreenI2c;" in input_menu
assert "LabMateScreenI2c" in read("labmate_internal.h")
assert "LabMateI2cControl i2c;" in read("labmate_internal.h")
assert "labmate_i2c_control_reset(&app->i2c);" in app
assert "case LabMateScreenI2c:" in input_router
assert "if(event.key == InputKeyBack) app->screen = LabMateScreenMenu;" in input_router
assert "case LabMateScreenI2c:" in view
assert "draw_i2c(canvas, app);" in view
assert "void draw_i2c(Canvas* canvas, LabMateApp* app);" in ui_h
assert "void draw_i2c(Canvas* canvas, LabMateApp* app)" in ui
assert "labmate_i2c_present(&app->i2c, 0U, &view)" in ui
assert "case LabMateToolI2c: ui_icon_i2c(canvas, x, y); break;" in icons

# Explicitly truthful initial status in a user-facing production screen.
for label in (
    '"HW SCAN DISABLED"',
    '"BUS LOCK NOT BOUNDED"',
    '"NOT SCANNED"',
    '"MODEL NOT READY"',
    '"OK", "BLOCK", "BACK", "MENU"',
):
    assert label in ui, f"Missing truthful I2C app message: {label}"

# No UI input can initiate a fake scan or enter an unbounded I2C HAL lock.
code = "\n".join((input_menu, input_router, view, app, ui))
for forbidden in (
    "labmate_i2c_control_start(",
    "labmate_i2c_control_acquire_done(",
    "labmate_i2c_control_probe_done(",
    "labmate_i2c_control_next_probe(",
    "furi_hal_i2c_acquire(",
    "furi_hal_i2c_is_device_ready(",
    "power_enable_otg(",
    "gpio_ext_pc0",
    "gpio_ext_pc1",
):
    assert forbidden not in code, f"Unsafe/fake live I2C action: {forbidden}"
assert "furi_hal_i2c_acquire(" not in model
print("v1.8 I2C production LabMate navigation/UI integrated, bus still fail-closed PASS")
