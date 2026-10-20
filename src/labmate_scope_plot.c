#include "labmate_scope_plot.h"

LabMateScopePlotStats labmate_scope_plot_project(
    const LabMateScopeEdge* edges, uint16_t available, bool cropped_old_edges,
    LabMateScopePlotLine* out, uint16_t max_lines) {
    LabMateScopePlotStats result = {
        .result = LabMateScopePlotInvalid,
        .cropped_old_edges = cropped_old_edges,
    };
    if(available > LABMATE_SCOPE_PLOT_MAX_EDGES ||
       max_lines > LABMATE_SCOPE_PLOT_MAX_LINES ||
       (available && !edges) ||
       (available > 1U && (!out || max_lines < (uint16_t)((available - 1U) * 2U)))) {
        return result;
    }
    if(!available) {
        result.result = LabMateScopePlotNoEdges;
        return result;
    }
    result.visible_edges = available;
    if(available == 1U) {
        /* A lone edge proves a transition happened but establishes no
         * observed high/low duration, so no horizontal trace is drawn. */
        result.result = LabMateScopePlotOneEdge;
        return result;
    }

    /* Every delta is measured between two stored events; no extrapolation.
     * The sum is required below the unambiguous 32-bit edge-clock halfwrap.
     */
    uint64_t span = 0U;
    for(uint16_t i = 1U; i < available; ++i) {
        if(edges[i].delta_ticks == 0U ||
           edges[i].delta_ticks > LABMATE_SCOPE_MAX_SAFE_DELTA ||
           edges[i].high == edges[i - 1U].high ||
           edges[i].tick - edges[i - 1U].tick != edges[i].delta_ticks) {
            result.result = LabMateScopePlotTimebaseError;
            return result;
        }
        span += edges[i].delta_ticks;
        if(span > LABMATE_SCOPE_MAX_SAFE_DELTA) {
            result.result = LabMateScopePlotTimebaseError;
            return result;
        }
    }
    result.window_cycles = (uint32_t)span;
    uint64_t elapsed = 0U;
    uint8_t x_previous = LABMATE_SCOPE_PLOT_X_LEFT;
    for(uint16_t i = 1U; i < available; ++i) {
        elapsed += edges[i].delta_ticks;
        const uint8_t x_next = (uint8_t)(
            LABMATE_SCOPE_PLOT_X_LEFT +
            (elapsed * (LABMATE_SCOPE_PLOT_X_RIGHT - LABMATE_SCOPE_PLOT_X_LEFT) / span));
        const uint8_t y_previous = edges[i - 1U].high ?
            LABMATE_SCOPE_PLOT_Y_HIGH : LABMATE_SCOPE_PLOT_Y_LOW;
        const uint8_t y_next = edges[i].high ?
            LABMATE_SCOPE_PLOT_Y_HIGH : LABMATE_SCOPE_PLOT_Y_LOW;
        out[result.line_count++] = (LabMateScopePlotLine){
            x_previous, y_previous, x_next, y_previous};
        out[result.line_count++] = (LabMateScopePlotLine){
            x_next, y_previous, x_next, y_next};
        x_previous = x_next;
    }
    result.result = LabMateScopePlotReady;
    return result;
}

/* Read-only focus window: last 13 stored edges = at most 12 measured
 * intervals (~6 periods for a square wave). NEVER interpolate fake edges.
 * This view is independent of full 256-edge A/B and reference metrics. */
LabMateScopePlotStats labmate_scope_plot_focus(
    const LabMateScopeEdge* edges, uint16_t available, bool cropped_old_edges,
    LabMateScopePlotLine* out, uint16_t max_lines) {
    if(available > LABMATE_SCOPE_PLOT_MAX_EDGES || (available && !edges)) {
        return (LabMateScopePlotStats){.result = LabMateScopePlotInvalid};
    }
    const uint16_t shown = available > LABMATE_SCOPE_PLOT_FOCUS_EDGES ?
        LABMATE_SCOPE_PLOT_FOCUS_EDGES : available;
    const LabMateScopeEdge* selected = shown ? edges + (available - shown) : NULL;
    return labmate_scope_plot_project(
        selected, shown, cropped_old_edges || available > shown, out, max_lines);
}
