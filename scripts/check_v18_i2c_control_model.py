#!/usr/bin/env python3
"""I2C model integration gate: verify lifecycle remains HAL-free and cancellation truthful."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
h = (root / "src/labmate_i2c_control.h").read_text()
c = (root / "src/labmate_i2c_control.c").read_text()
tests = (root / "tests/test_i2c_control.c.inc").read_text()

for forbidden in ("#include <furi", "furi_hal_i2c_acquire(", "furi_hal_gpio_", "canvas_", "storage_"):
    assert forbidden not in c, f"Pure I2C state must not directly touch device: {forbidden}"
for req in ("AwaitAcquire", "AwaitRelease", "stop_requested", "bus_held", "probe_inflight", "generation"):
    assert req in h, f"Missing lifecycle state: {req}"
before_acquire = c.split("bool labmate_i2c_control_request_stop(",1)[1].split("bool labmate_i2c_control_acquire_done(",1)[0]
assert "c->stop_requested = true;" in before_acquire
assert "AwaitAcquire remains pending" in before_acquire
assert "c->bus_held = false;" not in before_acquire
release = c.split("bool labmate_i2c_control_release_done(",1)[1]
assert "c->bus_held = false;" in release
for test_name in ("test_stop_during_blocked_acquire();", "test_acquire_denied_after_stop();",
                  "test_full_scan_and_release();", "test_cancel_during_inflight_probe();",
                  "test_cancel_between_probes();", "test_probe_error_and_restart();"):
    assert test_name in tests, test_name
print("v1.8 I2C lifecycle state and truthful cancellation guard PASS (model only)")
