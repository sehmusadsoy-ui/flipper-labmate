#include "labmate_scope_reference_view.h"
#include <stdio.h>
#include <string.h>

/* Four aligned labelled rows; no paragraphs, repeated errors or false PASS.
 * All GUI work is read-only, with a bounded 128x64 monochrome layout. */
static const char* verdict_text(LabMateScopeVerdict v) {
    switch(v) {
    case LabMateScopeVerdictPass: return "PASS";
    case LabMateScopeVerdictOutOfTolerance: return "OUT OF RANGE";
    case LabMateScopeVerdictNoSignal: return "NO SIGNAL";
    case LabMateScopeVerdictBusy: return "BUSY";
    case LabMateScopeVerdictInvalid:
    default: return "NO CAPTURE";
    }
}

static void label(Canvas* c, Font font, int32_t x, int32_t y, const char* s) {
    canvas_set_font(c, font);
    canvas_draw_str(c, x, y, s);
}

static bool right_value(Canvas* c, int32_t y, const char* value) {
    const size_t n = strlen(value);
    if(n > 11U) return false;
    label(c, FontSecondary, 124 - (int32_t)n * 6, y, value);
    return true;
}

bool labmate_scope_reference_view_draw(
    Canvas* c, LabMateScopeReferencePreset selected,
    LabMateScopeToleranceResult result, const LabMateScopeMetrics* measured) {
    if(!c || (unsigned)result.verdict > (unsigned)LabMateScopeVerdictBusy)
        return false;
    LabMateScopeReference ref = {0};
    if(!labmate_scope_reference_preset(selected, &ref)) return false;
    const bool complete =
        result.verdict == LabMateScopeVerdictPass ||
        result.verdict == LabMateScopeVerdictOutOfTolerance;
    if(complete &&
       (!measured || measured->status != LabMateScopeMetricsReady ||
        measured->truncated || measured->completed_cycles == 0U ||
        measured->frequency_millihz == 0U ||
        measured->duty_permille > 1000U)) return false;
    if(complete) {
        /* Do not reuse a stale PASS after changing reference or capture.
         * Exact mHz/permille comparison always precedes display rounding. */
        const LabMateScopeToleranceResult checked =
            labmate_scope_tolerance_evaluate(
                &ref, measured, LabMateScopeObservationComplete);
        if(checked.verdict != result.verdict ||
           checked.frequency_error_millihz != result.frequency_error_millihz ||
           checked.duty_error_permille != result.duty_error_permille)
            return false;
    }

    char freq[24] = "--";
    char duty[24] = "--";
    if(complete) {
        if(measured->frequency_millihz < UINT64_C(100000000)) {
            const uint64_t hz = measured->frequency_millihz / UINT64_C(1000);
            const uint64_t dec =
                (measured->frequency_millihz % UINT64_C(1000)) / UINT64_C(10);
            (void)snprintf(freq, sizeof(freq), "%lu.%02luHz",
                           (unsigned long)hz, (unsigned long)dec);
        } else {
            (void)snprintf(freq, sizeof(freq), ">99kHz");
        }
        (void)snprintf(duty, sizeof(duty), "%u.%u%%",
            (unsigned)(measured->duty_permille / 10U),
            (unsigned)(measured->duty_permille % 10U));
    }
    const char* verdict = verdict_text(result.verdict);
    /* All labels and values must fit their own columns BEFORE any paint. */
    if(strlen(ref.name) > 11U || strlen(freq) > 11U ||
       strlen(duty) > 11U || strlen(verdict) > 11U) return false;

    label(c, FontPrimary, 3, 11, "REFERENCE");
    label(c, FontSecondary, 82, 9, "3/3");
    label(c, FontSecondary, 105, 9, "PC1");
    canvas_draw_line(c, 0, 13, 127, 13);
    canvas_draw_line(c, 49, 16, 49, 52);

    label(c, FontSecondary, 4, 22, "TARGET");
    (void)right_value(c, 22, ref.name);
    label(c, FontSecondary, 4, 32, "FREQ");
    (void)right_value(c, 32, freq);
    label(c, FontSecondary, 4, 42, "DUTY");
    (void)right_value(c, 42, duty);
    label(c, FontSecondary, 4, 51, "RESULT");
    (void)right_value(c, 51, verdict);

    canvas_draw_line(c, 0, 54, 127, 54);
    canvas_draw_line(c, 46, 56, 46, 63);
    canvas_draw_line(c, 92, 56, 92, 63);
    label(c, FontSecondary, 3, 62, "^ REF");
    label(c, FontSecondary, 52, 62, "v PAGE");
    label(c, FontSecondary, 101, 62, "BACK");
    return true;
}
