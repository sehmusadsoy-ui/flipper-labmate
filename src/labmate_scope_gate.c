#include "labmate_scope_gate.h"

LabMateScopeGate labmate_scope_gate_pc1(
    const LabMateScopePc1Environment* e, const LabMateScopeOwnerState* s) {
    /* The native IRQ driver is hard-wired to PC1/EXTI1. Never approve a
     * different pin index and then configure PC1 behind the caller's back. */
    if(!e || !s || e->selected_pin != LABMATE_MONITOR_PC1_INDEX)
        return LabMateScopeGateInvalid;
    if(e->capture_release_fault || e->monitor_release_fault ||
       s->phase == LabMateScopeOwnerReleaseFault ||
       s->fault_cleanup_phase != LabMateScopeOwnerIdle ||
       s->callback_detached || s->pin_restored)
        return LabMateScopeGateFault;
    if(!e->firmware_lease_api || !e->firmware_try_callback)
        return LabMateScopeGateUnsupported;
    if(s->phase != LabMateScopeOwnerIdle || s->handle ||
       e->comm_owner != LabMateCommNone || e->monitor_active ||
       e->logger_active || e->uart_active || e->counter_active || e->button_active ||
       !labmate_capture_can_acquire(
           e->capture_owner, LabMateCaptureScope, e->selected_pin,
           e->frequency_irq_active, e->frequency_hw_active, e->pulse_irq_active))
        return LabMateScopeGateBusy;
    /* Scope is an independent, append-only capture owner on PC1/EXTI1. */
    return LabMateScopeGateReady;
}

bool labmate_scope_owner_lease_acquired(LabMateScopeOwnerState* s, uint32_t h) {
    if(!s || s->phase != LabMateScopeOwnerIdle || s->handle || !h) return false;
    s->handle = h;
    s->phase = LabMateScopeOwnerLease;
    s->callback_detached = false;
    s->pin_restored = false;
    s->fault_cleanup_phase = LabMateScopeOwnerIdle;
    return true;
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
    /* Remember the precise hardware stages confirmed before the fault.
     * Never remove a callback or restore a pin that this owner did not set. */
    LabMateScopeOwnerPhase owned = s->phase == LabMateScopeOwnerReleaseFault
                                   ? s->fault_cleanup_phase : s->phase;
    if(owned == LabMateScopeOwnerLease)
        return (LabMateScopeReleasePlan){false, false, true};
    if(owned == LabMateScopeOwnerCallback)
        return (LabMateScopeReleasePlan){!s->callback_detached, false, true};
    if(owned == LabMateScopeOwnerPinConfigured || owned == LabMateScopeOwnerRunning)
        return (LabMateScopeReleasePlan){!s->callback_detached, !s->pin_restored, true};
    return no; /* Unknown state: do not touch any foreign peripheral. */
}
bool labmate_scope_owner_stop_confirmed(
    LabMateScopeOwnerState* s, bool callback_removed,
    bool pin_restored, bool lease_released) {
    if(!s || !s->handle || s->phase == LabMateScopeOwnerIdle) return false;
    LabMateScopeReleasePlan p = labmate_scope_owner_stop_plan(s);
    /* Positive acknowledgements persist across partial STOP failures. A
     * later recovery plan can never detach an already-removed callback or
     * restore a pin already handed back to the firmware. */
    if(p.detach_callback && callback_removed) s->callback_detached = true;
    if(p.restore_pin && pin_restored && (!p.detach_callback || callback_removed))
        s->pin_restored = true;
    if(!p.release_lease || (p.detach_callback && !callback_removed) ||
       (p.restore_pin && !pin_restored) || !lease_released) {
        if(s->phase != LabMateScopeOwnerReleaseFault)
            s->fault_cleanup_phase = s->phase;
        s->phase = LabMateScopeOwnerReleaseFault;
        return false;
    }
    s->handle = 0U;
    s->phase = LabMateScopeOwnerIdle;
    s->fault_cleanup_phase = LabMateScopeOwnerIdle;
    s->callback_detached = false;
    s->pin_restored = false;
    return true;
}
