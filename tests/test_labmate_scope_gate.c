#include "labmate_scope_gate.h"
#include <assert.h>
#include <stdio.h>

static LabMateScopePc1Environment ready(void) {
    return (LabMateScopePc1Environment){
        .selected_pin = LABMATE_MONITOR_PC1_INDEX,
        .firmware_lease_api = true,
        .firmware_try_callback = true,
    };
}
static void check_refusal_matrix(void) {
    LabMateScopeOwnerState s = {0};
    LabMateScopePc1Environment c = ready();
    assert(labmate_scope_gate_pc1(&c, &s) == LabMateScopeGateReady);
    assert(labmate_scope_gate_pc1(NULL, &s) == LabMateScopeGateInvalid);
    assert(labmate_scope_gate_pc1(&c, NULL) == LabMateScopeGateInvalid);
    for(unsigned pin = 0; pin < 8; ++pin) {
        c.selected_pin = pin;
        assert(labmate_scope_gate_pc1(&c, &s) ==
               (pin == 1 ? LabMateScopeGateReady : LabMateScopeGateBusy));
    }
    /* Scope must have its OWN owner; it cannot alias FrequencyLow. */
    assert(labmate_capture_pin_allowed(LabMateCaptureScope, 1U));
    for(uint8_t pin = 0; pin < 8U; ++pin) {
        assert(labmate_capture_pin_allowed(LabMateCaptureScope, pin) == (pin == 1U));
        assert(labmate_capture_can_acquire(
            LabMateCaptureNone, LabMateCaptureScope, pin,
            false, false, false) == (pin == 1U));
    }
    assert(labmate_capture_owner_after_stop(
        LabMateCaptureFrequencyLow, LabMateCaptureScope) == LabMateCaptureFrequencyLow);
    assert(labmate_capture_owner_after_stop(
        LabMateCaptureScope, LabMateCaptureScope) == LabMateCaptureNone);
    c.selected_pin = 8;
    assert(labmate_scope_gate_pc1(&c, &s) == LabMateScopeGateInvalid);
    c = ready(); c.firmware_lease_api = false;
    assert(labmate_scope_gate_pc1(&c, &s) == LabMateScopeGateUnsupported);
    c = ready(); c.firmware_try_callback = false;
    assert(labmate_scope_gate_pc1(&c, &s) == LabMateScopeGateUnsupported);
    c = ready(); c.comm_owner = LabMateCommI2c3;
    assert(labmate_scope_gate_pc1(&c, &s) == LabMateScopeGateBusy);
    c.comm_owner = LabMateCommOneWirePa4;
    assert(labmate_scope_gate_pc1(&c, &s) == LabMateScopeGateBusy);
    c = ready();
    for(int owner = LabMateCaptureFrequencyLow; owner <= LabMateCaptureScope; ++owner) {
        c.capture_owner = (LabMateCaptureOwner)owner;
        assert(labmate_scope_gate_pc1(&c, &s) == LabMateScopeGateBusy);
    }
#define EXPECT_BUSY(member) do { c = ready(); c.member = true; \
    assert(labmate_scope_gate_pc1(&c, &s) == LabMateScopeGateBusy); } while(0)
    EXPECT_BUSY(frequency_irq_active);
    EXPECT_BUSY(frequency_hw_active);
    EXPECT_BUSY(pulse_irq_active);
    EXPECT_BUSY(counter_active);
    EXPECT_BUSY(button_active);
    EXPECT_BUSY(monitor_active);
    EXPECT_BUSY(logger_active);
    EXPECT_BUSY(uart_active);
#undef EXPECT_BUSY
    c = ready(); c.capture_release_fault = true;
    assert(labmate_scope_gate_pc1(&c, &s) == LabMateScopeGateFault);
    c = ready(); c.monitor_release_fault = true;
    assert(labmate_scope_gate_pc1(&c, &s) == LabMateScopeGateFault);
    c = ready(); s.handle = 77;
    assert(labmate_scope_gate_pc1(&c, &s) == LabMateScopeGateBusy);
    assert(s.handle == 77 && s.phase == LabMateScopeOwnerIdle);
}
static void check_ordered_start_and_stop(void) {
    LabMateScopeOwnerState s = {0};
    LabMateScopePc1Environment c = ready();
    assert(!labmate_scope_owner_lease_acquired(&s, 0));
    assert(!labmate_scope_owner_started(&s));
    LabMateScopeReleasePlan p = labmate_scope_owner_stop_plan(&s);
    assert(!p.detach_callback && !p.restore_pin && !p.release_lease);
    assert(!labmate_scope_owner_stop_confirmed(&s, true, true, true));
    assert(labmate_scope_owner_lease_acquired(&s, 5));
    assert(!labmate_scope_owner_lease_acquired(&s, 99));
    assert(labmate_scope_gate_pc1(&c, &s) == LabMateScopeGateBusy);
    p = labmate_scope_owner_stop_plan(&s);
    assert(!p.detach_callback && !p.restore_pin && p.release_lease);
    assert(!labmate_scope_owner_pin_configured(&s));
    assert(labmate_scope_owner_callback_added(&s));
    p = labmate_scope_owner_stop_plan(&s);
    assert(p.detach_callback && !p.restore_pin && p.release_lease);
    assert(!labmate_scope_owner_started(&s));
    assert(labmate_scope_owner_pin_configured(&s));
    assert(labmate_scope_owner_started(&s));
    assert(!labmate_scope_owner_started(&s));
    p = labmate_scope_owner_stop_plan(&s);
    assert(p.detach_callback && p.restore_pin && p.release_lease);
    /* Callback removed and pin restored, but native lease release failed:
     * the next STOP plan must NOT touch callback/pin a second time. */
    LabMateScopeOwnerState retry = {0};
    assert(labmate_scope_owner_lease_acquired(&retry, 80));
    assert(labmate_scope_owner_callback_added(&retry));
    assert(labmate_scope_owner_pin_configured(&retry));
    assert(!labmate_scope_owner_stop_confirmed(&retry, true, true, false));
    LabMateScopeReleasePlan remaining = labmate_scope_owner_stop_plan(&retry);
    assert(!remaining.detach_callback && !remaining.restore_pin && remaining.release_lease);
    assert(labmate_scope_owner_stop_confirmed(&retry, false, false, true));
    assert(retry.handle == 0 && retry.phase == LabMateScopeOwnerIdle);
    assert(labmate_scope_owner_stop_confirmed(&s, true, true, true));
    assert(s.phase == LabMateScopeOwnerIdle && s.handle == 0);
    assert(labmate_scope_gate_pc1(&c, &s) == LabMateScopeGateReady);
    assert(!labmate_scope_owner_stop_confirmed(&s, true, true, true));
}
static void check_rollback_and_sticky_fault(void) {
    LabMateScopeOwnerState s = {0};
    LabMateScopePc1Environment c = ready();
    assert(labmate_scope_owner_lease_acquired(&s, 19));
    assert(labmate_scope_owner_stop_confirmed(&s, false, false, true));
    assert(s.handle == 0 && s.phase == LabMateScopeOwnerIdle); /* failed callback, lease released */
    assert(labmate_scope_owner_lease_acquired(&s, 20));
    assert(!labmate_scope_owner_stop_confirmed(&s, false, false, false));
    LabMateScopeReleasePlan lease_only = labmate_scope_owner_stop_plan(&s);
    assert(!lease_only.detach_callback && !lease_only.restore_pin && lease_only.release_lease);
    assert(labmate_scope_owner_stop_confirmed(&s, false, false, true));
    assert(s.handle == 0 && s.phase == LabMateScopeOwnerIdle);
    assert(s.fault_cleanup_phase == LabMateScopeOwnerIdle);
    assert(labmate_scope_owner_lease_acquired(&s, 21));
    assert(labmate_scope_owner_callback_added(&s));
    assert(labmate_scope_owner_pin_configured(&s));
    assert(!labmate_scope_owner_stop_confirmed(&s, false, true, true));
    assert(s.handle == 21 && s.phase == LabMateScopeOwnerReleaseFault);
    assert(labmate_scope_gate_pc1(&c, &s) == LabMateScopeGateFault);
    assert(!labmate_scope_owner_lease_acquired(&s, 22));
    assert(!labmate_scope_owner_callback_added(&s));
    assert(!labmate_scope_owner_stop_confirmed(&s, true, false, true));
    assert(s.handle == 21);
    assert(labmate_scope_owner_stop_confirmed(&s, true, true, true));
    assert(s.phase == LabMateScopeOwnerIdle && s.handle == 0);
}
int main(void) {
    check_refusal_matrix();
    check_ordered_start_and_stop();
    check_rollback_and_sticky_fault();
    puts("v1.9 Scope PC1 preflight and STOP/BACK state model PASS");
    return 0;
}
