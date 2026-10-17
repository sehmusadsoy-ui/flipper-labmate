#pragma once

/* v1.9 Logic Scope supervision, pure C: no I/O, IRQ registration or HAL.
 *
 * Observe an IRQ-excluded snapshot from labmate_scope_buffer at a regular
 * cadence using an independent, verified 32-bit monotonic millisecond clock.
 * Timer calls / UI must not run from the IRQ. The guard never performs
 * STOP or changes GPIO ownership: terminal results REQUEST owned teardown.
 *
 * REQUIRED: each poll interval <= max_poll_gap_ms, no unseen full 32-bit
 * millisecond wrap, and session_max_ms less than the high-resolution edge
 * timer's independently verified half-wrap period. A gap is a CLOCK_UNSAFE
 * result, not false NO_SIGNAL. Caller must handle missed scheduling safely.
 */
#include <stdbool.h>
#include <stdint.h>
#include "labmate_scope_buffer.h"

/* Conservative v1.9 short capture windows; real DWT frequency must still
 * be checked by the native driver before any IRQ mode is enabled. */
#define LABMATE_SCOPE_GUARD_MAX_SESSION_MS UINT32_C(5000)
#define LABMATE_SCOPE_GUARD_MAX_POLL_GAP_MS UINT32_C(100)

typedef enum {
    LabMateScopeGuardRunning = 0,
    LabMateScopeGuardNoTrigger,
    LabMateScopeGuardQuiet,
    LabMateScopeGuardDurationLimit,
    LabMateScopeGuardClockUnsafe,
    LabMateScopeGuardFull,
    LabMateScopeGuardCaptureError,
    LabMateScopeGuardStopped,
    LabMateScopeGuardInvalid,
} LabMateScopeGuardResult;

typedef struct {
    uint32_t trigger_timeout_ms;
    uint32_t quiet_timeout_ms;
    uint32_t max_session_ms;
    uint32_t max_poll_gap_ms;
    uint32_t previous_poll_ms;
    uint32_t elapsed_ms;
    uint32_t quiet_ms;
    uint16_t previous_edge_count;
    LabMateScopeGuardResult result;
    bool initialized;
} LabMateScopeTimeguard;

/* The maximum session MUST be chosen with the real native edge timebase
 * frequency and half-wrap in mind; this pure module cannot inspect DWT. */
bool labmate_scope_timeguard_init(
    LabMateScopeTimeguard* guard,
    uint32_t initial_ms,
    uint32_t trigger_timeout_ms,
    uint32_t quiet_timeout_ms,
    uint32_t max_session_ms,
    uint32_t max_poll_gap_ms);

/* Pass an IRQ-excluded, consistent LabMateScopeSnapshot. Poll regularly
 * even while waiting for the first trigger. Terminal results are sticky.
 * A non-Running return requires application-thread owned IRQ teardown. */
LabMateScopeGuardResult labmate_scope_timeguard_poll(
    LabMateScopeTimeguard* guard,
    uint32_t now_ms,
    LabMateScopeSnapshot snapshot);
