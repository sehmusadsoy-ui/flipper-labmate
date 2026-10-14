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

# The decoder stays pure even after adding a real hardware-backed app.
hw = (root / "src/labmate_onewire_hw.c").read_text()
input_src = (root / "src/labmate_input_onewire.c").read_text()
menu = (root / "src/labmate_navigation.c").read_text()
for required in (
    "onewire_host_alloc(&gpio_ext_pa4)", "onewire_host_start(s->host);",
    "onewire_host_reset(s->host)", "onewire_host_write(s->host, LABMATE_1W_CONVERT)",
    "onewire_host_read_bytes(s->host, bytes, sizeof(bytes))",
    "labmate_onewire_ds18b20_decode(bytes, sizeof(bytes), true, &temp)",
    "onewire_host_stop(s->host)", "onewire_host_free(s->host)",
    "labmate_comm_local_release(s->owner, LabMateCommOneWirePa4)",
):
    assert required in hw, required
for forbidden in ("power_enable_otg(", "gpio_ibutton", "gpio_ext_pb14",
                  "furi_hal_power_enable_otg"):
    assert forbidden not in hw, f"Forbidden automatic power/shared pin: {forbidden}"
assert "event.key == InputKeyOk" in input_src
assert "event.key == InputKeyBack" in input_src
assert "labmate_onewire_hw_stop(&app->thermometer);" in input_src
assert '"1-Wire Temp"' in menu
assert "LabMateToolOneWire" in (root / "src/labmate_navigation.h").read_text()
print("1-Wire DS18B20 real PA4 reader wiring, stop and codec isolation PASS (SDK/host only)")
