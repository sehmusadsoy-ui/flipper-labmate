#!/usr/bin/env python3
"""Fail closed: v1.8 1-Wire W2 GPIO owner NOT VERIFIED.

A separately reviewed resource/ownership gate is required before any
production app may invoke the Momentum 1-Wire host or modify PB14.
This guard is not a GPIO arbiter and proves only static non-integration.
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
source_dir = root / "src"
app_manifest = (root / "application.fam").read_text()

# HAL-free feature code is compiled into the ordinary development FAP by
# sources=["src/*.c"], but its address/lease models MUST remain unreachable.
assert 'sources=["src/*.c"]' in app_manifest

model_sources = (
    source_dir / "labmate_onewire_ds18b20.c",
    source_dir / "labmate_onewire_session.c",
)
for path in model_sources:
    code = path.read_text()
    for blocked in (
        "#include <one_wire/", "onewire_host_", "power_enable_otg(",
        "furi_hal_gpio_init(", "furi_hal_ibutton_pin_configure(",
        "furi_hal_ibutton_pin_write(", "furi_hal_rfid_",
    ):
        assert blocked not in code, f"Unexpected 1-Wire model hardware call {path}: {blocked}"

# Production app must not reach these models, nor introduce a hidden
# GPIO-facing OneWire backend. Permit no probe or preview source in src/.
app_files = sorted(source_dir.glob("*.c")) + sorted(source_dir.glob("*.h"))
assert not any("onewire_probe" in p.name or "onewire_worker" in p.name for p in app_files)
pure_models = {p.name for p in model_sources}
pure_models.add("labmate_onewire_ds18b20.h")
pure_models.add("labmate_onewire_session.h")
for path in app_files:
    if path.name in pure_models:
        continue
    code = path.read_text()
    for pattern in (
        r"\bonewire_host_(alloc|free|start|stop|reset|write|read|search)\b",
        r"\blabmate_onewire_session_begin\s*\(",
        r"\blabmate_onewire_ds18b20_decode\s*\(",
        r"\bLabMateToolOneWire\b",
        r"\bLabMateScreenOneWire\b",
        r"\bfuri_hal_ibutton_pin_configure\s*\(",
    ):
        assert not re.search(pattern, code), f"W2 BLOCKED: forbidden {path} -> {pattern}"

# A hypothetical test enum is NOT an actual owner acquisition, and must
# never be assigned in the coordinator from an app-local availability guess.
app_entry = (source_dir / "labmate.c").read_text()
assert "LabMateOneWireArbiterAtomicLeaseSupported" not in app_entry
print("W2 real 1-Wire GPIO integration remains DISABLED: static fail-closed guard PASS")
