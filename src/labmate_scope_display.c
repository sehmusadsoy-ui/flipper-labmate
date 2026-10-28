#include "labmate_scope_display.h"
#include "labmate_scope_ui.h"
#include "ui_kit.h"
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

    /* Scope Pixel Step 3: visual-only mapping. The 13 real captured
     * edge intervals are already validated above; translate y by +7
     * into the narrower pixel viewport without inventing a transition. */
    const bool active = d->state == LabMateScopeDisplayArmed ||
                        d->state == LabMateScopeDisplayRunning;
    const bool faulty_plot = d->plot.result == LabMateScopePlotInvalid ||
                             d->plot.result == LabMateScopePlotTimebaseError;
    const bool bad = d->state == LabMateScopeDisplayError || faulty_plot;
    UiKitInstrumentState chip = UiKitInstrumentReady;
    if(bad || d->state == LabMateScopeDisplayUnsupported)
        chip = UiKitInstrumentError;
    else if(d->state == LabMateScopeDisplayBusy)
        chip = UiKitInstrumentBusy;
    else if(active)
        chip = UiKitInstrumentLive;
    else if(measured)
        chip = UiKitInstrumentHeld;
    else if(d->state == LabMateScopeDisplayNoTrigger)
        chip = UiKitInstrumentWaiting;
    else if(d->state != LabMateScopeDisplayStopped || d->total_edges)
        chip = UiKitInstrumentStopped;

    if(!ui_kit_pixel_header(c, "Scope", true, chip, false)) return false;
    canvas_set_font(c, FontSecondary);
    canvas_set_color(c, ColorBlack);
    canvas_draw_str(c, 4U, 20U, "Pin PC1");
    (void)ui_kit_scope_page_dots(c, 0U);

    /* 124x21 rounded scope window; true sampled highs and lows at
     * y=27 and y=42. The capture plot remains at its measured x offsets. */
    canvas_draw_rframe(c, 2U, 24U, 124U, 21U, 3U);
    if(has_waveform(d) && !bad) {
        for(uint16_t i = 0U; i < d->plot.line_count; ++i) {
            const LabMateScopePlotLine* p = &d->lines[i];
            canvas_draw_line(c, p->x0, (int16_t)p->y0 + 7,
                             p->x1, (int16_t)p->y1 + 7);
        }
    } else if(chip == UiKitInstrumentReady && !d->total_edges) {
        /* Explicit empty-state decoration, not asserted to be a signal. */
        canvas_set_font(c, FontSecondary);
        canvas_draw_str(c, 19U, 33U, "Press OK to run");
        (void)ui_kit_pulse_line_dotted(c, 10U, 40U, 108U);
    } else {
        const char* message = "Listening...";
        if(d->state == LabMateScopeDisplayNoTrigger)
            message = "No signal";
        else if(d->state == LabMateScopeDisplayBusy)
            message = "PC1 busy";
        else if(d->state == LabMateScopeDisplayUnsupported)
            message = "Unavailable";
        else if(bad)
            message = "Invalid sample";
        else if(d->plot.result == LabMateScopePlotOneEdge)
            message = "Wait next edge";
        else if(!active)
            message = "No valid cycle";
        canvas_set_font(c, FontSecondary);
        const uint16_t message_width = canvas_string_width(c, message);
        if(message_width <= 116U)
            canvas_draw_str(c, (128U - message_width) / 2U, 35U, message);
    }

    /* Never show stale frequency during ARMED/LIVE, invalid or partial
     * captures. Completed metrics remain available after confirmed STOP. */
    const char* label = measured ? "Held" :
        bad ? "Error" : d->state == LabMateScopeDisplayBusy ? "Busy" :
        d->state == LabMateScopeDisplayUnsupported ? "Unavailable" :
        d->state == LabMateScopeDisplayNoTrigger ? "No signal" :
        active ? "Live" : d->total_edges ? "Stopped" : "Ready";
    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, 4U, 52U, label);
    if(measured) {
        canvas_draw_str(c, 42U, 52U, freq);
        canvas_draw_str(c, 97U, 52U, duty);
    } else {
        canvas_set_font(c, FontSecondary);
        const uint16_t edge_width = canvas_string_width(c, edges);
        if(edge_width <= 65U)
            canvas_draw_str(c, 125U - edge_width, 52U, edges);
    }

    /* DOWN changes page only when the native capture is no longer active.
     * BACK remains functional via the header chevron; OK retains Run/Stop. */
    (void)ui_kit_key_hint(c, 4U, UiKitKeyOk, active ? "Stop" : "Run");
    if(!active)
        (void)ui_kit_key_hint(c, 70U, UiKitKeyDown, "Next");
    canvas_set_color(c, ColorBlack);
    return true;

