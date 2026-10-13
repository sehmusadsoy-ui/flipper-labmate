#include "labmate_scope_project.h"
#include <string.h>

_Static_assert(
    LABMATE_SCOPE_GRAPH_COLUMNS <= 128U,
    "Graph must fit Flipper's 128-pixel wide display");
_Static_assert(
    LABMATE_SCOPE_GRAPH_COLUMNS >= 2U,
    "Graph needs separate left and right columns");

static LabMateScopeViewState view_from_trace_state(LabMateScopeState state) {
    switch(state) {
    case LabMateScopeOverflow: return LabMateScopeViewOverflow;
    case LabMateScopeFault: return LabMateScopeViewFault;
    default: return LabMateScopeViewTrace;
    }
}

bool labmate_scope_project(
    const LabMateScopeTrace* trace,
    uint32_t window_start_ticks,
    uint32_t window_end_ticks,
    LabMateScopeProjection* output) {

    if(!output) return false;
    memset(output, 0, sizeof(*output));
    output->state = LabMateScopeViewInvalid;

    if(!trace || window_start_ticks >= window_end_ticks ||
       trace->event_count > LABMATE_SCOPE_MAX_EVENTS)
        return false;

    output->window_start_ticks = window_start_ticks;
    output->window_end_ticks = window_end_ticks;

    if(trace->event_count == 0U) {
        /* No waveform, not a guessed flat line. */
        if(trace->state == LabMateScopeArmed)
            output->state = LabMateScopeViewWaitingTrigger;
        else if(trace->state == LabMateScopeStopped)
            output->state = LabMateScopeViewNotTriggered;
        else if(trace->state == LabMateScopeFault)
            output->state = LabMateScopeViewFault;
        else
            output->state = LabMateScopeViewNoSpan;
        return true;
    }

    /* A single observed anchor with no elapsed time is NOT evidence
     * of a persistent level over a graph width. */
    if(trace->elapsed_ticks == 0U) {
        output->state = LabMateScopeViewNoSpan;
        return true;
    }

    /* First event must anchor a known post-trigger level at time zero.
     * This guards consumers against drawing uninitialized history. */
    if(trace->events[0].offset_ticks != 0U ||
       trace->events[0].level > 1U)
        return false;

    const uint32_t last_known =
        (trace->state == LabMateScopeOverflow) ?
            trace->events[trace->event_count - 1U].offset_ticks :
            trace->elapsed_ticks;
    if(window_end_ticks > last_known) return false;

    /* Reject inconsistent event ordering instead of inventing pulses.
     * Scope TRACE's normal producer always stores strictly advancing
     * offsets and binary levels. Verify again at presentation boundary. */
    for(uint16_t i = 1U; i < trace->event_count; ++i) {
        if(trace->events[i].offset_ticks <= trace->events[i - 1U].offset_ticks ||
           trace->events[i].offset_ticks > trace->elapsed_ticks ||
           trace->events[i].level > 1U ||
           trace->events[i].level == trace->events[i - 1U].level)
            return false;
    }

    const uint32_t span = window_end_ticks - window_start_ticks;
    uint16_t next = 1U;
    uint8_t level = trace->events[0].level;

    /* The first visible pixel begins AFTER all events at/before
     * window_start. A left-clipped transition is not redrawn as new. */
    while(next < trace->event_count &&
          trace->events[next].offset_ticks <= window_start_ticks) {
        level = trace->events[next].level;
        ++next;
    }

    for(uint16_t x = 0U; x < LABMATE_SCOPE_GRAPH_COLUMNS; ++x) {
        LabMateScopePixelColumn* col = &output->columns[x];
        col->entering_level = level;
        col->leaving_level = level;

        /* Pixel placement is FLOOR((edge-start) * (N-1) / span).
         * Perform multiply in uint64_t (max span is 2^31-1).
         * Events at window_end belong to final pixel column.
         */
        while(next < trace->event_count) {
            const uint32_t tick = trace->events[next].offset_ticks;
            if(tick > window_end_ticks) break;
            const uint32_t relative = tick - window_start_ticks;
            const uint32_t at = (uint32_t)(((uint64_t)relative *
                (LABMATE_SCOPE_GRAPH_COLUMNS - 1U)) / span);
            if(at != x) break;

            level = trace->events[next].level;
            if(col->transitions != UINT8_MAX) ++col->transitions;
            ++next;
        }
        col->leaving_level = level;
        if(col->transitions >= 2U) ++output->dense_columns;
    }

    output->state = view_from_trace_state(trace->state);
    output->has_waveform = true;
    output->left_cropped = window_start_ticks > 0U;
    /* Overflow implies a known truncated trace, even if the user
     * views exactly its final STORED edge. */
    output->right_cropped =
        window_end_ticks < last_known || trace->state == LabMateScopeOverflow;
    return true;
}
