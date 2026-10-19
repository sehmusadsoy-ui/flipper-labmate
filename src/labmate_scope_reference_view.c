#include "labmate_scope_reference_view.h"
#include <stdio.h>
#include <string.h>

static const char* reference_verdict(LabMateScopeVerdict verdict) {
    switch(verdict) {
    case LabMateScopeVerdictPass: return "PASS";
    case LabMateScopeVerdictOutOfTolerance: return "OUT OF TOL";
    case LabMateScopeVerdictNoSignal: return "NO SIGNAL";
    case LabMateScopeVerdictBusy: return "BUSY";
    case LabMateScopeVerdictInvalid:
    default: return "WAIT / INVALID";
    }
}

bool labmate_scope_reference_view_draw(
    Canvas* c, LabMateScopeReferencePreset selected,
    LabMateScopeToleranceResult result, const LabMateScopeMetrics* measured) {
    if(!c || (unsigned)result.verdict > (unsigned)LabMateScopeVerdictBusy)
        return false;
    LabMateScopeReference reference = {0};
    if(!labmate_scope_reference_preset(selected, &reference)) return false;

    const bool has_metrics =
        result.verdict == LabMateScopeVerdictPass ||
        result.verdict == LabMateScopeVerdictOutOfTolerance;
    if(has_metrics &&
       (!measured || measured->status != LabMateScopeMetricsReady ||
        measured->truncated || measured->completed_cycles == 0U ||
        measured->frequency_millihz == 0U ||
        measured->duty_permille > 1000U)) return false;

    /* Never show a stale PASS after reference selection or capture changes.
     * Preserve the exact full-mHz/duty verdict; formatting is ONLY cosmetic. */
    if(has_metrics) {
        const LabMateScopeToleranceResult verified =
            labmate_scope_tolerance_evaluate(
                &reference, measured, LabMateScopeObservationComplete);
        if(verified.verdict != result.verdict ||
           verified.frequency_error_millihz != result.frequency_error_millihz ||
           verified.duty_error_permille != result.duty_error_permille)
            return false;
    }

    char target[24];
    char verdict[24];
    char frequency[24] = "NO VALID CAPTURE";
    char duty[24] = "";
    (void)snprintf(target, sizeof(target), "TARGET %s", reference.name);
    (void)snprintf(verdict, sizeof(verdict), "RESULT %s", reference_verdict(result.verdict));
    if(has_metrics) {
        if(measured->frequency_millihz < UINT64_C(100000000)) {
            const uint64_t hz = measured->frequency_millihz / UINT64_C(1000);
            const uint64_t fraction =
                (measured->frequency_millihz % UINT64_C(1000)) / UINT64_C(10);
            (void)snprintf(frequency, sizeof(frequency), "MEAS %lu.%02luHz",
                (unsigned long)hz, (unsigned long)fraction);
        } else {
            (void)snprintf(frequency, sizeof(frequency), "MEAS >99kHz");
        }
        (void)snprintf(duty, sizeof(duty), "DUTY %u.%u%%",
            (unsigned)(measured->duty_permille / 10U),
            (unsigned)(measured->duty_permille % 10U));
    } else {
        (void)snprintf(duty, sizeof(duty), "RUN, STOP, RETRY");
    }
    if(strlen(target) > 20U || strlen(verdict) > 20U ||
       strlen(frequency) > 20U || strlen(duty) > 20U) return false;

    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, 3, 9, "REFERENCE");
    canvas_draw_str(c, 102, 9, "PC1");
    canvas_draw_line(c, 0, 13, 127, 13);
    canvas_draw_str(c, 3, 23, target);
    canvas_draw_str(c, 3, 34, verdict);
    canvas_draw_str(c, 3, 44, frequency);
    canvas_draw_str(c, 3, 51, duty);
    canvas_draw_line(c, 0, 53, 127, 53);
    canvas_draw_str(c, 3, 62, "UP:REF DN:PG BK:EXIT");
    return true;
}
