/* Host-only Scope PC1 pin-identity regression.
 * Build from repository root:
 * cc -std=c11 -Wall -Wextra -Werror -Isrc \
 *   tests/test_scope_pc1_pin_gate.c src/labmate_scope_gate.c \
 *   src/labmate_resource_policy.c -o /tmp/test_scope_pc1_pin_gate
 * /tmp/test_scope_pc1_pin_gate
 */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "labmate_scope_gate.h"

static void test_stale_direct_lease_rejected(void) {
    LabMateScopeOwnerState owner = {0};
    owner.callback_detached = true;
    assert(!labmate_scope_owner_lease_acquired(&owner, 41U));
    assert(owner.handle == 0U && owner.callback_detached);
    owner.callback_detached = false;
    owner.pin_restored = true;
    assert(!labmate_scope_owner_lease_acquired(&owner, 41U));
    assert(owner.handle == 0U && owner.pin_restored);
    owner.pin_restored = false;
    owner.fault_cleanup_phase = LabMateScopeOwnerRunning;
    assert(!labmate_scope_owner_lease_acquired(&owner, 41U));
    assert(owner.handle == 0U &&
           owner.fault_cleanup_phase == LabMateScopeOwnerRunning);
    owner.fault_cleanup_phase = LabMateScopeOwnerIdle;
    assert(!labmate_scope_owner_lease_acquired(&owner, 0U));
    assert(labmate_scope_owner_lease_acquired(&owner, 41U));
    assert(owner.handle == 41U && owner.phase == LabMateScopeOwnerLease);
}

static void test_lease_release_fail_closed(void) {
    LabMateScopeOwnerState owner = {0};
    assert(labmate_scope_owner_lease_acquired(&owner, 42U));
    assert(!labmate_scope_owner_lease_acquired(&owner, 43U));
    assert(labmate_scope_owner_callback_added(&owner));
    assert(labmate_scope_owner_pin_configured(&owner));
    assert(labmate_scope_owner_started(&owner));

    LabMateScopeReleasePlan plan = labmate_scope_owner_stop_plan(&owner);
    assert(plan.detach_callback && plan.restore_pin && plan.release_lease);

    /* Native STOP reports callback/pin removed but lease release refused. */
    assert(!labmate_scope_owner_stop_confirmed(&owner, true, true, false));
    assert(owner.phase == LabMateScopeOwnerReleaseFault);
    assert(owner.handle == 42U);
    plan = labmate_scope_owner_stop_plan(&owner);
    assert(!plan.detach_callback && !plan.restore_pin && plan.release_lease);

    /* Retry must ONLY release the outstanding matching lease. */
    assert(labmate_scope_owner_stop_confirmed(&owner, false, false, true));
    assert(owner.phase == LabMateScopeOwnerIdle && owner.handle == 0U);
    plan = labmate_scope_owner_stop_plan(&owner);
    assert(!plan.detach_callback && !plan.restore_pin && !plan.release_lease);
}

int main(void) {
    LabMateScopeOwnerState owner = {0};
    LabMateScopePc1Environment env = {
        .selected_pin = LABMATE_MONITOR_PC1_INDEX,
        .capture_owner = LabMateCaptureNone,
        .comm_owner = LabMateCommNone,
        .firmware_lease_api = true,
        .firmware_try_callback = true,
    };
    assert(labmate_scope_gate_pc1(&env, &owner) == LabMateScopeGateReady);

    /* All seven alternative valid monitor indices must fail closed. */
    for(uint8_t i = 0; i < LABMATE_MONITOR_PIN_COUNT; ++i) {
        if(i == LABMATE_MONITOR_PC1_INDEX) continue;
        env.selected_pin = i;
        assert(labmate_scope_gate_pc1(&env, &owner) == LabMateScopeGateInvalid);
        assert(owner.handle == 0 && owner.phase == LabMateScopeOwnerIdle);
    }
    env.selected_pin = UINT8_MAX;
    assert(labmate_scope_gate_pc1(&env, &owner) == LabMateScopeGateInvalid);

    env.selected_pin = LABMATE_MONITOR_PC1_INDEX;
    env.firmware_try_callback = false;
    assert(labmate_scope_gate_pc1(&env, &owner) == LabMateScopeGateUnsupported);
    env.firmware_try_callback = true;

    env.comm_owner = LabMateCommI2c3;
    assert(labmate_scope_gate_pc1(&env, &owner) == LabMateScopeGateBusy);
    env.comm_owner = LabMateCommNone;

    env.capture_release_fault = true;
    assert(labmate_scope_gate_pc1(&env, &owner) == LabMateScopeGateFault);
    env.capture_release_fault = false;

    /* A native owner with an IDLE phase but unfinished cleanup must never
     * be treated as available merely because its handle is zero. */
    owner.callback_detached = true;
    assert(labmate_scope_gate_pc1(&env, &owner) == LabMateScopeGateFault);
    owner.callback_detached = false;
    owner.pin_restored = true;
    assert(labmate_scope_gate_pc1(&env, &owner) == LabMateScopeGateFault);
    owner.pin_restored = false;
    owner.fault_cleanup_phase = LabMateScopeOwnerRunning;
    assert(labmate_scope_gate_pc1(&env, &owner) == LabMateScopeGateFault);
    owner.fault_cleanup_phase = LabMateScopeOwnerIdle;
    assert(labmate_scope_gate_pc1(&env, &owner) == LabMateScopeGateReady);

    test_stale_direct_lease_rejected();
    test_lease_release_fail_closed();
    puts("scope PC1 pin gate + ownership lifecycle: PASS");
    return 0;
}
