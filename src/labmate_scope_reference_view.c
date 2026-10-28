#include "labmate_scope_reference_view.h"
#include "labmate_scope_ui.h"
#include "ui_kit.h"
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

    /* Scope Reference Step3: one truth source for WAIT/MATCH/OFF/NO-SIG
     * and BUSY. The tolerance engine and complete-data guard above are
     * unchanged; this renderer never infers a PASS from raw numbers. */
    const UiKitInstrumentState chip = result.verdict == LabMateScopeVerdictPass ?
        UiKitInstrumentMatch :
        result.verdict == LabMateScopeVerdictOutOfTolerance ? UiKitInstrumentOff :
        result.verdict == LabMateScopeVerdictBusy ? UiKitInstrumentBusy :
        UiKitInstrumentWaiting;
    const char* verdict = verdict_label(result.verdict);
    if(strlen(ref.name) > 11U || strlen(frequency) > 11U ||
       strlen(duty) > 11U || strlen(verdict) > 11U) return false;

    /* Reference + Waiting won't fit FontPrimary and a right state chip
     * on the 128px top line. Use a MEASURED Secondary title, without
     * shortening "Reference", moving the chip, or hiding the verdict.
     * This deliberate exception is isolated to the Reference page. */
    canvas_set_font(c, FontSecondary);
    const uint16_t title_w = canvas_string_width(c, "Reference");
    const uint8_t chip_w = ui_kit_state_chip_width(c, chip);
    if(!chip_w || !title_w || 9U + title_w + 2U > 127U - chip_w)
        return false;
    canvas_set_font(c, FontSecondary);
    const uint16_t preset_w = canvas_string_width(c, ref.name);
    if(!preset_w || preset_w > 60U) return false;
    /* Preflight both value rows BEFORE painting any pixel. */
    const char* frequency_value =
        result.verdict == LabMateScopeVerdictNoSignal ? "No signal" :
        result.verdict == LabMateScopeVerdictBusy ? "Busy" : frequency;
    canvas_set_font(c, FontSecondary);
    const uint16_t f_label_w = canvas_string_width(c, "Frequency");
    const uint16_t d_label_w = canvas_string_width(c, "Duty");
    const uint16_t f_value_w = canvas_string_width(c, frequency_value);
    const uint16_t d_value_w = canvas_string_width(c, duty);
    if(!f_value_w || !d_value_w ||
       4U + f_label_w + 5U > 124U - f_value_w ||
       4U + d_label_w + 5U > 124U - d_value_w)
        return false;

    canvas_set_color(c, ColorBlack);
    canvas_draw_line(c, 5U, 2U, 2U, 5U);
    canvas_draw_line(c, 2U, 5U, 5U, 8U);
    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, 9U, 9U, "Reference");
    (void)ui_kit_state_chip_compact(c, chip, false);
    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, 4U, 20U, "Pin PC1");
    (void)ui_kit_scope_page_dots(c, 3U);

    /* Target uses the exact configured preset (100Hz 50% / 1kHz 50%).
     * No fake sample frequency is used to make WAIT appear like MATCH. */
    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, 4U, 33U, "Target");
    canvas_draw_rframe(c, 60U, 24U, 66U, 12U, 3U);
    canvas_draw_str(c, 60U + (66U - preset_w) / 2U, 33U, ref.name);
    canvas_draw_str(c, 4U, 43U, "Frequency");
    canvas_draw_str(c, 124U - f_value_w, 43U, frequency_value);
    canvas_draw_str(c, 4U, 52U, "Duty");
    canvas_draw_str(c, 124U - d_value_w, 52U, duty);

    /* UP remains the exact Reference preset toggle. DOWN navigates to
     * Scope while stopped; the existing bridge handles all key events. */
    (void)ui_kit_key_hint(c, 4U, UiKitKeyUp, "Target");
    (void)ui_kit_key_hint(c, 70U, UiKitKeyDown, "Next");
    canvas_set_color(c, ColorBlack);
    return true;
}
