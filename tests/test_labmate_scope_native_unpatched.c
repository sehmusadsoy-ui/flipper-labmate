/* A mismatched/ordinary Momentum SDK must never use the legacy
 * assert-register IRQ API or touch any GPIO/EXTI register.
 * Compile with -DLABMATE_SCOPE_TEST_UNPATCHED.
 */
#include "labmate_scope_native.h"
#include "mock_runtime.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    static LabMateScopeNative s;
    LabMateCaptureOwner owner = LabMateCaptureNone;
    LabMateScopePc1Environment env = {
        .selected_pin = LABMATE_MONITOR_PC1_INDEX,
        .capture_owner = LabMateCaptureNone,
        .firmware_lease_api = false,
        .firmware_try_callback = false,
    };
    labmate_mock_reset();
    assert(labmate_scope_native_init(&s));
    assert(labmate_scope_native_start(&s, &env, &owner, 0) ==
           LabMateScopeNativeUnsupported);
    assert(owner == LabMateCaptureNone && !s.active);
    assert(labmate_mock_hal.held_handle == 0U);
    assert(labmate_mock_hal.gpio_writes == 0U);
    assert(labmate_mock_hal.exti_writes == 0U);
    assert(labmate_mock_hal.callback_removes == 0U);
    assert(!labmate_mock_hal.callback);
    puts("v1.9 unpatched-Momentum fail-closed IRQ test PASS");
    return 0;
}
