#include "labmate_scope_pair_view.h"
#include <stdio.h>
#include <string.h>

static void format_frequency(char* out, size_t cap, uint64_t mhz, bool negative) {
    /* Units are milli-Hz, not raw ticks. Use integer hundredths, never %f.
     * Magnitude is bounded by valid PC1 captured edge-clock arithmetic. */
    const char* units = "Hz";
    uint64_t hundredths = (mhz + 5U) / 10U;
    if(mhz >= UINT64_C(1000000000)) {
        units = "MHz";
        hundredths = (mhz + UINT64_C(5000000)) / UINT64_C(10000000);
    } else if(mhz >= UINT64_C(1000000)) {
        units = "kHz";
        hundredths = (mhz + UINT64_C(5000)) / UINT64_C(10000);
    }
    /* Out-of-range numbers never become unbounded LCD text. */
    if(hundredths > UINT32_MAX) {
        (void)snprintf(out, cap, "RANGE");
        return;
    }
    (void)snprintf(out, cap, "%s%lu.%02lu%s", negative ? "-" : "",
                   (unsigned long)(hundredths / 100U),
                   (unsigned long)(hundredths % 100U), units);
}
static void metric_line(char* out, size_t cap, char prefix, const LabMateScopeMetrics* m) {
    char f[19];
    format_frequency(f, sizeof(f), m->frequency_millihz, false);
    (void)snprintf(out, cap, "%c%s %s %u.%u%%", prefix,
                   m->truncated ? "*" : "", f,
                   (unsigned)(m->duty_permille / 10U),
                   (unsigned)(m->duty_permille % 10U));
}
bool labmate_scope_pair_view_draw(Canvas* c, const LabMateScopePair* p,
                                  bool last_valid) {
    if(!c || !p || (p->has_b && (!p->has_a || !p->delta.comparable)) ||
       (p->has_a && (p->a.status != LabMateScopeMetricsReady ||
                     !p->a.completed_cycles)) ||
       (p->has_b && (p->b.status != LabMateScopeMetricsReady ||
                     !p->b.completed_cycles))) return false;
    canvas_set_font(c, FontSecondary);
    /* An asterisk denotes only the measured PREFIX of a saturated
     * 256-edge buffer, NOT a 5-second full signal reconstruction. */
    const bool clipped = (p->has_a && p->a.truncated) ||
                         (p->has_b && p->b.truncated);
    canvas_draw_str(c, 3, 9, clipped ? "A/B *PREFIX ONLY" : "COMPARE PC1 A/B");
    canvas_draw_line(c, 0, 13, 127, 13);
    if(!p->has_a) {
        canvas_draw_str(c, 3, 24, "CAPTURE THEN STOP");
        canvas_draw_str(c, 3, 35, "LEFT: SAVE A");
        canvas_draw_str(c, 3, 46, last_valid ? "A READY TO SAVE" : "NEED FULL CYCLE");
    } else {
        /* Larger temporary protects snprintf's compile-time worst case;
         * the explicit 20-glyph check below remains the actual LCD limit. */
        char line[48];
        metric_line(line, sizeof(line), 'A', &p->a);
        /* FontSecondary is 6px/glyph; max 20 chars from x=3. */
        if(strlen(line) > 20U) return false;
        canvas_draw_str(c, 3, 24, line);
        if(!p->has_b) {
            canvas_draw_str(c, 3, 35, "RUN NEW PC1 FOR B");
            canvas_draw_str(c, 3, 46, last_valid ? "RIGHT: SAVE B" : "NO FRESH B YET");
        } else {
            metric_line(line, sizeof(line), 'B', &p->b);
            if(strlen(line) > 20U) return false;
            canvas_draw_str(c, 3, 33, line);
            char f[19];
            const int64_t signed_delta = p->delta.frequency_delta_millihz;
            const bool neg = signed_delta < 0;
            const uint64_t magnitude = neg ?
                (uint64_t)(-(signed_delta + 1)) + 1U : (uint64_t)signed_delta;
            format_frequency(f, sizeof(f), magnitude, false);
            (void)snprintf(line, sizeof(line), "dF %c%s", neg ? '-' : '+', f);
            if(strlen(line) > 20U) return false;
            canvas_draw_str(c, 3, 42, line);
            const int16_t dd = p->delta.duty_delta_permille;
            const uint16_t magnitude_dd = dd < 0 ? (uint16_t)(-(int32_t)dd) :
                                                (uint16_t)dd;
            (void)snprintf(line, sizeof(line), "dD %c%u.%u%%",
                           dd < 0 ? '-' : '+', (unsigned)(magnitude_dd / 10U),
                           (unsigned)(magnitude_dd % 10U));
            if(strlen(line) > 20U) return false;
            canvas_draw_str(c, 3, 51, line);
        }
    }
    canvas_draw_line(c, 0, 54, 127, 54);
    canvas_draw_str(c, 3, 62, "DN PLOT BK EXIT");
    return true;
}
