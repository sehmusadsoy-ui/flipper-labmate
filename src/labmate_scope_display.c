#include "labmate_scope_display.h"
#include <stdio.h>

static const char* scope_state_label(LabMateScopeDisplayState s) {
    switch(s) {
    case LabMateScopeDisplayArmed: return "ARMED";
    case LabMateScopeDisplayRunning: return "LIVE";
    case LabMateScopeDisplayStopped: return "HOLD";
    case LabMateScopeDisplayNoTrigger: return "NO TRIGGER";
    case LabMateScopeDisplayQuiet: return "QUIET";
    case LabMateScopeDisplayFull: return "FULL";
    case LabMateScopeDisplayBusy: return "BUSY";
    case LabMateScopeDisplayUnsupported: return "UNSUPPORTED";
    case LabMateScopeDisplayError: return "ERR";
    default: return "ERR";
    }
}

bool labmate_scope_display_draw(Canvas* c, const LabMateScopeDisplay* d) {
    if(!c || !d || d->state > LabMateScopeDisplayError ||
       d->total_edges > LABMATE_SCOPE_MAX_EDGES ||
       d->plot.result > LabMateScopePlotTimebaseError ||
       d->plot.line_count > LABMATE_SCOPE_PLOT_MAX_LINES ||
       (d->plot.line_count && !d->lines)) return false;

    /* Validate the WHOLE geometry before painting any part of a waveform. */
    for(uint16_t i = 0; i < d->plot.line_count; ++i) {
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
    canvas_draw_str(c, 94, 9, "PC1");
    canvas_draw_line(c, 0, 13, 127, 13);

    const bool can_draw = d->plot.result == LabMateScopePlotReady &&
        d->state != LabMateScopeDisplayBusy &&
        d->state != LabMateScopeDisplayUnsupported &&
        d->state != LabMateScopeDisplayError;
    if(can_draw) {
        for(uint16_t i = 0; i < d->plot.line_count; ++i) {
            const LabMateScopePlotLine* p = &d->lines[i];
            canvas_draw_line(c, p->x0, p->y0, p->x1, p->y1);
        }
    } else if(d->state == LabMateScopeDisplayBusy ||
              d->state == LabMateScopeDisplayUnsupported ||
              d->state == LabMateScopeDisplayError) {
        canvas_draw_str(c, 7, 33, scope_state_label(d->state));
    } else if(d->plot.result == LabMateScopePlotTimebaseError ||
              d->plot.result == LabMateScopePlotInvalid) {
        canvas_draw_str(c, 7, 33, "DATA INVALID");
    } else if(d->plot.result == LabMateScopePlotNoEdges) {
        canvas_draw_str(c, 7, 33,
            d->state == LabMateScopeDisplayNoTrigger ? "NO TRIGGER" : "WAIT REAL EDGE");
    } else {
        canvas_draw_str(c, 7, 33, "WAIT 2 EDGES");
    }

    /* A 128px LCD with 6px FontSecondary fits at most 20 characters
     * starting from x=3. Use SHORT status text on the footer row; long
     * diagnostic names remain on the center line. At worst:
     * E:256 NO TRG LAST64 = 19 glyphs and 114px, fully on-screen.
     */
    const char* short_state = scope_state_label(d->state);
    if(d->state == LabMateScopeDisplayNoTrigger) short_state = "NO TRG";
    else if(d->state == LabMateScopeDisplayUnsupported) short_state = "UNSUP";
    char summary[24];
    snprintf(summary, sizeof(summary), "E:%u %s%s", (unsigned)d->total_edges,
             short_state, d->plot.cropped_old_edges ? " LAST64" : "");
    canvas_draw_str(c, 3, 50, summary);
    canvas_draw_line(c, 0, 53, 127, 53);
    canvas_draw_str(c, 3, 62, "OK RUN/STOP BK EXIT");
    return true;
}
