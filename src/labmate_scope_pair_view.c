#include "labmate_scope_pair_view.h"
#include <stdio.h>
#include <string.h>

/* All formats are bounded to the Flipper's 20-column secondary font.
 * No floating-point output and no extrapolation from a partial capture. */
static void format_frequency(char* out, size_t cap, uint64_t mhz, bool negative) {
    const char* unit = "Hz";
    uint64_t hundredths = (mhz + 5U) / 10U;
    if(mhz >= UINT64_C(1000000000)) {
        unit = "MHz";
        hundredths = (mhz + UINT64_C(5000000)) / UINT64_C(10000000);
    } else if(mhz >= UINT64_C(1000000)) {
        unit = "kHz";
        hundredths = (mhz + UINT64_C(5000)) / UINT64_C(10000);
    }
    if(hundredths > UINT32_MAX) {
        (void)snprintf(out, cap, "RANGE");
        return;
    }
    (void)snprintf(out, cap, "%s%lu.%02lu%s", negative ? "-" : "",
        (unsigned long)(hundredths / 100U),
        (unsigned long)(hundredths % 100U), unit);
}

static void metric_line(char* out, size_t cap, char prefix, const LabMateScopeMetrics* m) {
    char freq[20];
    format_frequency(freq, sizeof(freq), m->frequency_millihz, false);
    (void)snprintf(out, cap, "%c%s %s %u.%u%%", prefix,
        m->truncated ? "*" : ":", freq,
        (unsigned)(m->duty_permille / 10U),
        (unsigned)(m->duty_permille % 10U));
}

static void format_duration(char* out, size_t cap, uint64_t ticks, const LabMateScopeMetrics* m) {
    if(!m->timebase_hz || !m->completed_cycles ||
       ticks > UINT64_MAX / UINT64_C(1000000)) {
        (void)snprintf(out, cap, "RANGE");
        return;
    }
    const uint64_t divisor = (uint64_t)m->timebase_hz * m->completed_cycles;
    const uint64_t us = (ticks * UINT64_C(1000000) + divisor / 2U) / divisor;
    if(us >= 1000U) {
        const uint64_t centims = (us + 5U) / 10U;
        if(centims > UINT32_MAX) {
            (void)snprintf(out, cap, "RANGE");
            return;
        }
        (void)snprintf(out, cap, "%lu.%02lums",
            (unsigned long)(centims / 100U), (unsigned long)(centims % 100U));
    } else {
        (void)snprintf(out, cap, "%luus", (unsigned long)us);
    }
}

/* page=0 summary and B-A deltas; 1=A's genuine cycle averages; 2=B's.
 * If a single capture was only a PREFIX, use * in the heading; never
 * imply that it represents an unobserved complete test window. */
bool labmate_scope_pair_view_draw(Canvas* c, const LabMateScopePair* p,
                                   bool last_valid, uint8_t page) {
    if(!c || !p || page > 2U ||
       (p->has_b && (!p->has_a || !p->delta.comparable)) ||
       (p->has_a && (p->a.status != LabMateScopeMetricsReady ||
                     !p->a.completed_cycles)) ||
       (p->has_b && (p->b.status != LabMateScopeMetricsReady ||
                     !p->b.completed_cycles))) return false;

    /* Guard every dynamic text line BEFORE the first pixel. */
    char lines[4][48] = {{0}};
    const bool partial = (p->has_a && p->a.truncated) ||
                         (p->has_b && p->b.truncated);
    if(page == 0U) {
        if(!p->has_a) {
            (void)snprintf(lines[0], sizeof(lines[0]), "SAVE FIRST CAPTURE");
            (void)snprintf(lines[1], sizeof(lines[1]),
                "%s", last_valid ? "LEFT = STORE A" : "RUN, THEN STOP");
            (void)snprintf(lines[2], sizeof(lines[2]), "A/B USES ONE PC1");
        } else {
            metric_line(lines[0], sizeof(lines[0]), 'A', &p->a);
            if(!p->has_b) {
                (void)snprintf(lines[1], sizeof(lines[1]), "B: NOT SAVED");
                (void)snprintf(lines[2], sizeof(lines[2]),
                    "%s", last_valid ? "RIGHT = STORE NEW B" : "RUN NEW CAPTURE");
            } else {
                metric_line(lines[1], sizeof(lines[1]), 'B', &p->b);
                char frequency[20];
                const int64_t diff = p->delta.frequency_delta_millihz;
                const bool negative = diff < 0;
                const uint64_t magnitude = negative ?
                    (uint64_t)(-(diff + 1)) + 1U : (uint64_t)diff;
                format_frequency(frequency, sizeof(frequency), magnitude, false);
                (void)snprintf(lines[2], sizeof(lines[2]), "F DIFF %c%s",
                    negative ? '-' : '+', frequency);
                const int16_t dd = p->delta.duty_delta_permille;
                const uint16_t mag = dd < 0 ? (uint16_t)(-(int32_t)dd) : (uint16_t)dd;
                (void)snprintf(lines[3], sizeof(lines[3]), "D DIFF %c%u.%u%%",
                    dd < 0 ? '-' : '+', (unsigned)(mag / 10U),
                    (unsigned)(mag % 10U));
            }
        }
    } else {
        const LabMateScopeMetrics* m = page == 1U ? &p->a : &p->b;
        const bool exists = page == 1U ? p->has_a : p->has_b;
        if(!exists) {
            (void)snprintf(lines[0], sizeof(lines[0]),
                "%s", page == 1U ? "A: NOT SAVED" : "B: NOT SAVED");
            (void)snprintf(lines[1], sizeof(lines[1]), "RUN, STOP, SAVE");
        } else {
            char time[20];
            format_duration(time, sizeof(time), m->total_high_ticks, m);
            (void)snprintf(lines[0], sizeof(lines[0]), "HIGH    %s", time);
            format_duration(time, sizeof(time), m->total_low_ticks, m);
            (void)snprintf(lines[1], sizeof(lines[1]), "LOW     %s", time);
            format_duration(time, sizeof(time),
                m->total_high_ticks + m->total_low_ticks, m);
            (void)snprintf(lines[2], sizeof(lines[2]), "PERIOD  %s", time);
            (void)snprintf(lines[3], sizeof(lines[3]), "DUTY    %u.%u%%",
                (unsigned)(m->duty_permille / 10U),
                (unsigned)(m->duty_permille % 10U));
        }
    }
    for(unsigned i = 0U; i < 4U; ++i) {
        if(strlen(lines[i]) > 20U) return false;
    }

    canvas_set_font(c, FontSecondary);
    if(page == 0U)
        canvas_draw_str(c, 3, 9, partial ? "A/B *PARTIAL" : "A/B COMPARE");
    else
        canvas_draw_str(c, 3, 9, page == 1U ? "A DETAILS" : "B DETAILS");
    canvas_draw_str(c, 102, 9, "PC1");
    canvas_draw_line(c, 0, 13, 127, 13);
    const int32_t y[4] = {23, 32, 42, 51};
    for(unsigned i = 0U; i < 4U; ++i) {
        if(lines[i][0]) canvas_draw_str(c, 3, y[i], lines[i]);
    }
    canvas_draw_line(c, 0, 53, 127, 53);
    canvas_draw_str(c, 3, 62,
        page == 0U ? "UP:MORE DN:PG BK:OUT" : "UP:NEXT DN:PG BK:OUT");
    return true;
}
