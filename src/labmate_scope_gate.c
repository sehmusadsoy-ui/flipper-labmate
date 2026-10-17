#include "labmate_scope_gate.h"

LabMateScopeGate labmate_scope_gate_pc1(
    const LabMateScopePc1Environment* e, const LabMateScopeOwnerState* s) {
    if(!e || !s || e->selected_pin >= LABMATE_MONITOR_PIN_COUNT)
        return LabMateScopeGateInvalid;
    if(e->capture_release_fault || e->monitor_release_fault ||
       s->phase == LabMateScopeOwnerReleaseFault) return LabMateScopeGateFault;
    if(!e->firmware_lease_api || !e->firmware_try_callback)
        return LabMateScopeGateUnsupported;
    if(s->phase != LabMateScopeOwnerIdle || s->handle ||
       e->comm_owner != LabMateCommNone || e->monitor_active ||
       e->logger_active || e->uart_active || e->counter_active || e->button_active ||
       !labmate_capture_can_acquire(
           e->capture_owner, LabMateCaptureFrequencyLow, e->selected_pin,
           e->frequency_irq_active, e->frequency_hw_active, e->pulse_irq_active))
        return LabMateScopeGateBusy;
    /* FrequencyLow is the existing PC1 EXTI1 allowlist; a future Scope
     * enum/IRQ driver must only be added in a separate reviewed change. */
    return LabMateScopeGateReady;
}

bool labmate_scope_owner_lease_acquired(LabMateScopeOwnerState* s, uint32_t h) {
    if(!s || s->phase != LabMateScopeOwnerIdle || s->handle || !h) return false;
    s->handle = h; s->phase = LabMateScopeOwnerLease; return true;
}
bool labmate_scope_owner_callback_added(LabMateScopeOwnerState* s) {
    if(!s || !s->handle || s->phase != LabMateScopeOwnerLease) return false;
    s->phase = LabMateScopeOwnerCallback; return true;
}
bool labmate_scope_owner_pin_configured(LabMateScopeOwnerState* s) {
    if(!s || !s->handle || s->phase != LabMateScopeOwnerCallback) return false;
    s->phase = LabMateScopeOwnerPinConfigured; return true;
}
bool labmate_scope_owner_started(LabMateScopeOwnerState* s) {
    if(!s || !s->handle || s->phase != LabMateScopeOwnerPinConfigured) return false;
    s->phase = LabMateScopeOwnerRunning; return true;
}
LabMateScopeReleasePlan labmate_scope_owner_stop_plan(const LabMateScopeOwnerState* s) {
    LabMateScopeReleasePlan no = {0};
    if(!s || !s->handle || s->phase == LabMateScopeOwnerIdle) return no;
    if(s->phase == LabMateScopeOwnerLease)
        return (LabMateScopeReleasePlan){false, false, true};
    if(s->phase == LabMateScopeOwnerCallback)
        return (LabMateScopeReleasePlan){true, false, true};
    /* A fault retains a conservative stop plan, not a proof of recovery. */
    return (LabMateScopeReleasePlan){true, true, true};
}
bool labmate_scope_owner_stop_confirmed(
    LabMateScopeOwnerState* s, bool callback_removed,
    bool pin_restored, bool lease_released) {
    if(!s || !s->handle || s->phase == LabMateScopeOwnerIdle) return false;
    LabMateScopeReleasePlan p = labmate_scope_owner_stop_plan(s);
    if((p.detach_callback && !callback_removed) ||
       (p.restore_pin && !pin_restored) ||
       (p.release_lease && !lease_released)) {
        s->phase = LabMateScopeOwnerReleaseFault;
        return false;
    }
    s->handle = 0U; s->phase = LabMateScopeOwnerIdle; return true;
}
