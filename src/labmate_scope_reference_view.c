#include "labmate_scope_reference_view.h"
#include <stdio.h>

static const char* labmate_scope_reference_verdict_text(LabMateScopeVerdict verdict) {
    switch(verdict) {
    case LabMateScopeVerdictPass: return "PASS";
    case LabMateScopeVerdictOutOfTolerance: return "OUT OF TOLERANCE";
    case LabMateScopeVerdictNoSignal: return "NO SIGNAL";
    case LabMateScopeVerdictBusy: return "BUSY";
    case LabMateScopeVerdictInvalid:
    default: return "INVALID / WAIT";
    }
}

bool labmate_scope_reference_view_draw(
    Canvas* canvas,
    LabMateScopeReferencePreset selected,
    LabMateScopeToleranceResult result,
    const LabMateScopeMetrics* measured) {
    if(!canvas || result.verdict < LabMateScopeVerdictInvalid ||
       result.verdict > LabMateScopeVerdictBusy) return false;

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

    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, 3, 9, "REF COMPARE PC1");
    canvas_draw_line(canvas, 0, 13, 127, 13);

    char title[24];
    (void)snprintf(title, sizeof(title), "REF: %s", reference.name);
    canvas_draw_str(canvas, 3, 24, title);
    canvas_draw_str(canvas, 3, 36,
        labmate_scope_reference_verdict_text(result.verdict));

    if(has_metrics) {
        char observed[24];
        /* This line is for display only. The verdict uses full mHz
         * precision from the pure-C evaluator, never rounded LCD text. */
        if(measured->frequency_millihz < UINT64_C(100000000)) {
            const uint64_t hz = measured->frequency_millihz / UINT64_C(1000);
            const uint64_t hundredths =
                (measured->frequency_millihz % UINT64_C(1000)) / UINT64_C(10);
            (void)snprintf(observed, sizeof(observed),
                "%lu.%02luHz %u.%u%%",
                (unsigned long)hz, (unsigned long)hundredths,
                (unsigned)(measured->duty_permille / 10U),
                (unsigned)(measured->duty_permille % 10U));
        } else {
            (void)snprintf(observed, sizeof(observed), ">99kHz %u.%u%%",
                (unsigned)(measured->duty_permille / 10U),
                (unsigned)(measured->duty_permille % 10U));
        }
        canvas_draw_str(canvas, 3, 49, observed);
    } else {
        canvas_draw_str(canvas, 3, 49, "NO VALID MEASUREMENT");
    }

    canvas_draw_line(canvas, 0, 53, 127, 53);
    canvas_draw_str(canvas, 3, 62, "UP REF  DN PLOT");
    return true;
}
