#pragma once
/* v2.0 Phase 2K: fail-closed app-thread native capture release decision.
 * Boolean reports come from each native owner AFTER its STOP attempt.
 * This policy is NOT independent evidence of actual IRQ line circuitry.
 * Pure C11, no HAL, heap, GPIO, clocks or storage.
 */
#include <stdbool.h>

typedef struct {
    bool scope_stop_confirmed;
    bool frequency_low_active;
    bool frequency_high_active;
    bool pulse_active;
    bool counter_active;
    bool button_active;
    bool frequency_low_lease_pending;
    bool frequency_high_lease_pending;
    bool pulse_lease_pending;
    bool release_fault;
} LabMateCaptureReleaseEvidence;

/* A release failure or any pending native handle means the application
 * must not advertise "free" or authorize a new capture from STOP/BACK.
 * This is intentionally stricter than merely seeing active=false.
 */
static inline bool labmate_capture_release_proven(
    const LabMateCaptureReleaseEvidence* e) {
    return e && e->scope_stop_confirmed &&
           !e->frequency_low_active && !e->frequency_high_active &&
           !e->pulse_active && !e->counter_active && !e->button_active &&
           !e->frequency_low_lease_pending && !e->frequency_high_lease_pending &&
           !e->pulse_lease_pending && !e->release_fault;
}
