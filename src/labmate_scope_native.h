#pragma once

/* E11-matched Momentum ONLY. Standalone v1.9 PC1 EXTI1 driver module.
 * Not connected to the production app menu or installed on Flipper yet.
 * Parent app owns the lifetime of this heap/static session (NOT stack).
 * All APIs called under the app mutex from the application thread;
 * ONLY the registered callback runs in IRQ context.
 */
#include "labmate_scope_buffer.h"
#include "labmate_scope_gate.h"
#include "labmate_scope_timeguard.h"

typedef enum {
    LabMateScopeNativeReady = 0,
    LabMateScopeNativeBusy,
    LabMateScopeNativeUnsupported,
    LabMateScopeNativeFault,
    LabMateScopeNativeClockError,
} LabMateScopeNativeStatus;

typedef struct {
    LabMateScopeEdge storage[LABMATE_SCOPE_MAX_EDGES];
    LabMateScopeBuffer buffer;
    LabMateScopeTimeguard timeguard;
    LabMateScopeOwnerState owner;
    volatile bool irq_enabled;
    bool session_initialized;
    bool active;
    bool fault_sticky;
    LabMateScopeNativeStatus status;
} LabMateScopeNative;

/* Caller must own and keep memory alive until STOP has detached the IRQ.
 * Refuses reinit with any outstanding lease/registered callback. */
bool labmate_scope_native_init(LabMateScopeNative* state);

/* env must be the actual current local app owner/busy snapshot. shared_owner
 * points to app->capture_owner and must equal env.capture_owner.
 * No pin, IRQ or firmware registers modified when busy or unsupported.
 * Prepares the real DWT CYCCNT capture and registers only owned PC1 callback.
 * Separate patched E11 Firmware HAL features are mandatory. */
LabMateScopeNativeStatus labmate_scope_native_start(
    LabMateScopeNative* state, const LabMateScopePc1Environment* env,
    LabMateCaptureOwner* shared_owner, uint32_t current_ms);

/* Poll from app thread at most 100 ms apart with monotonic millisecond clock.
 * Returns a terminal condition and automatically requests owned teardown. */
LabMateScopeGuardResult labmate_scope_native_poll(
    LabMateScopeNative* state, LabMateCaptureOwner* shared_owner, uint32_t now_ms);

/* STOP never releases anyone else's lease/IRQ. Teardown clears only owned
 * callback, PC1 EXTI1 configuration and matching firmware lease. On lease
 * release failure the token is retained and further STARTs are denied. */
bool labmate_scope_native_stop(
    LabMateScopeNative* state, LabMateCaptureOwner* shared_owner);

/* IRQ-safe consistency snapshot. Copy at most capacity_to_copy records into
 * caller-owned buffer; no live drawing or storage in the callback. */
LabMateScopeSnapshot labmate_scope_native_read(
    LabMateScopeNative* state, LabMateScopeEdge* dst,
    uint16_t capacity_to_copy, uint16_t* copied);
