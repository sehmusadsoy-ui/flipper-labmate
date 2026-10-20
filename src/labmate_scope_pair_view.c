#include "labmate_scope_pair_view.h"
#include "labmate_scope_ui.h"
#include <stdio.h>
#include <string.h>

/* A and B are SEQUENTIAL captures from PC1. Do not invent dual channels.
 * All LCD text is formatted and bounds-checked before the first pixel. */
static void frequency(char* out, size_t cap, uint64_t mhz) {
    if(mhz >= UINT64_C(100000000)) {
        (void)snprintf(out, cap, ">99kHz");
        return;
    }
    const bool khz = mhz >= UINT64_C(1000000);
    const uint64_t cents = khz ? (mhz + 5000U) / 10000U :
                                  (mhz + 5U) / 10U;
    (void)snprintf(out, cap, "%lu.%02lu%s",
        (unsigned long)(cents / 100U),
        (unsigned long)(cents % 100U), khz ? "kHz" : "Hz");
}

static void duration(char* out, size_t cap, uint64_t ticks,
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
    if(us >= 1000U) {
        const uint64_t hundredths = (us + 5U) / 10U;
        if(hundredths > UINT32_MAX) {
            (void)snprintf(out, cap, "RANGE");
            return;
        }
        (void)snprintf(out, cap, "%lu.%02lums",
            (unsigned long)(hundredths / 100U),
            (unsigned long)(hundredths % 100U));
    } else {
        (void)snprintf(out, cap, "%luus", (unsigned long)us);
    }
}

static bool metric_valid(const LabMateScopeMetrics* m) {
    return m->status == LabMateScopeMetricsReady &&
           m->completed_cycles > 0U && m->timebase_hz > 0U &&
           m->duty_permille <= 1000U &&
           m->total_high_ticks <= UINT64_MAX - m->total_low_ticks;
}

static void aligned_value(Canvas* c, int32_t y, const char* value) {
    const int32_t x = 124 - (int32_t)strlen(value) * 6;
    labmate_scope_ui_text(c, FontSecondary, x, y, value);
}

bool labmate_scope_pair_view_draw(Canvas* c, const LabMateScopePair* p,
                                  bool last_valid, uint8_t page) {
    if(!c || !p || page > 2U ||
       (p->has_b && (!p->has_a || !p->delta.comparable)) ||
       (p->has_a && !metric_valid(&p->a)) ||
       (p->has_b && !metric_valid(&p->b))) return false;

    char af[20] = "--", bf[20] = "--";
    char ad[12] = "--", bd[12] = "--";
    char df[24] = {0}, dd[16] = {0};
    char detail[5][24] = {{0}};
    if(p->has_a) {
        frequency(af, sizeof(af), p->a.frequency_millihz);
        (void)snprintf(ad, sizeof(ad), "%u.%u%%",
            (unsigned)(p->a.duty_permille / 10U),
            (unsigned)(p->a.duty_permille % 10U));
    }
    if(p->has_b) {
        frequency(bf, sizeof(bf), p->b.frequency_millihz);
        (void)snprintf(bd, sizeof(bd), "%u.%u%%",
            (unsigned)(p->b.duty_permille / 10U),
            (unsigned)(p->b.duty_permille % 10U));
        const int64_t difference = p->delta.frequency_delta_millihz;
        const bool neg = difference < 0;
        const uint64_t mag = neg ?
            (uint64_t)(-(difference + 1)) + 1U : (uint64_t)difference;
        char val[20];
        frequency(val, sizeof(val), mag);
        (void)snprintf(df, sizeof(df), "%c%s", neg ? '-' : '+', val);
        const int16_t delta = p->delta.duty_delta_permille;
        const uint16_t abs_d = delta < 0 ?
            (uint16_t)(-(int32_t)delta) : (uint16_t)delta;
        (void)snprintf(dd, sizeof(dd), "%c%u.%u%%", delta < 0 ? '-' : '+',
            (unsigned)(abs_d / 10U), (unsigned)(abs_d % 10U));
    }

    const LabMateScopeMetrics* m = page == 2U ? &p->b : &p->a;
    const bool saved = page == 1U ? p->has_a :
                       page == 2U ? p->has_b : false;
    if(page != 0U && saved) {
        frequency(detail[0], sizeof(detail[0]), m->frequency_millihz);
        (void)snprintf(detail[1], sizeof(detail[1]), "%u.%u%%",
            (unsigned)(m->duty_permille / 10U),
            (unsigned)(m->duty_permille % 10U));
        duration(detail[2], sizeof(detail[2]), m->total_high_ticks, m);
        duration(detail[3], sizeof(detail[3]), m->total_low_ticks, m);
        duration(detail[4], sizeof(detail[4]),
            m->total_high_ticks + m->total_low_ticks, m);
    }
    if(strlen(af) > 8U || strlen(bf) > 8U ||
       strlen(ad) > 6U || strlen(bd) > 6U ||
       strlen(df) > 13U || strlen(dd) > 8U) return false;
    for(uint8_t i = 0; i < 5U; ++i)
        if(strlen(detail[i]) > 10U) return false;

    if(page == 0U) {
        (void)labmate_scope_ui_header(c, "COMPARE", "2/4");
        if(!p->has_a) {
            /* One restrained empty-state instead of an instruction wall. */
            labmate_scope_ui_text(c, FontPrimary, 27, 29, "A  /  B");
            labmate_scope_ui_text(c, FontSecondary, 16, 45, "No saved samples");
        } else {
            labmate_scope_ui_text(c, FontSecondary, 4, 23,
                p->a.truncated ? "A*" : "A");
            labmate_scope_ui_text(c, FontSecondary, 21, 23, af);
            labmate_scope_ui_text(c, FontSecondary, 90, 23, ad);
            labmate_scope_ui_text(c, FontSecondary, 4, 32,
                p->has_b && p->b.truncated ? "B*" : "B");
            labmate_scope_ui_text(c, FontSecondary, 21, 32, bf);
            labmate_scope_ui_text(c, FontSecondary, 90, 32, bd);
            canvas_draw_line(c, 4, 36, 123, 36);
            if(p->has_b) {
                labmate_scope_ui_text(c, FontSecondary, 4, 44, "dF");
                labmate_scope_ui_text(c, FontSecondary, 27, 44, df);
                labmate_scope_ui_text(c, FontSecondary, 4, 52, "dD");
                labmate_scope_ui_text(c, FontSecondary, 27, 52, dd);
            } else {
                labmate_scope_ui_text(c, FontSecondary, 8, 49, "B not saved");
            }
        }
        const char* action =
            !p->has_a ? (last_valid ? "(<)Save" : "(OK)Run") :
            !p->has_b ? (last_valid ? "(>)Save" : "(OK)Run") :
            "(^)More";
        (void)labmate_scope_ui_footer(c, action, "(v)Pg");
    } else {
        (void)labmate_scope_ui_header(
            c, page == 1U ? "A DETAIL" : "B DETAIL", "3/4");
        if(!saved) {
            labmate_scope_ui_text(c, FontSecondary, 23, 30,
                page == 1U ? "No sample A" : "No sample B");
            labmate_scope_ui_text(c, FontSecondary, 14, 44,
                "Capture and save");
        } else {
            const char* label[] = {"FREQ", "DUTY", "HIGH", "LOW", "PERIOD"};
            const int32_t rows[] = {21, 29, 37, 45, 53};
            for(uint8_t i = 0U; i < 5U; ++i) {
                labmate_scope_ui_text(c, FontSecondary, 4, rows[i], label[i]);
                aligned_value(c, rows[i], detail[i]);
            }
        }
        (void)labmate_scope_ui_footer(
            c, p->has_a && p->has_b ? "(^)Next" : "", "(v)Pg");
    }
    return true;
}
