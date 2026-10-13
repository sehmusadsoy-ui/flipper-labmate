#!/usr/bin/env python3
"""I2C lifecycle model guard. Does NOT prove bus ownership/cancel timing."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
header = (root / "src/labmate_i2c_control.h").read_text()
source = (root / "src/labmate_i2c_control.c").read_text()
test = (root / "tests/test_i2c_control.c.inc").read_text()

for forbidden in (
    "furi_", "Furi", "gpio_", "Gpio", "canvas_", "storage_",
    "pthread_", "LL_I2C", "furi_hal_i2c_acquire("
):
    assert forbidden not in source, f"Unexpected hardware dependency: {forbidden}"

for required in (
    "LabMateI2cControlAwaitAcquire",
    "LabMateI2cControlScanning",
    "LabMateI2cControlAwaitRelease",
    "LabMateI2cControlCancelled",
    "LabMateI2cControlFailed",
    "bus_held",
    "stop_requested",
    "probe_inflight",
    "generation",
):
    assert required in header, required

acq = source.split("bool labmate_i2c_control_acquire_done(", 1)[1]
assert "c->bus_held = true;" in acq
assert "if(c->stop_requested)" in acq
assert "c->state = LabMateI2cControlAwaitRelease;" in acq
assert "labmate_i2c_scan_begin(&c->scan);" in acq
assert acq.index("if(c->stop_requested)") < acq.index("labmate_i2c_scan_begin(&c->scan);")

stop = source.split("bool labmate_i2c_control_request_stop(", 1)[1].split(
    "bool labmate_i2c_control_acquire_done(", 1
)[0]
assert "c->stop_requested = true;" in stop
assert "AwaitAcquire remains pending" in stop
assert "c->state = LabMateI2cControlCancelled;" not in stop
assert "c->bus_held = false;" not in stop

release = source.split("bool labmate_i2c_control_release_done(", 1)[1]
assert "c->bus_held = false;" in release
assert "c->state != LabMateI2cControlAwaitRelease" in release

for required in (
    "test_stop_during_blocked_acquire();",
    "test_acquire_denied_after_stop();",
    "test_full_scan_and_release();",
    "test_cancel_during_inflight_probe();",
    "test_cancel_between_probes();",
    "test_probe_error_and_restart();",
):
    assert required in test, required

# The pure functions are NOT integrated into event routing or GPIO.
app_sources = "".join((root / "src" / file).read_text() for file in (
    "labmate.c", "labmate_input.c", "labmate_view.c", "labmate_input_menu.c"
))
assert "labmate_i2c_control_" not in app_sources
print("I2C lifecycle: pure state-only, no HAL/UI integration or fake cancel/release PASS")
