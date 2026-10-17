#include "labmate_scope_timeguard.h"

bool labmate_scope_timeguard_init(
    LabMateScopeTimeguard* guard,
    uint32_t initial_ms,
    uint32_t trigger_timeout_ms,
    uint32_t quiet_timeout_ms,
    uint32_t max_session_ms,
    uint32_t max_poll_gap_ms) {
    if(!guard || !trigger_timeout_ms || !quiet_timeout_ms ||
       !max_session_ms || !max_poll_gap_ms ||
       max_session_ms > LABMATE_SCOPE_MAX_SAFE_DELTA ||
       max_poll_gap_ms > LABMATE_SCOPE_MAX_SAFE_DELTA ||
       trigger_timeout_ms > max_session_ms ||
       quiet_timeout_ms > max_session_ms ||
       max_poll_gap_ms > trigger_timeout_ms ||
       max_poll_gap_ms > quiet_timeout_ms) return false;

    *guard = (LabMateScopeTimeguard){
        .trigger_timeout_ms = trigger_timeout_ms,
        .quiet_timeout_ms = quiet_timeout_ms,
        .max_session_ms = max_session_ms,
        .max_poll_gap_ms = max_poll_gap_ms,
        .previous_poll_ms = initial_ms,
        .result = LabMateScopeGuardRunning,
        .initialized = true,
    };
    return true;
}

LabMateScopeGuardResult labmate_scope_timeguard_poll(
    LabMateScopeTimeguard* guard,
    uint32_t now_ms,
    LabMateScopeSnapshot sample) {
    if(!guard || !guard->initialized) return LabMateScopeGuardInvalid;
    if(guard->result != LabMateScopeGuardRunning) return guard->result;

    /* All comparisons are modulo-32 safe ONLY when polls are frequent.
     * A silent complete 32-bit millisecond wrap cannot be detected here. */
    const uint32_t dt = now_ms - guard->previous_poll_ms;
    if(dt > guard->max_poll_gap_ms) {
        guard->result = LabMateScopeGuardClockUnsafe;
        return guard->result;
    }
    guard->previous_poll_ms = now_ms;
    if(sample.capacity == 0U || sample.capacity > LABMATE_SCOPE_MAX_EDGES ||
       sample.count > sample.capacity || sample.count < guard->previous_edge_count ||
       (sample.state == LabMateScopeArmed && sample.count != 0U) ||
       (sample.state == LabMateScopeRecording && sample.count == 0U)) {
        guard->result = LabMateScopeGuardInvalid;
        return guard->result;
    }
    if(sample.timebase_error || sample.state == LabMateScopeError) {
        guard->result = LabMateScopeGuardCaptureError;
        return guard->result;
    }
    if(sample.overflowed || sample.state == LabMateScopeFull) {
        guard->result = LabMateScopeGuardFull;
        return guard->result;
    }
    if(sample.state == LabMateScopeStopped) {
        guard->result = LabMateScopeGuardStopped;
        return guard->result;
    }
    if(sample.state != LabMateScopeArmed && sample.state != LabMateScopeRecording) {
        guard->result = LabMateScopeGuardInvalid;
        return guard->result;
    }

    /* No unbounded addition: session stops at max_session_ms, and dt is
     * no larger than that maximum by init validation. */
    guard->elapsed_ms += dt;
    if(sample.count != guard->previous_edge_count) {
        guard->previous_edge_count = sample.count;
        guard->quiet_ms = 0U;
    } else if(sample.count != 0U) {
        guard->quiet_ms += dt;
    }

    if(guard->elapsed_ms >= guard->max_session_ms) {
        guard->result = LabMateScopeGuardDurationLimit;
    } else if(sample.state == LabMateScopeArmed &&
              guard->elapsed_ms >= guard->trigger_timeout_ms) {
        /* NO TRIGGER is honest even when unmatched edges were observed. */
        guard->result = LabMateScopeGuardNoTrigger;
    } else if(sample.state == LabMateScopeRecording &&
              guard->quiet_ms >= guard->quiet_timeout_ms) {
        guard->result = LabMateScopeGuardQuiet;
    }
    return guard->result;
}
