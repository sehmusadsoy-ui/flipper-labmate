#include "labmate_scope_native.h"
#include "labmate_capture_exti.h"

#include <furi.h>
#include <furi_hal.h>
#include <furi_hal_resources.h>
#include <stm32wbxx_ll_exti.h>
#include <string.h>

/* IMPORTANT: no fallback to the stock (asserting) GPIO callback API.
 * Compilation of the module itself is harmless without the matched ABI,
 * but START must always fail CLOSED on any unpatched firmware.
 */
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1) && defined(FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK)
#define LABMATE_SCOPE_NATIVE_MATCHED_ABI 1
#else
#define LABMATE_SCOPE_NATIVE_MATCHED_ABI 0
#endif

#define SCOPE_TRIGGER_TIMEOUT_MS UINT32_C(1000)
#define SCOPE_QUIET_TIMEOUT_MS UINT32_C(200)
#define SCOPE_POLL_MAX_MS UINT32_C(100)

#if LABMATE_SCOPE_NATIVE_MATCHED_ABI
static void labmate_scope_pc1_irq(void* context) {
    LabMateScopeNative* session = context;
    if(!session || !session->irq_enabled ||
       session->owner.phase != LabMateScopeOwnerRunning) return;

    /* O(1): no heap, display, storage or blocking wait from IRQ. The GPIO
     * level is read AFTER the edge; unchanged callbacks are ignored by the
     * buffer. The actual edge is timestamped by DWT CYCCNT.
     */
    const uint32_t cycle = DWT->CYCCNT;
    const bool high = furi_hal_gpio_read(&gpio_ext_pc1);
    labmate_scope_buffer_push_edge(&session->buffer, cycle, high);
}

static bool labmate_scope_edge_timebase_safe(void) {
    const uint32_t hz = SystemCoreClock;
    if(hz == 0U || (DWT->CTRL & DWT_CTRL_CYCCNTENA_Msk) == 0U) return false;
    /* The whole 5-second capture is strictly shorter than a half-wrap of
     * this 32-bit clock, as required by the buffer. Clock frequency cannot
     * be assumed from a hard-coded FAP SDK value.
     */
    return (uint64_t)hz * LABMATE_SCOPE_GUARD_MAX_SESSION_MS <
           (uint64_t)LABMATE_SCOPE_MAX_SAFE_DELTA * UINT64_C(1000);
}
#endif

bool labmate_scope_native_init(LabMateScopeNative* session) {
    if(!session || session->active || session->owner.handle ||
       session->owner.phase != LabMateScopeOwnerIdle) return false;
    memset(session, 0, sizeof(*session));
    if(!labmate_scope_buffer_init(
           &session->buffer, session->storage, LABMATE_SCOPE_MAX_EDGES)) return false;
    session->session_initialized = true;
    session->status = LabMateScopeNativeReady;
    return true;
}

LabMateScopeNativeStatus labmate_scope_native_start(
    LabMateScopeNative* session, const LabMateScopePc1Environment* env,
    LabMateCaptureOwner* shared_owner, uint32_t current_ms) {
    if(!session || !env || !shared_owner || !session->session_initialized ||
       session->active || *shared_owner != env->capture_owner) {
        return LabMateScopeNativeFault;
    }
#if LABMATE_SCOPE_NATIVE_MATCHED_ABI
    if(session->fault_sticky) return LabMateScopeNativeFault;
    LabMateScopePc1Environment snapshot = *env;
    snapshot.firmware_lease_api = true;
    snapshot.firmware_try_callback = true;
    const LabMateScopeGate gate = labmate_scope_gate_pc1(&snapshot, &session->owner);
    if(gate != LabMateScopeGateReady) {
        session->status =
            (gate == LabMateScopeGateUnsupported) ? LabMateScopeNativeUnsupported :
            (gate == LabMateScopeGateFault || gate == LabMateScopeGateInvalid) ?
                LabMateScopeNativeFault : LabMateScopeNativeBusy;
        return session->status;
    }
    if(!labmate_scope_edge_timebase_safe()) {
        session->status = LabMateScopeNativeClockError;
        return session->status;
    }
    if(!labmate_scope_timeguard_init(
           &session->timeguard, current_ms, SCOPE_TRIGGER_TIMEOUT_MS,
           SCOPE_QUIET_TIMEOUT_MS, LABMATE_SCOPE_GUARD_MAX_SESSION_MS,
           SCOPE_POLL_MAX_MS)) {
        session->status = LabMateScopeNativeClockError;
        return session->status;
    }

    const uint32_t handle =
        furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PC1);
    if(!handle) {
        session->status = LabMateScopeNativeBusy;
        return session->status;
    }
    if(!labmate_scope_owner_lease_acquired(&session->owner, handle)) {
        /* Invalid bookkeeping: preserve native lease identity and do not
         * configure another peripheral while ownership is uncertain. */
        session->owner.handle = handle;
        session->owner.phase = LabMateScopeOwnerReleaseFault;
        session->owner.fault_cleanup_phase = LabMateScopeOwnerLease;
        session->fault_sticky = true;
        session->status = LabMateScopeNativeFault;
        return session->status;
    }

    /* Acquire a callback slot BEFORE any GPIO mode / EXTI reset.
     * try_add rejects a legacy client with a foreign callback rather than
     * asserting or resetting its pin. On denial, release only the lease.
     */
    if(!furi_hal_gpio_try_add_int_callback(
           &gpio_ext_pc1, labmate_scope_pc1_irq, session)) {
        const bool released =
            furi_hal_resource_lease_release(handle, FURI_HAL_LEASE_IRQ_PC1);
        labmate_scope_owner_stop_confirmed(&session->owner, false, false, released);
        if(!released) session->fault_sticky = true;
        session->status = released ? LabMateScopeNativeBusy : LabMateScopeNativeFault;
        return session->status;
    }
    labmate_scope_owner_callback_added(&session->owner);
    /* Shared interrupt line was briefly enabled by try_add. Quiesce while
     * programming only the now-owned PC1 line.
     */
    furi_hal_gpio_disable_int_callback(&gpio_ext_pc1);
    labmate_capture_exti_clear(LL_EXTI_LINE_1, true);
    furi_hal_gpio_init(
        &gpio_ext_pc1, GpioModeInterruptRiseFall,
        GpioPullNo, GpioSpeedVeryHigh);
    labmate_scope_owner_pin_configured(&session->owner);

    const bool initial = furi_hal_gpio_read(&gpio_ext_pc1);
    if(!labmate_scope_buffer_arm(
           &session->buffer, LabMateScopeTriggerEither, initial)) {
        /* Should be unreachable after init+teardown; owned STOP nonetheless. */
        labmate_scope_native_stop(session, shared_owner);
        session->status = LabMateScopeNativeFault;
        return session->status;
    }

    labmate_scope_owner_started(&session->owner);
    *shared_owner = LabMateCaptureScope;
    session->active = true;
    session->irq_enabled = true;
    furi_hal_gpio_enable_int_callback(&gpio_ext_pc1);
    session->status = LabMateScopeNativeReady;
    return session->status;
#else
    (void)current_ms;
    session->status = LabMateScopeNativeUnsupported;
    return session->status;
#endif
}

bool labmate_scope_native_stop(
    LabMateScopeNative* session, LabMateCaptureOwner* shared_owner) {
    if(!session || !shared_owner) return false;
#if LABMATE_SCOPE_NATIVE_MATCHED_ABI
    const LabMateScopeReleasePlan todo =
        labmate_scope_owner_stop_plan(&session->owner);
    if(!todo.release_lease) return !session->active && !session->owner.handle;

    /* Callback cannot race with the buffer STOP; critical section excludes
     * in-flight ISR. Do NOT detach if it is not our callback.
     */
    if(todo.detach_callback) {
        FURI_CRITICAL_ENTER();
        session->irq_enabled = false;
        furi_hal_gpio_disable_int_callback(&gpio_ext_pc1);
        FURI_CRITICAL_EXIT();
        furi_hal_gpio_remove_int_callback(&gpio_ext_pc1);
    }
    /* Only an owned configured PC1 is allowed to reset EXTI/GPIO state. */
    if(todo.restore_pin) {
        labmate_capture_exti_clear(LL_EXTI_LINE_1, true);
        furi_hal_gpio_init_simple(&gpio_ext_pc1, GpioModeAnalog);
    }
    session->active = false;
    labmate_scope_buffer_stop(&session->buffer);
    if(*shared_owner == LabMateCaptureScope)
        *shared_owner = LabMateCaptureNone;

    const bool lease_released = furi_hal_resource_lease_release(
        session->owner.handle, FURI_HAL_LEASE_IRQ_PC1);
    const bool complete = labmate_scope_owner_stop_confirmed(
        &session->owner, todo.detach_callback, todo.restore_pin, lease_released);
    if(!complete) {
        session->fault_sticky = true;
        session->status = LabMateScopeNativeFault;
    }
    return complete;
#else
    return !session->active && !session->owner.handle;
#endif
}

LabMateScopeGuardResult labmate_scope_native_poll(
    LabMateScopeNative* session, LabMateCaptureOwner* shared_owner, uint32_t now_ms) {
    if(!session || !shared_owner || !session->active ||
       *shared_owner != LabMateCaptureScope) return LabMateScopeGuardInvalid;
    const LabMateScopeSnapshot sample = labmate_scope_native_read(session, NULL, 0, NULL);
    LabMateScopeGuardResult outcome =
        labmate_scope_timeguard_poll(&session->timeguard, now_ms, sample);
    if(outcome != LabMateScopeGuardRunning) {
        /* This is an application-thread operation; never STOP from the IRQ. */
        if(!labmate_scope_native_stop(session, shared_owner))
            return LabMateScopeGuardCaptureError;
    }
    return outcome;
}

LabMateScopeSnapshot labmate_scope_native_read(
    LabMateScopeNative* session, LabMateScopeEdge* dst,
    uint16_t capacity_to_copy, uint16_t* copied) {
    if(copied) *copied = 0U;
    if(!session || !session->session_initialized || (capacity_to_copy && !dst))
        return (LabMateScopeSnapshot){.state = LabMateScopeError, .timebase_error = true};
    FURI_CRITICAL_ENTER();
    const LabMateScopeSnapshot sample = labmate_scope_buffer_snapshot(&session->buffer);
    if(dst && capacity_to_copy && copied) {
        uint16_t count = sample.count;
        if(count > capacity_to_copy) count = capacity_to_copy;
        /* Copy the most recent bounded samples; no stack-allocated 3 KiB
         * frames, heap alloc or file writes from the ISR. */
        const uint16_t first = (uint16_t)(sample.count - count);
        memcpy(dst, session->buffer.edges + first, sizeof(*dst) * count);
        *copied = count;
    }
    FURI_CRITICAL_EXIT();
    return sample;
}
