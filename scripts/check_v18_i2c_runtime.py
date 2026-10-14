#!/usr/bin/env python3
"""Fail closed for the v1.8 integrated real I2C runtime / menu boundaries.

Static source checks complement host fake-HAL tests and the SDK FAP build.
These DO NOT establish a real on-device I2C probe or patched firmware build.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
read = lambda path: (root / path).read_text(encoding="utf-8")

adapter = read("src/labmate_i2c_momentum.c")
runtime = read("src/labmate_i2c_runtime.c")
screen = read("src/labmate_i2c_ui.c")
handler = read("src/labmate_input_i2c.c")
app = read("src/labmate.c")
menu = read("src/labmate_navigation.c")
routing = read("src/labmate_input.c")
patch = read("scripts/patch_momentum_i2c_timeout.py")

assert "FURI_HAL_I2C_HAS_EXTERNAL_ACQUIRE_TIMEOUT" in adapter
assert "LABMATE_MOMENTUM_TIMED_I2C_API" in adapter
assert "furi_hal_i2c_external_acquire_timeout(timeout_ms)" in adapter
assert "furi_hal_i2c_is_device_ready(" in adapter
assert "furi_hal_i2c_release(&furi_hal_i2c_handle_external)" in adapter
assert "furi_hal_i2c_acquire(" not in adapter
assert "#else" in adapter and "return false;" in adapter

assert "furi_thread_alloc_ex(" in runtime
assert "furi_thread_start(" in runtime
assert "furi_thread_join(" in runtime
assert "furi_thread_free(" in runtime
assert "labmate_comm_local_claim(" in runtime
assert "labmate_comm_local_release(" in runtime
assert "s->stop_requested = true;" in runtime
assert "labmate_i2c_momentum_available()" in runtime
assert "labmate_i2c_runtime_reap(s);" in runtime
assert "furi_hal_i2c_acquire(" not in runtime
assert "labmate_i2c_runtime_free(app->i2c);" in app
assert "labmate_i2c_runtime_poll(app->i2c);" in app

for s in ("LabMateToolI2c", "LabMateToolOneWire", "LabMateToolUart"):
    assert s in menu
assert '"MEASURE", "OUTPUT", "RECORDS", "INFO", "COMM"' in menu
assert "LabMateScreenI2c" in routing
assert "labmate_input_i2c(app, event, work);" in routing
assert "labmate_i2c_runtime_start(" in handler
assert "labmate_i2c_runtime_stop(" in handler
assert "event.key == InputKeyBack" in handler
assert "event.key == InputKeyOk" in handler

assert '"FW API"' in screen
assert '"NO ACKS / CHECK BUS"' in screen
assert '"REAL ACK RESULTS"' in screen
assert "result.row_address[i]" in screen
assert "ui_footer_pair(canvas" in screen
assert "FURI_HAL_I2C_HAS_EXTERNAL_ACQUIRE_TIMEOUT" in patch
assert "FuriWaitForever" in patch

print("I2C runtime integration PASS (SOURCE ONLY, physical scan still pending)")
