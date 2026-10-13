#!/usr/bin/env python3
"""Guard passive I2C snapshot formatting. Not a physical scan or GUI claim."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "src/labmate_i2c_present.c").read_text()
header = (root / "src/labmate_i2c_present.h").read_text()
tests = (root / "tests/test_i2c_present.c.inc").read_text()

for forbidden in (
    "furi_", "Furi", "canvas_", "storage_", "gpio_", "Gpio",
    "LL_I2C", "furi_mutex_", "furi_thread_", "furi_hal_i2c_"
):
    assert forbidden not in source, f"Hardware/UI dependency in pure I2C snapshot: {forbidden}"

for required in (
    "#define LABMATE_I2C_VIEW_ROWS 4U",
    "LabMateI2cViewNotScanned",
    "LabMateI2cViewStopPending",
    "LabMateI2cViewNoDevices",
    "LabMateI2cViewReleasing",
    "model_quiescent",
):
    assert required in header, required

assert "case LabMateI2cControlFinished:" in source
assert "c->scan.total_found == 0U ? LabMateI2cViewNoDevices" in source
assert "case LabMateI2cControlIdle: return LabMateI2cViewNotScanned;" in source
assert "c->stop_requested ? LabMateI2cViewStopPending" in source
assert "requested >= out->page_count" in source
assert "c->scan.stored_count > LABMATE_I2C_RESULT_CAP" in source
assert "!labmate_i2c_control_active(c) && !c->bus_held" in source

for required in (
    "test_unscanned_and_blocked();",
    "test_no_device_only_after_real_model_finish();",
    "test_pages_results_and_truncation();",
    "test_partial_cancel_and_error();",
):
    assert required in tests, required

# No live GUI or input hook-in until bus ownership + worker lifecycle are safe.
app_src = "".join((root / "src" / p).read_text() for p in (
    "labmate.c", "labmate_input.c", "labmate_view.c", "labmate_input_menu.c"
))
assert "labmate_i2c_present(" not in app_src
print("I2C UI model source isolation / honest statuses guard PASS (HOST ONLY)")
