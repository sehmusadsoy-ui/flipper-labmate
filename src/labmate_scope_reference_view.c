#include "labmate_scope_reference_view.h"
#include "labmate_scope_ui.h"
#include <stdio.h>
#include <string.h>

/* Exact comparison is independent of rendering and number formatting.
 * A stale PASS after changing target or capture is always rejected. */
static const char* verdict_label(LabMateScopeVerdict verdict) {
    switch(verdict) {
    case LabMateScopeVerdictPass: return "PASS";
    case LabMateScopeVerdictOutOfTolerance: return "FAIL";
    case LabMateScopeVerdictNoSignal: return "NO SIGNAL";
    case LabMateScopeVerdictBusy: return "BUSY";
    case LabMateScopeVerdictInvalid:
    default: return "WAIT";
    }
}

static void right_value(Canvas* c, int32_t y, const char* s) {
    labmate_scope_ui_text(c, FontSecondary,
        124 - (int32_t)strlen(s) * 6, y, s);
}

bool labmate_scope_reference_view_draw(
    Canvas* c, LabMateScopeReferencePreset selected,
    LabMateScopeToleranceResult result, const LabMateScopeMetrics* measured) {
    if(!c || (unsigned)result.verdict > (unsigned)LabMateScopeVerdictBusy)
        return false;
    LabMateScopeReference ref = {0};
    if(!labmate_scope_reference_preset(selected, &ref)) return false;
    const bool complete = result.verdict == LabMateScopeVerdictPass ||
                          result.verdict == LabMateScopeVerdictOutOfTolerance;
    if(complete &&
       (!measured || measured->status != LabMateScopeMetricsReady ||
        measured->truncated || measured->completed_cycles == 0U ||
        measured->frequency_millihz == 0U ||
        measured->duty_permille > 1000U)) return false;
    if(complete) {
        const LabMateScopeToleranceResult checked =
            labmate_scope_tolerance_evaluate(
                &ref, measured, LabMateScopeObservationComplete);
        if(checked.verdict != result.verdict ||
           checked.frequency_error_millihz != result.frequency_error_millihz ||
           checked.duty_error_permille != result.duty_error_permille)
            return false;
    }

    char frequency[24] = "--";
    char duty[24] = "--";
    if(complete) {
        if(measured->frequency_millihz >= UINT64_C(100000000)) {
            (void)snprintf(frequency, sizeof(frequency), ">99kHz");
        } else if(measured->frequency_millihz >= UINT64_C(1000000)) {
            const uint64_t rounded =
                (measured->frequency_millihz + 5000U) / 10000U;
            (void)snprintf(frequency, sizeof(frequency), "%lu.%02lukHz",
                (unsigned long)(rounded / 100U),
                (unsigned long)(rounded % 100U));
        } else {
            const uint64_t rounded =
                (measured->frequency_millihz + 5U) / 10U;
            (void)snprintf(frequency, sizeof(frequency), "%lu.%02luHz",
                (unsigned long)(rounded / 100U),
                (unsigned long)(rounded % 100U));
        }
        (void)snprintf(duty, sizeof(duty), "%u.%u%%",
            (unsigned)(measured->duty_permille / 10U),
            (unsigned)(measured->duty_permille % 10U));
    }

    const char* verdict = verdict_label(result.verdict);
    if(strlen(ref.name) > 11U || strlen(frequency) > 11U ||
       strlen(duty) > 11U || strlen(verdict) > 11U) return false;

    (void)labmate_scope_ui_header(c, "REFERENCE", "4/4");
    const char* labels[4] = {"TARGET", "FREQ", "DUTY", "RESULT"};
    const char* values[4] = {ref.name, frequency, duty, verdict};
    const int32_t y[4] = {22, 32, 42, 52};
    for(uint8_t i = 0U; i < 4U; ++i) {
        labmate_scope_ui_text(c, FontSecondary, 4, y[i], labels[i]);
        right_value(c, y[i], values[i]);
    }
    (void)labmate_scope_ui_footer(c, "(^)Ref", "(v)Pg");
    return true;
}
