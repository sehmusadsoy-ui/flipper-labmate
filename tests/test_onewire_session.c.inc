/* Pure, mock-owner model only. NEVER exercises real PB14, OTG or 1-Wire. */
#include "labmate_onewire_session.h"
#include <assert.h>
#include <stdio.h>

static LabMateOneWireEnvironment eligible_mock(void) {
    LabMateOneWireEnvironment e = {0};
    e.pin = LabMateOneWirePinIbButtonPb14;
    e.voltage = LabMateOneWireVoltageVerified3V3;
    /* This is a MOCK certificate. Actual Momentum arbiter NOT verified. */
    e.arbiter = LabMateOneWireArbiterAtomicLeaseSupported;
    return e;
}

static void test_reject_uncertain_environment(void) {
    LabMateOneWireEnvironment e = eligible_mock();
    LabMateOneWireSession s;
    uint32_t token = 777U;
    labmate_onewire_session_init(&s);
    assert(labmate_onewire_environment_check(NULL) == LabMateOneWireGateNoArbiter);
    assert(labmate_onewire_environment_check(&e) == LabMateOneWireGateModelEligible);
    assert(!labmate_onewire_session_begin(NULL, &e, &token));
    assert(!labmate_onewire_session_begin(&s, NULL, &token));
    assert(!labmate_onewire_session_begin(&s, &e, NULL));
    assert(!labmate_onewire_session_active(NULL));
    assert(!labmate_onewire_session_can_exit(NULL));

    e.arbiter = LabMateOneWireArbiterUnknown;
    assert(labmate_onewire_environment_check(&e) == LabMateOneWireGateNoArbiter);
    assert(!labmate_onewire_session_begin(&s, &e, &token));
    assert(token == 777U && s.state == LabMateOneWireSessionIdle);
    e.arbiter = LabMateOneWireArbiterUnavailable;
    assert(labmate_onewire_environment_check(&e) == LabMateOneWireGateNoArbiter);
    e = eligible_mock();

    e.voltage = LabMateOneWireVoltageUnknown;
    assert(labmate_onewire_environment_check(&e) == LabMateOneWireGateUnsafeVoltage);
    e.voltage = LabMateOneWireVoltageUnsafe;
    assert(labmate_onewire_environment_check(&e) == LabMateOneWireGateUnsafeVoltage);
    e = eligible_mock();

    e.auto_power_requested = true;
    assert(labmate_onewire_environment_check(&e) == LabMateOneWireGateUnsafePower);
    e = eligible_mock();
    e.parasite_power_requested = true;
    assert(labmate_onewire_environment_check(&e) == LabMateOneWireGateUnsafePower);
    e = eligible_mock();

    const LabMateOneWirePin rejected[] = {
        LabMateOneWirePinUnknown, LabMateOneWirePinPc0,
        LabMateOneWirePinPc1, LabMateOneWirePinOther
    };
    for(unsigned i = 0U; i < sizeof(rejected)/sizeof(rejected[0]); ++i) {
        e.pin = rejected[i];
        assert(labmate_onewire_environment_check(&e) == LabMateOneWireGateUnsupportedPin);
        assert(!labmate_onewire_session_begin(&s, &e, &token));
    }
    e = eligible_mock();
    e.capture_active = true;
    assert(labmate_onewire_environment_check(&e) == LabMateOneWireGateResourceBusy);
    e = eligible_mock(); e.gpio_monitor_active = true;
    assert(labmate_onewire_environment_check(&e) == LabMateOneWireGateResourceBusy);
    e = eligible_mock(); e.pwm_running = true;
    assert(labmate_onewire_environment_check(&e) == LabMateOneWireGateResourceBusy);
    e = eligible_mock(); e.ibutton_active = true;
    assert(labmate_onewire_environment_check(&e) == LabMateOneWireGateResourceBusy);
    e = eligible_mock(); e.expansion_connected = true;
    assert(labmate_onewire_environment_check(&e) == LabMateOneWireGateResourceBusy);
    e = eligible_mock(); e.other_owner_unknown = true;
    assert(labmate_onewire_environment_check(&e) == LabMateOneWireGateResourceBusy);
    assert(s.generation == 0U && s.state == LabMateOneWireSessionIdle);
}

static void test_stop_while_awaiting_mock_lease(void) {
    LabMateOneWireSession s;
    uint32_t token = 0U, bad = 0U;
    LabMateOneWireEnvironment e = eligible_mock();
    labmate_onewire_session_init(&s);
    assert(labmate_onewire_session_can_exit(&s));
    assert(labmate_onewire_session_begin(&s, &e, &token));
    assert(token != 0U && s.state == LabMateOneWireSessionAwaitLease);
    assert(!labmate_onewire_session_can_exit(&s));
    assert(!labmate_onewire_session_begin(&s, &e, &bad));
    assert(!labmate_onewire_session_operation_begin(&s));
    assert(!labmate_onewire_session_finish(&s));
    assert(!labmate_onewire_session_release_done(&s, token));
    assert(labmate_onewire_session_stop(&s));
    assert(s.stop_requested && s.state == LabMateOneWireSessionAwaitLease);
    assert(labmate_onewire_session_stop(&s)); /* Idempotent pending STOP. */
    assert(!labmate_onewire_session_lease_done(&s, token+1U, true));
    assert(labmate_onewire_session_lease_done(&s, token, true));
    assert(s.state == LabMateOneWireSessionAwaitRelease && s.lease_held);
    assert(!labmate_onewire_session_can_exit(&s));
    assert(!labmate_onewire_session_operation_begin(&s));
    assert(!labmate_onewire_session_begin(&s, &e, &bad));
    assert(labmate_onewire_session_release_done(&s, token));
    assert(s.state == LabMateOneWireSessionCancelled && !s.lease_held);
    assert(labmate_onewire_session_can_exit(&s));
    assert(!labmate_onewire_session_release_done(&s, token));
    assert(labmate_onewire_session_begin(&s, &e, &bad));
    assert(bad != token);
    assert(!labmate_onewire_session_lease_done(&s, token, true));
    assert(labmate_onewire_session_stop(&s));
    assert(labmate_onewire_session_lease_done(&s, bad, false));
    assert(s.state == LabMateOneWireSessionCancelled && labmate_onewire_session_can_exit(&s));
}

static void test_inflight_stop_and_error(void) {
    LabMateOneWireSession s;
    LabMateOneWireEnvironment e = eligible_mock();
    uint32_t token;
    labmate_onewire_session_init(&s);
    assert(labmate_onewire_session_begin(&s, &e, &token));
    assert(labmate_onewire_session_lease_done(&s, token, true));
    assert(s.state == LabMateOneWireSessionReady);
    assert(labmate_onewire_session_operation_begin(&s));
    assert(s.state == LabMateOneWireSessionAwaitOperation);
    assert(!labmate_onewire_session_operation_begin(&s));
    assert(!labmate_onewire_session_finish(&s));
    assert(labmate_onewire_session_stop(&s));
    assert(s.state == LabMateOneWireSessionAwaitOperation && s.lease_held);
    assert(!labmate_onewire_session_can_exit(&s));
    assert(!labmate_onewire_session_operation_done(&s, token+1U, true));
    assert(labmate_onewire_session_operation_done(&s, token, true));
    assert(s.state == LabMateOneWireSessionAwaitRelease && s.lease_held);
    assert(!labmate_onewire_session_operation_begin(&s));
    assert(labmate_onewire_session_release_done(&s, token));
    assert(s.state == LabMateOneWireSessionCancelled);

    assert(labmate_onewire_session_begin(&s, &e, &token));
    assert(labmate_onewire_session_lease_done(&s, token, true));
    assert(labmate_onewire_session_operation_begin(&s));
    assert(labmate_onewire_session_operation_done(&s, token, false));
    assert(s.error_pending && s.state == LabMateOneWireSessionAwaitRelease);
    assert(!labmate_onewire_session_can_exit(&s));
    assert(labmate_onewire_session_release_done(&s, token));
    assert(s.state == LabMateOneWireSessionFailed && labmate_onewire_session_can_exit(&s));
}

static void test_finish_restart_and_token_saturation(void) {
    LabMateOneWireSession s;
    LabMateOneWireEnvironment e = eligible_mock();
    uint32_t token=0U, next=0U;
    labmate_onewire_session_init(&s);
    assert(labmate_onewire_session_begin(&s, &e, &token));
    assert(labmate_onewire_session_lease_done(&s, token, true));
    assert(labmate_onewire_session_operation_begin(&s));
    assert(labmate_onewire_session_operation_done(&s, token, true));
    assert(s.state == LabMateOneWireSessionReady);
    assert(labmate_onewire_session_finish(&s));
    assert(s.state == LabMateOneWireSessionAwaitRelease);
    assert(!labmate_onewire_session_can_exit(&s));
    assert(labmate_onewire_session_release_done(&s, token));
    assert(s.state == LabMateOneWireSessionCompleted);
    assert(labmate_onewire_session_can_exit(&s));
    assert(!labmate_onewire_session_stop(&s));
    assert(labmate_onewire_session_begin(&s, &e, &next) && next != token);
    assert(labmate_onewire_session_lease_done(&s, next, false));
    assert(s.state == LabMateOneWireSessionFailed);
    assert(labmate_onewire_session_can_exit(&s));
    assert(!labmate_onewire_session_operation_done(&s, token, true));
    assert(!labmate_onewire_session_release_done(&s, token));

    s.generation = UINT32_MAX;
    assert(!labmate_onewire_session_begin(&s, &e, &next));
    assert(s.state == LabMateOneWireSessionFailed);
}

int main(void) {
    test_reject_uncertain_environment();
    test_stop_while_awaiting_mock_lease();
    test_inflight_stop_and_error();
    test_finish_restart_and_token_saturation();
    puts("1-Wire W2 HOST lease model: deny unknown, no auto power, late lease STOP, confirm release, stale events PASS");
    return 0;
}
