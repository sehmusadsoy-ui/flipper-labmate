#include "labmate_scope_display.h"
#include "labmate_scope_ui.h"
#include <stdio.h>
#include <string.h>

/* Only verified, completed H-L-H samples are eligible for HOLD readings.
 * Display formatting never changes the full-precision measurement result. */
static bool scope_complete(const LabMateScopeDisplay* d) {
    const LabMateScopeMetrics* m = d->completed;
    return d->state == LabMateScopeDisplayStopped && m &&
           m->status == LabMateScopeMetricsReady &&
           m->completed_cycles > 0U && !m->truncated &&
           m->frequency_millihz > 0U && m->timebase_hz > 0U &&
           m->duty_permille <= 1000U;
}

static void scope_frequency(char* out, size_t cap, uint64_t mhz) {
    if(mhz >= UINT64_C(100000000)) {
        (void)snprintf(out, cap, ">99kHz");
    } else if(mhz >= UINT64_C(1000000)) {
        const uint64_t rounded = (mhz + 5000U) / 10000U;
        (void)snprintf(out, cap, "%lu.%02lukHz",
            (unsigned long)(rounded / 100U),
            (unsigned long)(rounded % 100U));
    } else {
        const uint64_t rounded = (mhz + 5U) / 10U;
        (void)snprintf(out, cap, "%lu.%02luHz",
            (unsigned long)(rounded / 100U),
            (unsigned long)(rounded % 100U));
    }
}

static const char* status_name(LabMateScopeDisplayState s) {
    switch(s) {
    case LabMateScopeDisplayArmed: return "ARMED";
    case LabMateScopeDisplayRunning: return "LIVE";
    case LabMateScopeDisplayStopped: return "HOLD";
    case LabMateScopeDisplayNoTrigger: return "NO SIG";
    case LabMateScopeDisplayQuiet: return "QUIET";
    case LabMateScopeDisplayFull: return "FULL";
    case LabMateScopeDisplayBusy: return "BUSY";
    case LabMateScopeDisplayUnsupported: return "UNSUP";
    case LabMateScopeDisplayError: return "ERROR";
    default: return "ERROR";
    }
}

static bool has_waveform(const LabMateScopeDisplay* d) {
    return d->plot.result == LabMateScopePlotReady &&
           d->state != LabMateScopeDisplayBusy &&
           d->state != LabMateScopeDisplayUnsupported &&
           d->state != LabMateScopeDisplayError;
}

bool labmate_scope_display_draw(Canvas* c, const LabMateScopeDisplay* d) {
    /* Preflight all copied geometry and status strings before any paint. */
    if(!c || !d ||
       (unsigned)d->state > (unsigned)LabMateScopeDisplayError ||
       (unsigned)d->plot.result > (unsigned)LabMateScopePlotTimebaseError ||
       d->total_edges > LABMATE_SCOPE_MAX_EDGES ||
       d->plot.visible_edges > LABMATE_SCOPE_PLOT_MAX_EDGES ||
       d->plot.visible_edges > d->total_edges ||
       d->plot.line_count > LABMATE_SCOPE_PLOT_MAX_LINES ||
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
    char freq[20] = {0}, duty[16] = {0}, edges[20] = {0};
    const bool measured = scope_complete(d);
    if(measured) {
        scope_frequency(freq, sizeof(freq), d->completed->frequency_millihz);
        (void)snprintf(duty, sizeof(duty), "%u.%u%%",
            (unsigned)(d->completed->duty_permille / 10U),
            (unsigned)(d->completed->duty_permille % 10U));
        if(strlen(freq) > 8U || strlen(duty) > 5U) return false;
    } else {
        (void)snprintf(edges, sizeof(edges), "%u edges",
            (unsigned)d->total_edges);
        if(strlen(edges) > 9U) return false;
    }

    (void)labmate_scope_ui_header(c, "SCOPE", "1/4");

    /* Physically distinct 123x28 oscilloscope viewport. True measured
     * edges alone create trace segments; dots are uncalibrated guides. */
    canvas_draw_line(c, 2, 15, 125, 15);
    canvas_draw_line(c, 2, 42, 125, 42);
    canvas_draw_line(c, 2, 15, 2, 42);
    canvas_draw_line(c, 125, 15, 125, 42);
    for(int32_t x = 25; x <= 105; x += 20) {
        canvas_draw_line(c, x, 16, x, 17);
        canvas_draw_line(c, x, 40, x, 41);
    }
    if(has_waveform(d)) {
        /* Keep text-only empty states free of grid strokes behind glyphs. */
        for(int32_t x = 14; x <= 110; x += 16)
            canvas_draw_line(c, x, 28, x + 1, 28);
        for(uint16_t i = 0U; i < d->plot.line_count; ++i) {
            const LabMateScopePlotLine* p = &d->lines[i];
            canvas_draw_line(c, p->x0, p->y0, p->x1, p->y1);
        }
    } else {
        const char* headline = "READY";
        if(d->state == LabMateScopeDisplayNoTrigger) headline = "NO SIGNAL";
        else if(d->state == LabMateScopeDisplayBusy) headline = "PC1 BUSY";
        else if(d->state == LabMateScopeDisplayUnsupported) headline = "UNAVAILABLE";
        else if(d->state == LabMateScopeDisplayError ||
                d->plot.result == LabMateScopePlotInvalid ||
                d->plot.result == LabMateScopePlotTimebaseError)
            headline = "INVALID";
        else if(d->plot.result == LabMateScopePlotOneEdge)
            headline = "WAIT EDGE";
        else if(d->state == LabMateScopeDisplayArmed ||
                d->state == LabMateScopeDisplayRunning)
            headline = "LISTENING";
        /* FontSecondary, <= 11 characters, entirely inside viewport. */
        const int32_t center_x = 64 - (int32_t)strlen(headline) * 3;
        labmate_scope_ui_text(c, FontSecondary, center_x, 30, headline);
    }

    labmate_scope_ui_text(c, FontSecondary, 3, 51, status_name(d->state));
    if(measured) {
        labmate_scope_ui_text(c, FontSecondary, 42, 51, freq);
        labmate_scope_ui_text(c, FontSecondary, 97, 51, duty);
    } else {
        /* Never show a stale frequency with invalid/armed measurements. */
        labmate_scope_ui_text(c, FontSecondary, 73, 51, edges);
    }
    const bool active = d->state == LabMateScopeDisplayArmed ||
                        d->state == LabMateScopeDisplayRunning;
    (void)labmate_scope_ui_footer(c, active ? "(OK)Stop" : "(OK)Run",
        active ? "" : "(v)Pg");
    return true;
}
