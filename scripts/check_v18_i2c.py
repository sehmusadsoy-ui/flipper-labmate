#!/usr/bin/env python3
"""Guard that the unintegrated I2C scan model stays pure and bounded.

This does not validate any physical I2C bus, HAL ownership or on-device scan.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
header = (root / "src/labmate_i2c_scan.h").read_text()
source = (root / "src/labmate_i2c_scan.c").read_text()
test = (root / "tests/test_i2c_scan.c.inc").read_text()

for blocked in ("furi_", "Furi", "gpio_", "Gpio", "canvas_", "storage_", "pthread_", "HAL_", "LL_I2C"):
    assert blocked not in source, f"Hardware dependency in pure I2C model: {blocked}"

for required in (
    "#define LABMATE_I2C_FIRST_ADDR 0x08U",
    "#define LABMATE_I2C_LAST_ADDR 0x77U",
    "#define LABMATE_I2C_RESULT_CAP 16U",
    "LabMateI2cScanCancelled",
    "LabMateI2cScanError",
):
    assert required in header, required

for required in (
    "scan->awaiting_result",
    "scan->next_address > LABMATE_I2C_LAST_ADDR",
    "scan->stored_count < LABMATE_I2C_RESULT_CAP",
    "scan->total_found > scan->stored_count",
    "(uint8_t)(address7 << 1U)",
):
    assert required in source, required

for required in (
    "check_addresses();",
    "check_all_empty_and_duplicate();",
    "check_sparse_and_bounded();",
    "check_cancel_and_error();",
):
    assert required in test, required

print("I2C pure model guards PASS (no physical bus or UI hooked up)")
