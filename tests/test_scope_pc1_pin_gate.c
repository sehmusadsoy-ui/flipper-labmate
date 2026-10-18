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
    puts("scope PC1 pin gate: PASS");
    return 0;
}
