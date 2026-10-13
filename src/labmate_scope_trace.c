#include "labmate_scope_trace.h"
#include <limits.h>
#include <string.h>

_Static_assert(LABMATE_SCOPE_MAX_EVENTS == 128U, "Fixed-size scope trace");
_Static_assert(sizeof(LabMateScopeEvent) <= 8U, "Scope event RAM budget exceeded");

static bool valid_trigger(LabMateScopeTrigger trigger) {
    return trigger == LabMateScopeTriggerImmediate ||
           trigger == LabMateScopeTriggerRising ||
           trigger == LabMateScopeTriggerFalling ||
           trigger == LabMateScopeTriggerEither;
}

static bool triggered(LabMateScopeTrigger trigger, uint8_t old_level, uint8_t new_level) {
    if(old_level == new_level) return false;
    switch(trigger) {
    case LabMateScopeTriggerRising:
        return old_level == 0U && new_level == 1U;
    case LabMateScopeTriggerFalling:
        return old_level == 1U && new_level == 0U;
    case LabMateScopeTriggerEither:
        return true;
    case LabMateScopeTriggerImmediate:
    default:
        return false;
    }
}

void labmate_scope_trace_init(LabMateScopeTrace* trace) {
    if(trace) memset(trace, 0, sizeof(*trace));
}

bool labmate_scope_trace_is_active(const LabMateScopeTrace* trace) {
    return trace && (trace->state == LabMateScopeArmed || trace->state == LabMateScopeRecording);
}

bool labmate_scope_trace_start(
    LabMateScopeTrace* trace,
    LabMateScopeTrigger trigger,
    uint8_t initial_level,
    uint32_t start_tick,
    uint32_t* out_generation) {
    if(!trace || !out_generation || initial_level > 1U || !valid_trigger(trigger) ||
       labmate_scope_trace_is_active(trace) || trace->generation == UINT32_MAX)
        return false;

    /* Previously finalized data is replaced ONLY on a valid new start.
     * Increment rather than resetting token so late callbacks are stale. */
    ++trace->generation;
    trace->event_count = 0U;
    trace->elapsed_ticks = 0U;
    trace->missed_lower_bound = 0U;
    trace->last_tick = start_tick;
    trace->last_level = initial_level;
    trace->trigger = trigger;
    trace->fault_reason = LabMateScopeFaultNone;
    trace->state = trigger == LabMateScopeTriggerImmediate ?
                       LabMateScopeRecording : LabMateScopeArmed;

    if(trigger == LabMateScopeTriggerImmediate) {
        trace->events[0].offset_ticks = 0U;
        trace->events[0].level = initial_level;
        trace->event_count = 1U;
    }
    *out_generation = trace->generation;
    return true;
}

static LabMateScopeFeedResult fault(
    LabMateScopeTrace* trace, LabMateScopeFaultReason reason) {
    trace->state = LabMateScopeFault;
    trace->fault_reason = reason;
    return LabMateScopeFeedFault;
}

LabMateScopeFeedResult labmate_scope_trace_feed(
    LabMateScopeTrace* trace,
    uint32_t generation,
    uint32_t tick,
    uint8_t level) {
    if(!trace) return LabMateScopeFeedInactive;
    if(generation != trace->generation) return LabMateScopeFeedStale;
    if(!labmate_scope_trace_is_active(trace)) return LabMateScopeFeedInactive;

    if(level > 1U) return fault(trace, LabMateScopeFaultInvalidLevel);

    const uint32_t delta = tick - trace->last_tick; /* Unsigned tick rollover. */
    if(delta == 0U) {
        if(level == trace->last_level) return LabMateScopeFeedIgnored;
        return fault(trace, LabMateScopeFaultClock);
    }
    /* A gap >= 2^31 is ambiguous with a backwards clock. Reject.
     * Limit the entire arming/recording phase, even with periodic
     * unchanged-level polls, to avoid silently wrapping the offset. */
    if(delta > LABMATE_SCOPE_MAX_SPAN_TICKS)
        return fault(trace, LabMateScopeFaultClock);
    if(delta > LABMATE_SCOPE_MAX_SPAN_TICKS - trace->elapsed_ticks)
        return fault(trace, LabMateScopeFaultSpan);

    trace->elapsed_ticks += delta;
    trace->last_tick = tick;
    if(level == trace->last_level) return LabMateScopeFeedIgnored;

    const uint8_t old_level = trace->last_level;
    trace->last_level = level;
    if(trace->state == LabMateScopeArmed) {
        if(!triggered(trace->trigger, old_level, level)) return LabMateScopeFeedIgnored;
        trace->state = LabMateScopeRecording;
        trace->elapsed_ticks = 0U;
        trace->events[0].offset_ticks = 0U;
        trace->events[0].level = level;
        trace->event_count = 1U;
        return LabMateScopeFeedTriggered;
    }
    if(trace->event_count >= LABMATE_SCOPE_MAX_EVENTS) {
        /* First omitted observed transition. No overwrite, no false
         * claim about how many edges would arrive after freezing. */
        trace->missed_lower_bound = 1U;
        trace->state = LabMateScopeOverflow;
        return LabMateScopeFeedOverflow;
    }
    trace->events[trace->event_count].offset_ticks = trace->elapsed_ticks;
    trace->events[trace->event_count].level = level;
    ++trace->event_count;
    return LabMateScopeFeedRecorded;
}

bool labmate_scope_trace_stop(LabMateScopeTrace* trace, uint32_t generation) {
    if(!trace || generation != trace->generation || !labmate_scope_trace_is_active(trace))
        return false;
    trace->state = LabMateScopeStopped;
    return true;
}

bool labmate_scope_trace_event_at(
    const LabMateScopeTrace* trace, uint16_t index, LabMateScopeEvent* output) {
    if(!trace || !output || index >= trace->event_count) return false;
    *output = trace->events[index];
    return true;
}
