#!/usr/bin/env python3
"""W2 HAL-free mock lease model ONLY; no production atomic GPIO arbiter verified."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
head = (root / "src/labmate_onewire_session.h").read_text()
src = (root / "src/labmate_onewire_session.c").read_text()
tests = (root / "tests/test_onewire_session.c.inc").read_text()
for blocked in (
    "furi_", "Furi", "onewire_host_", "furi_hal_", "power_enable_",
    "gpio_", "Gpio", "canvas_", "storage_", "pthread_", "furi_mutex_",
    "furi_thread_", "FuriWaitForever", "furi_delay_",
):
    assert blocked not in src, f"Forbidden runtime/hardware call in mock model: {blocked}"
for required in (
    "LabMateOneWireArbiterUnknown",
    "LabMateOneWireArbiterUnavailable",
    "LabMateOneWireArbiterAtomicLeaseSupported",
    "LabMateOneWireVoltageVerified3V3",
    "LabMateOneWirePinIbButtonPb14",
    "LabMateOneWireSessionAwaitLease",
    "LabMateOneWireSessionAwaitOperation",
    "LabMateOneWireSessionAwaitRelease",
    "lease_held",
    "stop_requested",
):
    assert required in head, required
for required in (
    "e->arbiter != LabMateOneWireArbiterAtomicLeaseSupported",
    "e->voltage != LabMateOneWireVoltageVerified3V3",
    "e->auto_power_requested || e->parasite_power_requested",
    "e->pin != LabMateOneWirePinIbButtonPb14",
    "e->capture_active || e->gpio_monitor_active || e->pwm_running",
    "e->ibutton_active || e->expansion_connected || e->other_owner_unknown",
    "s->state == LabMateOneWireSessionAwaitLease",
    "s->state = LabMateOneWireSessionAwaitRelease",
    "s->lease_held = false;",
    "if(s->generation == UINT32_MAX) return false;",
):
    assert required in src, required
for required in (
    "test_reject_uncertain_environment();",
    "test_stop_while_awaiting_mock_lease();",
    "test_inflight_stop_and_error();",
    "test_finish_restart_and_token_saturation();",
):
    assert required in tests, required
production = "".join((root / "src" / name).read_text() for name in (
    "labmate.c", "labmate_navigation.h", "labmate_input_menu.c", "labmate_view.c"
))
assert "labmate_onewire_session_begin(" not in production
assert "LabMateToolOneWire" not in production
print("1-Wire W2 mock model isolated and fail-closed: PASS (HOST ONLY)")
