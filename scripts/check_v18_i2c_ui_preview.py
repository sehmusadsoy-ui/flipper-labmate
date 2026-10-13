#!/usr/bin/env python3
"""Verify the isolated I2C preview cannot be mistaken for real bus support."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
preview = (root / "tests/flipper_i2c_ui_preview/preview.c").read_text()
manifest = (root / "tests/flipper_i2c_ui_preview/application.fam").read_text()
production = (root / "application.fam").read_text()
workflow = (root / ".github/workflows/v18-i2c-ui-preview.yml").read_text()

for forbidden in (
    "furi_hal_i2c_", "furi_hal_gpio_", "gpio_ext_pc0", "gpio_ext_pc1",
    "furi_hal_power_", "storage_", "furi_hal_serial_", "furi_hal_bus_",
):
    assert forbidden not in preview, f"Unsafe bus/resource API in UX demo: {forbidden}"

for required in (
    '#include "../../src/labmate_i2c_scan.c"',
    '#include "../../src/labmate_i2c_control.c"',
    '#include "../../src/labmate_i2c_present.c"',
    '"SIMULATED - NO BUS"',
    'labmate_i2c_view_status_text(v->status)',
    'labmate_i2c_present(&demo.control, demo.page, &demo.snapshot)',
    'InputKeyBack',
    'InputKeyLeft',
    'InputKeyRight',
    'InputKeyUp',
    'InputKeyDown',
):
    assert required in preview, required

# GUI callback reads a short snapshot under its mutex; it must never
# draw while holding mutable state or leave a live mutex at app shutdown.
for required in (
    "FuriMutex* lock;",
    "furi_mutex_acquire(demo->lock, FuriWaitForever);",
    "const LabMateI2cView copy = demo->snapshot;",
    "furi_mutex_release(demo->lock);",
    "furi_mutex_acquire(demo.lock, FuriWaitForever);",
    "furi_mutex_release(demo.lock);",
    "furi_mutex_free(demo.lock);",
):
    assert required in preview, required

assert 'appid="labmate_i2cuipreview"' in manifest
assert 'sources=["preview.c"]' in manifest
assert 'sources=["src/*.c"]' in production
assert 'tests/flipper_i2c_ui_preview' in workflow
assert 'name: labmate-i2c-ui-preview' in workflow
assert "labmate_i2cuipreview.fap" in workflow

assert "LabMateToolI2c" not in (root / "src/labmate_navigation.h").read_text()
assert "LabMateScreenI2c" not in (root / "src/labmate_navigation.h").read_text()
print("Safe standalone I2C UX preview guard PASS: visible SIMULATED warning, no bus calls")
