#include "labmate_scope_native.h"
#include "mock_runtime.h"
#include <assert.h>
#include <stdio.h>

static LabMateScopePc1Environment free_pc1(void) {
    return (LabMateScopePc1Environment){
        .selected_pin = LABMATE_MONITOR_PC1_INDEX,
        .capture_owner = LabMateCaptureNone,
        .comm_owner = LabMateCommNone,
        .firmware_lease_api = true,
        .firmware_try_callback = true,
    };
}
static void test_owned_capture_and_stop(void) {
    static LabMateScopeNative s;
    LabMateCaptureOwner owner = LabMateCaptureNone;
    labmate_mock_reset();
    assert(labmate_scope_native_init(&s));
    LabMateScopePc1Environment env = free_pc1();
    assert(labmate_scope_native_start(&s, &env, &owner, 100) == LabMateScopeNativeReady);
    assert(owner == LabMateCaptureScope && s.active);
    assert(labmate_mock_hal.held_handle == 5U);
    assert(labmate_mock_hal.gpio_writes == 1U && labmate_mock_hal.exti_writes == 1U);
    labmate_mock_edge(100, true);
    labmate_mock_edge(200, false);
    LabMateScopeEdge samples[4] = {0};
    uint16_t copied = 0;
    LabMateScopeSnapshot snapshot = labmate_scope_native_read(&s, samples, 4, &copied);
    assert(snapshot.count == 2U && copied == 2U);
    assert(samples[0].tick == 100U && samples[1].tick == 200U);
    assert(samples[1].delta_ticks == 100U && !samples[1].high);
    assert(labmate_scope_native_stop(&s, &owner));
    assert(owner == LabMateCaptureNone && !s.active);
    assert(labmate_mock_hal.held_handle == 0U);
    assert(!labmate_mock_hal.callback && !labmate_mock_hal.callback_enabled);
    assert(labmate_mock_hal.callback_removes == 1U);
    assert(labmate_mock_hal.gpio_writes == 2U);
    assert(labmate_mock_hal.exti_writes == 2U);
    assert(labmate_scope_native_stop(&s, &owner));
    assert(labmate_mock_hal.callback_removes == 1U); /* no second foreign release */
    assert(labmate_scope_native_init(&s)); /* legal after owned teardown */
    assert(labmate_scope_native_start(&s, &env, &owner, 200) == LabMateScopeNativeReady);
    assert(labmate_scope_native_stop(&s, &owner));
}
static void test_foreign_owner_and_callback_denials(void) {
    static LabMateScopeNative s;
    LabMateCaptureOwner owner = LabMateCaptureNone;
    LabMateScopePc1Environment env = free_pc1();
    labmate_mock_reset();
    assert(labmate_scope_native_init(&s));
    env.capture_owner = LabMateCaptureFrequencyLow; owner = env.capture_owner;
    assert(labmate_scope_native_start(&s, &env, &owner, 0) == LabMateScopeNativeBusy);
    assert(!labmate_mock_hal.held_handle && !labmate_mock_hal.gpio_writes);
    env = free_pc1(); owner = LabMateCaptureNone;
    labmate_mock_hal.lease_occupied = true;
    assert(labmate_scope_native_start(&s, &env, &owner, 0) == LabMateScopeNativeBusy);
    assert(!labmate_mock_hal.gpio_writes && !labmate_mock_hal.exti_writes);
    labmate_mock_hal.lease_occupied = false;
    labmate_mock_hal.foreign_callback = true;
    assert(labmate_scope_native_start(&s, &env, &owner, 0) == LabMateScopeNativeBusy);
    assert(!labmate_mock_hal.held_handle);
    assert(!labmate_mock_hal.gpio_writes && !labmate_mock_hal.exti_writes);
    assert(labmate_mock_hal.callback_removes == 0U);
    labmate_mock_hal.foreign_callback = false;
    env = free_pc1(); env.comm_owner = LabMateCommI2c3;
    assert(labmate_scope_native_start(&s, &env, &owner, 0) == LabMateScopeNativeBusy);
    assert(!labmate_mock_hal.gpio_writes && !labmate_mock_hal.exti_writes);
}
static void test_partial_release_and_clock_safety(void) {
    static LabMateScopeNative s;
    LabMateCaptureOwner owner = LabMateCaptureNone;
    LabMateScopePc1Environment env = free_pc1();
    labmate_mock_reset();
    assert(labmate_scope_native_init(&s));
    labmate_mock_dwt.CTRL = 0U;
    assert(labmate_scope_native_start(&s, &env, &owner, 0) == LabMateScopeNativeClockError);
    assert(!labmate_mock_hal.held_handle);
    labmate_mock_dwt.CTRL = DWT_CTRL_CYCCNTENA_Msk;
    SystemCoreClock = UINT32_C(900000000);
    assert(labmate_scope_native_start(&s, &env, &owner, 0) == LabMateScopeNativeClockError);
    SystemCoreClock = UINT32_C(64000000);
    labmate_mock_hal.foreign_callback = true;
    labmate_mock_hal.refuse_release = true;
    assert(labmate_scope_native_start(&s, &env, &owner, 0) == LabMateScopeNativeFault);
    assert(s.fault_sticky && s.owner.handle == 5U);
    assert(!labmate_mock_hal.gpio_writes && !labmate_mock_hal.exti_writes);
    assert(labmate_scope_native_start(&s, &env, &owner, 0) == LabMateScopeNativeFault);
    labmate_mock_hal.refuse_release = false;
    assert(labmate_scope_native_stop(&s, &owner));
    assert(labmate_mock_hal.held_handle == 0U);
    assert(!labmate_mock_hal.gpio_writes && !labmate_mock_hal.exti_writes);
    assert(s.fault_sticky);
    assert(!labmate_scope_native_init(&s)); /* fault cannot be wiped by re-arm */
    assert(labmate_scope_native_start(&s, &env, &owner, 0) ==
           LabMateScopeNativeFault);
}
static void test_timeout_and_overflow_stop(void) {
    static LabMateScopeNative s;
    LabMateScopePc1Environment env = free_pc1();
    LabMateCaptureOwner owner = LabMateCaptureNone;
    labmate_mock_reset();
    assert(labmate_scope_native_init(&s));
    assert(labmate_scope_native_start(&s, &env, &owner, 0) == LabMateScopeNativeReady);
    for(uint32_t ms = 100U; ms < 1000U; ms += 100U)
        assert(labmate_scope_native_poll(&s, &owner, ms) == LabMateScopeGuardRunning);
    assert(labmate_scope_native_poll(&s, &owner, 1000U) == LabMateScopeGuardNoTrigger);
    assert(owner == LabMateCaptureNone && labmate_mock_hal.held_handle == 0U);
    assert(labmate_scope_native_init(&s));
    labmate_mock_reset();
    assert(labmate_scope_native_start(&s, &env, &owner, 0) == LabMateScopeNativeReady);
    for(uint32_t i = 0U; i < LABMATE_SCOPE_MAX_EDGES; ++i)
        labmate_mock_edge(i + 10U, (i & 1U) == 0U);
    assert(s.buffer.count == LABMATE_SCOPE_MAX_EDGES);
    labmate_mock_edge(900U, true);
    assert(s.buffer.overflowed && s.buffer.dropped_edges == 1U);
    assert(labmate_scope_native_poll(&s, &owner, 20U) == LabMateScopeGuardFull);
    assert(owner == LabMateCaptureNone && labmate_mock_hal.held_handle == 0U);
}
int main(void) {
    test_owned_capture_and_stop();
    test_foreign_owner_and_callback_denials();
    test_partial_release_and_clock_safety();
    test_timeout_and_overflow_stop();
    puts("v1.9 matched-Momentum PC1 real-driver mocked HAL scenarios PASS");
    return 0;
}
