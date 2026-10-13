#include "labmate_onewire_session.h"
#include <string.h>

LabMateOneWireGate labmate_onewire_environment_check(const LabMateOneWireEnvironment* e) {
    if(!e || e->arbiter != LabMateOneWireArbiterAtomicLeaseSupported)
        return LabMateOneWireGateNoArbiter;
    if(e->voltage != LabMateOneWireVoltageVerified3V3)
        return LabMateOneWireGateUnsafeVoltage;
    if(e->auto_power_requested || e->parasite_power_requested)
        return LabMateOneWireGateUnsafePower;
    /* LabMate PC0/PC1 have pre-existing pulse, monitor and I2C uses.
     * Restrict model to PB14; still cannot reserve it without real arbiter. */
    if(e->pin != LabMateOneWirePinIbButtonPb14)
        return LabMateOneWireGateUnsupportedPin;
    if(e->capture_active || e->gpio_monitor_active || e->pwm_running ||
       e->ibutton_active || e->expansion_connected || e->other_owner_unknown)
        return LabMateOneWireGateResourceBusy;
    return LabMateOneWireGateModelEligible;
}

void labmate_onewire_session_init(LabMateOneWireSession* s) {
    if(s) memset(s, 0, sizeof(*s));
}

bool labmate_onewire_session_active(const LabMateOneWireSession* s) {
    if(!s) return false;
    return s->state == LabMateOneWireSessionAwaitLease ||
           s->state == LabMateOneWireSessionReady ||
           s->state == LabMateOneWireSessionAwaitOperation ||
           s->state == LabMateOneWireSessionAwaitRelease;
}

bool labmate_onewire_session_can_exit(const LabMateOneWireSession* s) {
    return s && !labmate_onewire_session_active(s) && !s->lease_held;
}

bool labmate_onewire_session_begin(
    LabMateOneWireSession* s,
    const LabMateOneWireEnvironment* e,
    uint32_t* generation) {
    if(!s || !generation || labmate_onewire_environment_check(e) !=
       LabMateOneWireGateModelEligible ||
       labmate_onewire_session_active(s) || s->lease_held)
        return false;
    if(s->state != LabMateOneWireSessionIdle &&
       s->state != LabMateOneWireSessionCompleted &&
       s->state != LabMateOneWireSessionCancelled &&
       s->state != LabMateOneWireSessionFailed)
        return false;
    /* Saturation prevents silent token reuse after 2^32-1 sessions. */
    if(s->generation == UINT32_MAX) return false;
    ++s->generation;
    s->stop_requested = false;
    s->error_pending = false;
    s->state = LabMateOneWireSessionAwaitLease;
    *generation = s->generation;
    return true;
}

bool labmate_onewire_session_stop(LabMateOneWireSession* s) {
    if(!s || !labmate_onewire_session_active(s)) return false;
    s->stop_requested = true;
    if(s->state == LabMateOneWireSessionReady)
        s->state = LabMateOneWireSessionAwaitRelease;
    /* AwaitLease stays pending; operation-in-flight must finish before release. */
    return true;
}

bool labmate_onewire_session_lease_done(
    LabMateOneWireSession* s, uint32_t token, bool granted) {
    if(!s || token != s->generation ||
       s->state != LabMateOneWireSessionAwaitLease || s->lease_held)
        return false;
    if(!granted) {
        s->state = s->stop_requested ? LabMateOneWireSessionCancelled :
                                          LabMateOneWireSessionFailed;
        return true;
    }
    s->lease_held = true;
    s->state = s->stop_requested ?
                   LabMateOneWireSessionAwaitRelease : LabMateOneWireSessionReady;
    return true;
}

bool labmate_onewire_session_operation_begin(LabMateOneWireSession* s) {
    if(!s || s->state != LabMateOneWireSessionReady || !s->lease_held ||
       s->stop_requested)
        return false;
    s->state = LabMateOneWireSessionAwaitOperation;
    return true;
}

bool labmate_onewire_session_operation_done(
    LabMateOneWireSession* s, uint32_t token, bool succeeded) {
    if(!s || token != s->generation ||
       s->state != LabMateOneWireSessionAwaitOperation || !s->lease_held)
        return false;
    if(!succeeded) s->error_pending = true;
    s->state = (s->stop_requested || s->error_pending) ?
                   LabMateOneWireSessionAwaitRelease : LabMateOneWireSessionReady;
    return true;
}

bool labmate_onewire_session_finish(LabMateOneWireSession* s) {
    if(!s || s->state != LabMateOneWireSessionReady || !s->lease_held ||
       s->stop_requested)
        return false;
    s->state = LabMateOneWireSessionAwaitRelease;
    return true;
}

bool labmate_onewire_session_release_done(LabMateOneWireSession* s, uint32_t token) {
    if(!s || token != s->generation ||
       s->state != LabMateOneWireSessionAwaitRelease || !s->lease_held)
        return false;
    s->lease_held = false;
    s->state = s->error_pending ? LabMateOneWireSessionFailed :
               s->stop_requested ? LabMateOneWireSessionCancelled :
                                   LabMateOneWireSessionCompleted;
    return true;
}
