#include "labmate_scope_pair_view.h"
#include <stdio.h>
#include <string.h>

/* LabMate's 128x64 A/B layout deliberately uses two quiet aligned columns:
 * source name -> measured value, with a distinct right-aligned duty column.
 * A and B are sequential captures on ONE PC1, never simultaneous channels. */
static void label(Canvas* c, Font font, int32_t x, int32_t y, const char* s) {
    canvas_set_font(c, font);
    canvas_draw_str(c, x, y, s);
}

static void footer(Canvas* c, const char* action) {
    canvas_draw_line(c, 0, 54, 127, 54);
    canvas_draw_line(c, 46, 56, 46, 63);
    canvas_draw_line(c, 92, 56, 92, 63);
    label(c, FontSecondary, 3, 62, action);
    label(c, FontSecondary, 52, 62, "v PAGE");
    label(c, FontSecondary, 101, 62, "BACK");
}

static void format_frequency(char* out, size_t cap, uint64_t mhz) {
    const char* units = "Hz";
    uint64_t hundreds;
    if(mhz > UINT64_C(999999999999)) {
        (void)snprintf(out, cap, "RANGE");
        return;
    }
    if(mhz >= UINT64_C(1000000000)) {
        units = "MHz";
        hundreds = (mhz + UINT64_C(5000000)) / UINT64_C(10000000);
    } else if(mhz >= UINT64_C(1000000)) {
        units = "kHz";
        hundreds = (mhz + UINT64_C(5000)) / UINT64_C(10000);
    } else {
        hundreds = (mhz + 5U) / 10U;
    }
    if(hundreds > UINT32_MAX) {
        (void)snprintf(out, cap, "RANGE");
        return;
    }
    (void)snprintf(out, cap, "%lu.%02lu%s",
                   (unsigned long)(hundreds / 100U),
                   (unsigned long)(hundreds % 100U), units);
}

/* Mean observed high/low interval over complete H-L-H cycles. Never
 * generate intervals outside the observed edges or claim calibrated time. */
static void format_duration(char* out, size_t cap, uint64_t ticks,
                            const LabMateScopeMetrics* m) {
    if(!m->timebase_hz || !m->completed_cycles) {
        (void)snprintf(out, cap, "RANGE");
        return;
    }
    const uint64_t divisor = (uint64_t)m->timebase_hz * m->completed_cycles;
    if(ticks > (UINT64_MAX - divisor / 2U) / UINT64_C(1000000)) {
        (void)snprintf(out, cap, "RANGE");
        return;
    }
    const uint64_t us = (ticks * UINT64_C(1000000) + divisor / 2U) / divisor;
    if(us >= UINT64_C(1000)) {
        if(us > UINT64_C(42949672950)) {
            (void)snprintf(out, cap, "RANGE");
            return;
        }
        const uint64_t centims = (us + 5U) / 10U;
        if(centims > UINT32_MAX) {
            (void)snprintf(out, cap, "RANGE");
            return;
        }
        (void)snprintf(out, cap, "%lu.%02lums",
            (unsigned long)(centims / 100U),
            (unsigned long)(centims % 100U));
    } else {
        (void)snprintf(out, cap, "%luus", (unsigned long)us);
    }
}

static bool valid_metrics(const LabMateScopeMetrics* m) {
    return m->status == LabMateScopeMetricsReady &&
           m->completed_cycles > 0U && m->timebase_hz > 0U &&
           m->duty_permille <= 1000U &&
           m->total_high_ticks <= UINT64_MAX - m->total_low_ticks;
}

static void measured_row(Canvas* c, int32_t y, char id, bool partial,
                         const char* frequency, const char* duty) {
    char id_s[] = {id, partial ? '*' : '\0', '\0'};
    label(c, FontSecondary, 5, y, id_s);
    label(c, FontSecondary, 24, y, frequency);
    if(duty[0]) label(c, FontSecondary, 90, y, duty);
}

bool labmate_scope_pair_view_draw(Canvas* c, const LabMateScopePair* p,
                                  bool last_valid, uint8_t page) {
    if(!c || !p || page > 2U ||
       (p->has_b && (!p->has_a || !p->delta.comparable)) ||
       (p->has_a && !valid_metrics(&p->a)) ||
       (p->has_b && !valid_metrics(&p->b))) return false;

    /* Format and check ALL dynamic text before changing the framebuffer. */
    char a_freq[20] = "--", b_freq[20] = "--";
    char a_duty[16] = "", b_duty[16] = "";
    char d_freq[20] = "", d_duty[20] = "";
    char times[4][20] = {{0}};
    const LabMateScopeMetrics* m = page == 1U ? &p->a : &p->b;
    const bool saved = page == 1U ? p->has_a : p->has_b;

    if(p->has_a) {
        format_frequency(a_freq, sizeof(a_freq), p->a.frequency_millihz);
        (void)snprintf(a_duty, sizeof(a_duty), "%u.%u%%",
            (unsigned)(p->a.duty_permille / 10U),
            (unsigned)(p->a.duty_permille % 10U));
    }
    if(p->has_b) {
        format_frequency(b_freq, sizeof(b_freq), p->b.frequency_millihz);
        (void)snprintf(b_duty, sizeof(b_duty), "%u.%u%%",
            (unsigned)(p->b.duty_permille / 10U),
            (unsigned)(p->b.duty_permille % 10U));
        const int64_t df = p->delta.frequency_delta_millihz;
        const bool negative = df < 0;
        const uint64_t mag = negative ?
            (uint64_t)(-(df + 1)) + 1U : (uint64_t)df;
        char frequency[20];
        format_frequency(frequency, sizeof(frequency), mag);
        (void)snprintf(d_freq, sizeof(d_freq), "%c%s", negative ? '-' : '+', frequency);
        const int16_t dd = p->delta.duty_delta_permille;
        const uint16_t abs_dd = dd < 0 ? (uint16_t)(-(int32_t)dd) : (uint16_t)dd;
        (void)snprintf(d_duty, sizeof(d_duty), "%c%u.%u%%",
                       dd < 0 ? '-' : '+',
                       (unsigned)(abs_dd / 10U), (unsigned)(abs_dd % 10U));
    }
    if(page != 0U && saved) {
        format_duration(times[0], sizeof(times[0]), m->total_high_ticks, m);
        format_duration(times[1], sizeof(times[1]), m->total_low_ticks, m);
        format_duration(times[2], sizeof(times[2]),
                        m->total_high_ticks + m->total_low_ticks, m);
        (void)snprintf(times[3], sizeof(times[3]), "%u.%u%%",
                       (unsigned)(m->duty_permille / 10U),
                       (unsigned)(m->duty_permille % 10U));
    }
    if(strlen(a_freq) > 10U || strlen(b_freq) > 10U ||
       strlen(a_duty) > 6U || strlen(b_duty) > 6U ||
       strlen(d_freq) > 11U || strlen(d_duty) > 9U)
        return false;
    for(uint8_t i = 0U; i < 4U; ++i)
        if(strlen(times[i]) > 9U) return false; /* right-hand column */

    const bool partial = (p->has_a && p->a.truncated) ||
                         (p->has_b && p->b.truncated);
    if(page == 0U) {
        label(c, FontPrimary, 3, 11, "COMPARE");
    } else {
        label(c, FontPrimary, 3, 11, page == 1U ? "A DETAILS" : "B DETAILS");
    }
    label(c, FontSecondary, 82, 9, "2/3");
    label(c, FontSecondary, 105, 9, "PC1");
    canvas_draw_line(c, 0, 13, 127, 13);

    if(page != 0U) {
        if(!saved) {
            label(c, FontPrimary, 23, 30, "NOT SAVED");
            label(c, FontSecondary, 22, 43, "Save a capture first");
        } else {
            const char* row[4] = {"HIGH", "LOW", "PERIOD", "DUTY"};
            const int32_t y[4] = {22, 31, 40, 50};
            canvas_draw_line(c, 68, 17, 68, 52);
            for(uint8_t i = 0U; i < 4U; ++i) {
                label(c, FontSecondary, 5, y[i], row[i]);
                const int32_t x = 124 - (int32_t)strlen(times[i]) * 6;
                label(c, FontSecondary, x, y[i], times[i]);
            }
        }
        footer(c, "^ NEXT");
    } else if(!p->has_a) {
        /* Empty slots communicate the A/B concept without a wall of help. */
        canvas_draw_line(c, 63, 17, 63, 42);
        label(c, FontPrimary, 24, 28, "A");
        label(c, FontPrimary, 87, 28, "B");
        label(c, FontSecondary, 24, 40, "--");
        label(c, FontSecondary, 87, 40, "--");
        label(c, FontSecondary, 11, 51,
              last_valid ? "LEFT: save A now" : "Run, stop, save A");
        footer(c, last_valid ? "< SAVE" : "OK RUN");
    } else {
        canvas_draw_line(c, 19, 16, 19, 32);
        measured_row(c, 22, 'A', p->a.truncated, a_freq, a_duty);
        measured_row(c, 31, 'B', p->has_b && p->b.truncated, b_freq, b_duty);
        canvas_draw_line(c, 4, 34, 123, 34);
        if(!p->has_b) {
            label(c, FontSecondary, 6, 46,
                last_valid ? "RIGHT saves B" : "Capture B next");
        } else {
            label(c, FontSecondary, 5, 43, "F change");
            label(c, FontSecondary, 58, 43, d_freq);
            label(c, FontSecondary, 5, 52, "D change");
            label(c, FontSecondary, 58, 52, d_duty);
            (void)partial; /* A* / B* already identify measured prefix only. */
        }
        footer(c, !p->has_b ? (last_valid ? "> SAVE" : "OK RUN") : "^ MORE");
    }
    return true;
}
