#include "labmate_scope_display.h"
#include <stdio.h>

/* One deliberately quiet 128x64 UI. The viewport shows measured transitions
 * only; tick marks are uncalibrated navigation guides, not time divisions. */
static const char* scope_status(LabMateScopeDisplayState state) {
    switch(state) {
    case LabMateScopeDisplayArmed: return "ARMED";
    case LabMateScopeDisplayRunning: return "LIVE";
    case LabMateScopeDisplayStopped: return "HOLD";
    case LabMateScopeDisplayNoTrigger: return "NO SIGNAL";
    case LabMateScopeDisplayQuiet: return "QUIET";
    case LabMateScopeDisplayFull: return "FULL";
    case LabMateScopeDisplayBusy: return "BUSY";
    case LabMateScopeDisplayUnsupported: return "UNSUPPORTED";
    case LabMateScopeDisplayError: return "ERROR";
    default: return "ERROR";
    }
}

static void label(Canvas* c, Font font, int32_t x, int32_t y, const char* s) {
    canvas_set_font(c, font);
    canvas_draw_str(c, x, y, s);
}

static void footer(Canvas* c, const char* action) {
    /* Three visually independent key hints; never a continuous 20-glyph
     * command string. DOWN changes page only when acquisition is stopped. */
    canvas_draw_line(c, 0, 54, 127, 54);
    canvas_draw_line(c, 46, 56, 46, 63);
    canvas_draw_line(c, 92, 56, 92, 63);
    label(c, FontSecondary, 3, 62, action); /* <= 6 characters */
    label(c, FontSecondary, 52, 62, "v PAGE");
    label(c, FontSecondary, 101, 62, "BACK");
}

static bool ready_trace(const LabMateScopeDisplay* d) {
    return d->plot.result == LabMateScopePlotReady &&
           d->state != LabMateScopeDisplayBusy &&
           d->state != LabMateScopeDisplayUnsupported &&
           d->state != LabMateScopeDisplayError;
}

bool labmate_scope_display_draw(Canvas* c, const LabMateScopeDisplay* d) {
    /* Fail closed BEFORE the first pixel. Source is an IRQ-excluded copy. */
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
    } else if(d->plot.line_count) {
        return false;
    }
    for(uint16_t i = 0U; i < d->plot.line_count; ++i) {
        const LabMateScopePlotLine* p = &d->lines[i];
        if(p->x0 < LABMATE_SCOPE_PLOT_X_LEFT ||
           p->x0 > LABMATE_SCOPE_PLOT_X_RIGHT ||
           p->x1 < LABMATE_SCOPE_PLOT_X_LEFT ||
           p->x1 > LABMATE_SCOPE_PLOT_X_RIGHT ||
           (p->y0 != LABMATE_SCOPE_PLOT_Y_HIGH &&
            p->y0 != LABMATE_SCOPE_PLOT_Y_LOW) ||
           (p->y1 != LABMATE_SCOPE_PLOT_Y_HIGH &&
            p->y1 != LABMATE_SCOPE_PLOT_Y_LOW)) return false;
    }
    char count[20];
    const int count_len = snprintf(count, sizeof(count), "%u edges",
                                   (unsigned)d->total_edges);
    if(count_len < 0 || count_len > 14) return false;

    /* Consistent header: tool, page index and pin. Primary is used ONLY for
     * the heading or a single short empty-state message. */
    label(c, FontPrimary, 3, 11, "SCOPE");
    label(c, FontSecondary, 82, 9, "1/3");
    label(c, FontSecondary, 105, 9, "PC1");
    canvas_draw_line(c, 0, 13, 127, 13);

    /* Clean waveform window: frame and border-adjacent timing ticks only.
     * NO full-height grid lines through the waveform, NO fake trigger. */
    canvas_draw_line(c, 2, 15, 125, 15);
    canvas_draw_line(c, 2, 42, 125, 42);
    canvas_draw_line(c, 2, 15, 2, 42);
    canvas_draw_line(c, 125, 15, 125, 42);
    for(int32_t x = 33; x <= 95; x += 31) {
        canvas_draw_line(c, x, 16, x, 18);
        canvas_draw_line(c, x, 39, x, 41);
    }
    if(ready_trace(d)) {
        for(uint16_t i = 0U; i < d->plot.line_count; ++i) {
            const LabMateScopePlotLine* p = &d->lines[i];
            canvas_draw_line(c, p->x0, p->y0, p->x1, p->y1);
        }
    } else {
        const char* title = "READY";
        const char* info = "OK starts capture";
        int32_t title_x = 44;
        int32_t info_x = 16;
        if(d->state == LabMateScopeDisplayBusy) {
            title = "BUSY"; title_x = 47;
            info = "PC1 is in use"; info_x = 26;
        } else if(d->state == LabMateScopeDisplayUnsupported) {
            title = "UNAVAILABLE"; title_x = 16;
            info = "Firmware mismatch"; info_x = 16;
        } else if(d->state == LabMateScopeDisplayError ||
                  d->plot.result == LabMateScopePlotInvalid ||
                  d->plot.result == LabMateScopePlotTimebaseError) {
            title = "INVALID"; title_x = 35;
            info = "Check capture"; info_x = 29;
        } else if(d->plot.result == LabMateScopePlotOneEdge) {
            title = "1 EDGE"; title_x = 36;
            info = "Need another edge"; info_x = 13;
        } else if(d->state == LabMateScopeDisplayNoTrigger) {
            title = "NO SIGNAL"; title_x = 24;
            info = "Check PC1 input"; info_x = 20;
        } else if(d->state == LabMateScopeDisplayArmed ||
                  d->state == LabMateScopeDisplayRunning) {
            title = "LISTENING"; title_x = 24;
            info = "Waiting for edges"; info_x = 13;
        }
        label(c, FontPrimary, title_x, 30, title);
        label(c, FontSecondary, info_x, 39, info);
    }

    label(c, FontSecondary, 4, 51, count);
    const char* state = scope_status(d->state);
    if(d->plot.cropped_old_edges &&
       d->state != LabMateScopeDisplayError &&
       d->state != LabMateScopeDisplayBusy &&
       d->state != LabMateScopeDisplayUnsupported &&
       d->state != LabMateScopeDisplayNoTrigger) {
        /* Full count shown at left; FOCUS announces a cropped viewport. */
        label(c, FontSecondary, 69, 51, state);
        label(c, FontSecondary, 101, 51, "ZOOM");
    } else {
        const int32_t x = d->state == LabMateScopeDisplayUnsupported ? 61 :
                          d->state == LabMateScopeDisplayNoTrigger ? 70 :
                          d->state == LabMateScopeDisplayArmed ? 93 : 96;
        label(c, FontSecondary, x, 51, state);
    }
    footer(c, (d->state == LabMateScopeDisplayArmed ||
               d->state == LabMateScopeDisplayRunning) ? "OK STOP" : "OK RUN");
    return true;
}
