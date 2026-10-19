#include "labmate_scope_display.h"
#include <stdio.h>

/* Flipper 128x64: one mono pixel per trace/grid point; all labels fit the
 * 20-cell secondary-font width. No GPIO/IRQ, measurement or allocation. */
static const char* scope_state_label(LabMateScopeDisplayState s) {
    switch(s) {
    case LabMateScopeDisplayArmed: return "ARMED";
    case LabMateScopeDisplayRunning: return "LIVE";
    case LabMateScopeDisplayStopped: return "HOLD";
    case LabMateScopeDisplayNoTrigger: return "NO TRIG";
    case LabMateScopeDisplayQuiet: return "QUIET";
    case LabMateScopeDisplayFull: return "FULL";
    case LabMateScopeDisplayBusy: return "BUSY";
    case LabMateScopeDisplayUnsupported: return "UNSUP";
    case LabMateScopeDisplayError: return "ERROR";
    default: return "ERROR";
    }
}

bool labmate_scope_display_draw(Canvas* c, const LabMateScopeDisplay* d) {
    /* Validate the entire immutable IRQ-excluded snapshot BEFORE painting.
     * Never turn a partially invalid waveform into a plausible measurement. */
    if(!c || !d ||
       (unsigned)d->state > (unsigned)LabMateScopeDisplayError ||
       d->total_edges > LABMATE_SCOPE_MAX_EDGES ||
       (unsigned)d->plot.result > (unsigned)LabMateScopePlotTimebaseError ||
       d->plot.line_count > LABMATE_SCOPE_PLOT_MAX_LINES ||
       d->plot.visible_edges > LABMATE_SCOPE_PLOT_MAX_EDGES ||
       d->plot.visible_edges > d->total_edges ||
       (d->plot.line_count && !d->lines)) return false;
    if(d->plot.result == LabMateScopePlotReady) {
        if(d->plot.visible_edges < 2U ||
           d->plot.line_count != 2U * (d->plot.visible_edges - 1U)) return false;
    } else if(d->plot.line_count) return false;
    for(uint16_t i = 0U; i < d->plot.line_count; ++i) {
        const LabMateScopePlotLine* p = &d->lines[i];
        if(p->x0 < LABMATE_SCOPE_PLOT_X_LEFT ||
           p->x0 > LABMATE_SCOPE_PLOT_X_RIGHT ||
           p->x1 < LABMATE_SCOPE_PLOT_X_LEFT ||
           p->x1 > LABMATE_SCOPE_PLOT_X_RIGHT ||
           (p->y0 != LABMATE_SCOPE_PLOT_Y_HIGH && p->y0 != LABMATE_SCOPE_PLOT_Y_LOW) ||
           (p->y1 != LABMATE_SCOPE_PLOT_Y_HIGH && p->y1 != LABMATE_SCOPE_PLOT_Y_LOW))
            return false;
    }

    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, 3, 9, "LOGIC SCOPE");
    canvas_draw_str(c, 102, 9, "PC1");
    canvas_draw_line(c, 0, 13, 127, 13);

    /* Fixed oscilloscope viewport. Border encloses both real HIGH/LOW
     * levels (y=20/35); grid never touches the status or help rows. */
    canvas_draw_line(c, 1, 15, 126, 15);
    canvas_draw_line(c, 1, 40, 126, 40);
    canvas_draw_line(c, 1, 15, 1, 40);
    canvas_draw_line(c, 126, 15, 126, 40);
    const bool can_draw = d->plot.result == LabMateScopePlotReady &&
        d->state != LabMateScopeDisplayBusy &&
        d->state != LabMateScopeDisplayUnsupported &&
        d->state != LabMateScopeDisplayError;
    if(can_draw) {
        /* Sparse dashed divisions: visible timebase cues, never fake edges.
         * Draw before the trace so the real waveform stays dominant. */
        for(uint8_t x = 26U; x <= 101U; x += 25U) {
            canvas_draw_line(c, x, 17, x, 18);
            canvas_draw_line(c, x, 26, x, 27);
            canvas_draw_line(c, x, 37, x, 38);
        }
        for(uint8_t x = 12U; x <= 108U; x += 16U) {
            canvas_draw_line(c, x, 28, x + 2, 28);
        }
        for(uint16_t i = 0U; i < d->plot.line_count; ++i) {
            const LabMateScopePlotLine* p = &d->lines[i];
            canvas_draw_line(c, p->x0, p->y0, p->x1, p->y1);
        }
    } else if(d->state == LabMateScopeDisplayBusy ||
              d->state == LabMateScopeDisplayUnsupported ||
              d->state == LabMateScopeDisplayError) {
        canvas_draw_str(c, 9, 31, scope_state_label(d->state));
    } else if(d->plot.result == LabMateScopePlotTimebaseError ||
              d->plot.result == LabMateScopePlotInvalid) {
        canvas_draw_str(c, 9, 31, "DATA INVALID");
    } else if(d->plot.result == LabMateScopePlotNoEdges) {
        canvas_draw_str(c, 9, 31,
            d->state == LabMateScopeDisplayNoTrigger ?
                "NO TRIGGER - PC1" : "WAIT PC1 EDGE");
    } else {
        canvas_draw_str(c, 9, 31, "WAIT 2 EDGES");
    }

    /* Cropped = latest 13 observed edges, never a fabricated full trace.
     * Use ZM only for the longest state label to stay inside 20 glyphs. */
    const char* state = scope_state_label(d->state);
    const char* suffix = d->plot.cropped_old_edges ?
        (d->state == LabMateScopeDisplayNoTrigger ? " ZM" : " ZOOM") : "";
    char summary[24];
    const int used = snprintf(summary, sizeof(summary), "%u EDGES %s%s",
        (unsigned)d->total_edges, state, suffix);
    if(used < 0 || used > 20) return false;
    canvas_draw_str(c, 3, 50, summary);
    canvas_draw_line(c, 0, 53, 127, 53);
    canvas_draw_str(c, 3, 62,
        (d->state == LabMateScopeDisplayArmed ||
         d->state == LabMateScopeDisplayRunning) ?
            "OK:STOP BK:EXIT" : "OK:RUN DN:PG BK:EXIT");
    return true;
}
