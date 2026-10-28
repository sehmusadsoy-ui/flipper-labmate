#include "labmate_scope_pair_view.h"
#include "labmate_scope_ui.h"
#include "ui_kit.h"
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
    return m->status == LabMateScopeMetricsReady && !m->truncated &&
           m->completed_cycles > 0U && m->edge_count >= 3U &&
           m->edge_count <= LABMATE_SCOPE_MAX_EDGES &&
           m->timebase_hz > 0U && m->frequency_millihz > 0U &&
           m->frequency_millihz <= (uint64_t)m->timebase_hz * 500U &&
           m->duty_permille <= 1000U && m->min_period_ticks >= 2U &&
           m->max_period_ticks >= m->min_period_ticks &&
           m->total_high_ticks <= UINT64_MAX - m->total_low_ticks;
}

bool labmate_scope_pair_view_draw(Canvas* c, const LabMateScopePair* p,
                                  bool last_valid, uint8_t page) {
    if(!c || !p || page > 2U ||
       (p->has_a && p->generation_a == 0U) ||
       (p->has_b && (!p->has_a || !p->delta.comparable ||
                     p->generation_b <= p->generation_a)) ||
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

    /* Step 4 pixel layout: A/B are two distinct finished PC1 captures,
     * not concurrent channels. No waveform is stored in LabMateScopePair;
     * do not invent a trace from aggregate frequency/duty statistics. */
    canvas_set_font(c, FontSecondary);
    const uint16_t af_w = canvas_string_width(c, af);
    const uint16_t bf_w = canvas_string_width(c, bf);
    const uint16_t df_w = p->has_b ? canvas_string_width(c, df) : 0U;
    if(af_w > 54U || bf_w > 54U || (p->has_b && df_w > 100U))
        return false;
    if(page != 0U && saved) {
        const char* labels[] = {"Frequency", "Duty", "High", "Low"};
        for(uint8_t i = 0U; i < 4U; ++i) {
            const uint16_t lw = canvas_string_width(c, labels[i]);
            const uint16_t vw = canvas_string_width(c, detail[i]);
            if(!vw || 4U + lw + 5U > 124U - vw) return false;
        }
    }
    const char* title = page == 0U ? "Compare" :
                        page == 1U ? "Sample A" : "Sample B";
    /* Preflight every variable string before painting; reject out-of-range
     * dimensions rather than cropping measurement digits. */
    canvas_set_font(c, FontPrimary);
    if(9U + canvas_string_width(c, title) > 127U) return false;
    if(!ui_kit_pixel_header(c, title, false, UiKitInstrumentReady, false))
        return false;
    canvas_set_color(c, ColorBlack);
    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, 4U, 20U, "Pin PC1");
    if(!ui_kit_scope_page_dots(c, page == 0U ? 1U : 2U))
        return false;

    if(page == 0U) {
        /* Two independent sample cards; unsaved B must stay visibly EMPTY,
         * never "0 Hz" or a repeated copy of A. */
        canvas_draw_rframe(c, 4U, 25U, 58U, 21U, 3U);
        canvas_draw_rframe(c, 66U, 25U, 58U, 21U, 3U);
        canvas_set_font(c, FontSecondary);
        canvas_draw_str(c, 8U, 33U, "A");
        canvas_draw_str(c, 70U, 33U, "B");
        const char* av = p->has_a ? af : "Empty";
        const char* bv = p->has_b ? bf : "Empty";
        const uint16_t aw = canvas_string_width(c, av);
        const uint16_t bw = canvas_string_width(c, bv);
        canvas_draw_str(c, 4U + (58U - aw) / 2U, 43U, av);
        canvas_draw_str(c, 66U + (58U - bw) / 2U, 43U, bv);

        if(p->has_b) {
            /* Real B-A FREQUENCY difference, not an invented relative %
             * delta. Full value stays visible with a measured short label
             * only when the long heading would collide. */
            const char* label =
                4U + canvas_string_width(c, "Frequency") + 5U <= 124U - df_w ?
                    "Frequency" : "dF";
            canvas_draw_str(c, 4U, 53U, label);
            canvas_draw_str(c, 124U - df_w, 53U, df);
        } else {
            const char* instruction = p->has_a ?
                (last_valid ? "RIGHT saves B" : "Capture new B") :
                (last_valid ? "LEFT saves A" : "Capture then save");
            canvas_draw_str(c, 4U, 53U, instruction);
        }
    } else if(!saved) {
        canvas_draw_rframe(c, 4U, 25U, 120U, 12U, 3U);
        /* Distinct decorative "not captured" dash; NOT a fabricated wave. */
        (void)ui_kit_pulse_line_dotted(c, 9U, 33U, 108U);
        canvas_set_font(c, FontPrimary);
        canvas_draw_str(c, 20U, 46U,
                        page == 1U ? "No sample A" : "No sample B");
        canvas_set_font(c, FontSecondary);
        canvas_draw_str(c, 10U, 54U, "Capture then save");
    } else {
        /* No authentic per-sample edge history is retained; use four
         * real metrics instead of rendering a fictional oscilloscope wave.
         * The fifth metric (Period) remains in the underlying data/engine. */
        const char* labels[] = {"Frequency", "Duty", "High", "Low"};
        const uint8_t ys[] = {30U, 38U, 46U, 54U};
        canvas_set_font(c, FontSecondary);
        for(uint8_t i = 0U; i < 4U; ++i) {
            const uint16_t width = canvas_string_width(c, detail[i]);
            canvas_draw_str(c, 4U, ys[i], labels[i]);
            canvas_draw_str(c, 124U - width, ys[i], detail[i]);
        }
    }

    /* DOWN still advances Compare -> Details -> Reference, even with
     * missing saved samples. UP continues switching A/B when B exists.
     * LEFT/RIGHT/OK input logic stays in labmate_scope_bridge.c. */
    ui_kit_next_cue(c);
    canvas_set_color(c, ColorBlack);
    return true;
}

