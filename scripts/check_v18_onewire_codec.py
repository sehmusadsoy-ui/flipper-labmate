#!/usr/bin/env python3
"""1-Wire DS18B20 pure codec boundary checks: no sensor hardware is exercised."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
source = (root / "src/labmate_onewire_ds18b20.c").read_text()
header = (root / "src/labmate_onewire_ds18b20.h").read_text()
tests = (root / "tests/test_onewire_ds18b20.c.inc").read_text()

for blocked in (
    "furi_", "Furi", "onewire_host_", "power_enable_", "gpio_", "Gpio",
    "canvas_", "storage_", "malloc(", "free(", "furi_delay_", "thread_",
):
    assert blocked not in source, f"Hardware/runtime dependency: {blocked}"

for required in (
    "LABMATE_ONEWIRE_SCRATCHPAD_SIZE 9U",
    "LabMateOneWireDecodeCrcMismatch",
    "LabMateOneWireDecodeConversionUnconfirmed",
    "LabMateOneWireDecodeOutOfRange",
    "power_on_candidate",
):
    assert required in header, required

for required in (
    "0x8CU",
    "0x9FU",
    "0x1FU",
    "resolution",
    "quantized",
    "if(!conversion_confirmed)",
    "memset(out, 0, sizeof(*out));",
):
    assert required in source, required

for required in (
    "test_crc_and_known_values();",
    "test_corruption_and_invalid_inputs();",
    "test_resolution_limits_and_sign();",
    "test_signed_rounding();",
):
    assert required in tests, required

# The planned sensor feature is not attached to app coordinator/menus.
production = "".join((root / "src" / name).read_text() for name in (
    "labmate.c", "labmate_navigation.h", "labmate_input_menu.c", "labmate_view.c"
))
assert "LabMateToolOneWire" not in production
assert "labmate_onewire_ds18b20_decode(" not in production
print("1-Wire DS18B20 pure codec isolation / unconfirmed-reading safety PASS")
