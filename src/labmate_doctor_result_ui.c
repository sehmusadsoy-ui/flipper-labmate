#include "labmate_doctor_result_ui.h"
#include <stdio.h>

/* Presentation words are deliberately independent of the existing ALL-CAPS
 * diagnostic labels. Only a pre-existing assessment chooses the finding. */
static void result_set(
    LabMateDoctorResultPresentation* o, UiKitDiagKind glyph,
    const char* verdict, const char* short_verdict,
    const char* reason, const char* second, const char* action,
    const char* short_action, bool advisory) {
    (void)snprintf(o->line1, sizeof(o->line1), "%s", reason ? reason : "");
    (void)snprintf(o->line2, sizeof(o->line2), "%s", second ? second : "");
    o->card = (UiKitResultCard){
        .glyph = glyph,
        .verdict = verdict,
        .short_verdict = short_verdict,
        .reason = o->line1,
        .short_reason = "Check the last capture.",
        .reason_second = o->line2[0] ? o->line2 : NULL,
        .short_reason_second = "Review the reference.",
        .action = action,
        .short_action = short_action,
        .advisory = advisory,
    };
}

static void result_second(LabMateDoctorResultPresentation* o) {
    o->card.reason_second = o->line2[0] ? o->line2 : NULL;
}

/* Values remain exactly as captured in the source data. Only their display
 * precision is adapted to the small monochrome LCD. */
static void readable_frequency(char* output, size_t cap, uint32_t mhz) {
    if(mhz < 1000000U)
        (void)snprintf(output, cap, "%lu.%02lu Hz",
                       (unsigned long)(mhz / 1000U),
                       (unsigned long)((mhz % 1000U) / 10U));
    else
        (void)snprintf(output, cap, "%lu.%02lu kHz",
                       (unsigned long)(mhz / 1000000U),
                       (unsigned long)((mhz % 1000000U) / 10000U));
}

void labmate_doctor_result_signal(
    const LabMateDoctorPanelAssessment* assessment,
    const LabMateDoctorPanel* panel,
    const LabMateDashboardStore* store,
    LabMateDoctorResultPresentation* o) {
    if(!o) return;
    result_set(o, UiKitDiagNoData, "Need more data", NULL,
               "Not enough verified", "readings yet.", "Capture again", NULL, false);
    if(!assessment) return;

    switch(assessment->status) {
    case LabMateDoctorPanelSetReference:
        result_set(o, UiKitDiagNoData, "No reference yet", "No reference",
                   "Set one to compare", "live readings.", "OK Reference", NULL, false);
        return;
    case LabMateDoctorPanelNoData:
        result_set(o, UiKitDiagNoData, "No data yet", NULL,
                   "Capture a signal,", "then stop.", "Capture data", NULL, false);
        return;
    case LabMateDoctorPanelBusy:
        result_set(o, UiKitDiagNoData, "Capture is busy", NULL,
                   "Stop the capture,", "then try again.", "Stop capture", NULL, false);
        return;
    case LabMateDoctorPanelUnsafe:
        result_set(o, UiKitDiagNoData, "Reading unavailable", "Unsafe data",
                   "Clock or sample loss", "prevents assessment.", "Try again", NULL, false);
        return;
    case LabMateDoctorPanelInsufficient:
        return;
    case LabMateDoctorPanelAssessed:
        if(!assessment->doctor.evidence_accepted) return;
        break;
    default:
        return;
    }

    const LabMateSnapshotV1* snapshot = NULL;
    if(panel && store && panel->source <= LabMateSnapshotPulse &&
       store->slots[panel->source].has_snapshot)
        snapshot = &store->slots[panel->source].latest;

    switch(assessment->doctor.verdict) {
    case LabMateDoctorNoSignalObserved:
        result_set(o, UiKitDiagNoData, "No edges seen", NULL,
                   "No changes observed.", "Check the signal line.",
                   "Check wiring", "Wiring", true);
        if(snapshot) {
            const uint32_t duration = snapshot->observation_end_ms -
                                      snapshot->observation_start_ms;
            (void)snprintf(o->line1, sizeof(o->line1), "No edges: %lu ms",
                           (unsigned long)duration);
        }
        break;
    case LabMateDoctorWithinExpected:
        result_set(o, UiKitDiagHealthy, "No issue seen", NULL,
                   "Within the chosen", "reference range.", "Test under load",
                   "Test load", true);
        break;
    case LabMateDoctorFrequencyDeviation:
        result_set(o, UiKitDiagOffFrequencyDuty, "Frequency off", NULL,
                   "Measured frequency", "differs from expected.",
                   "Check source", "Source", true);
        if(snapshot && panel) {
            char observed[14], expected[14];
            readable_frequency(observed, sizeof(observed), snapshot->frequency_millihz);
            readable_frequency(expected, sizeof(expected), panel->reference.frequency_millihz);
            (void)snprintf(o->line1, sizeof(o->line1), "%s seen", observed);
            (void)snprintf(o->line2, sizeof(o->line2), "%s expected", expected);
        }
        break;
    case LabMateDoctorDutyDeviation:
        result_set(o, UiKitDiagOffFrequencyDuty, "Duty off", NULL,
                   "Measured duty differs", "from expected.",
                   "Check duty", NULL, true);
        if(snapshot && panel) {
            (void)snprintf(o->line1, sizeof(o->line1), "%u.%u%% observed",
                           (unsigned)(snapshot->duty_permille / 10U),
                           (unsigned)(snapshot->duty_permille % 10U));
            (void)snprintf(o->line2, sizeof(o->line2), "%u.%u%% expected",
                           (unsigned)(panel->reference.expected_duty_permille / 10U),
                           (unsigned)(panel->reference.expected_duty_permille % 10U));
        }
        break;
    case LabMateDoctorMultipleDeviations:
        result_set(o, UiKitDiagOffFrequencyDuty, "Both values off", NULL,
                   "Frequency differs", "and duty differs too.",
                   "Check signal", "Signal", true);
        if(snapshot && panel) {
            char measured[14], expected[14];
            readable_frequency(measured, sizeof(measured), snapshot->frequency_millihz);
            readable_frequency(expected, sizeof(expected), panel->reference.frequency_millihz);
            (void)snprintf(o->line1, sizeof(o->line1), "%s / %s", measured, expected);
            (void)snprintf(o->line2, sizeof(o->line2), "%u.%u / %u.%u%% duty",
                           (unsigned)(snapshot->duty_permille / 10U),
                           (unsigned)(snapshot->duty_permille % 10U),
                           (unsigned)(panel->reference.expected_duty_permille / 10U),
                           (unsigned)(panel->reference.expected_duty_permille % 10U));
        }
        break;
    case LabMateDoctorNotReady:
    default:
        result_set(o, UiKitDiagNoData, "Need more data", NULL,
                   "Not enough verified", "readings yet.",
                   "Capture again", NULL, false);
        break;
    }
    result_second(o);
}

void labmate_doctor_result_scope(
    const LabMateDoctorSymptomReport* r, LabMateDoctorResultPresentation* o) {
    if(!o) return;
    if(!r || r->status == LabMateSymptomNone) {
        result_set(o, UiKitDiagNoData, "No scope capture", "No capture",
                   "Run Scope, then stop.", "Reopen Doctor.",
                   "OK Settings", NULL, false);
        return;
    }
    if(r->status == LabMateSymptomUnsafe) {
        result_set(o, UiKitDiagNoData, "Reading unavailable", "Unsafe data",
                   "Clock or overflow", "made capture unsafe.",
                   "Try again", NULL, false);
        return;
    }
    if(r->status == LabMateSymptomInsufficient) {
        result_set(o, UiKitDiagNoData, "Need more data", NULL,
                   "Capture a little", "longer to compare.",
                   "Capture longer", NULL, false);
        (void)snprintf(o->line1, sizeof(o->line1), "%u edges in %lu ms",
                       (unsigned)r->edge_count, (unsigned long)r->window_ms);
        result_second(o);
        return;
    }
    if(r->status != LabMateSymptomReady) {
        result_set(o, UiKitDiagNoData, "Need more data", NULL,
                   "Capture again.", NULL, "Capture again", NULL, false);
        return;
    }

    const uint16_t flags = r->flags;
    if(flags & (LABMATE_SYMPTOM_STUCK_HIGH | LABMATE_SYMPTOM_STUCK_LOW)) {
        const bool high = (flags & LABMATE_SYMPTOM_STUCK_HIGH) != 0U;
        result_set(o, high ? UiKitDiagStuckHigh : UiKitDiagStuckLow,
                   high ? "High level held" : "Low level held", NULL,
                   "No edges observed.", "Check source and wire.",
                   "Check wiring", "Wiring", true);
        (void)snprintf(o->line1, sizeof(o->line1), "No edges: %lu ms",
                       (unsigned long)r->window_ms);
    } else if(flags & (LABMATE_SYMPTOM_STOPPED_HIGH | LABMATE_SYMPTOM_STOPPED_LOW)) {
        const bool high = (flags & LABMATE_SYMPTOM_STOPPED_HIGH) != 0U;
        result_set(o, high ? UiKitDiagStuckHigh : UiKitDiagStuckLow,
                   high ? "High level held" : "Low level held", NULL,
                   "The line fell quiet.", "Check source and wire.",
                   "Check wiring", "Wiring", true);
        (void)snprintf(o->line1, sizeof(o->line1), "Quiet after %u edges",
                       (unsigned)r->edge_count);
    } else if(flags & (LABMATE_SYMPTOM_MISSING_PULSE | LABMATE_SYMPTOM_RUNT_PULSE)) {
        const bool gaps = (flags & LABMATE_SYMPTOM_MISSING_PULSE) != 0U;
        result_set(o, gaps ? UiKitDiagMissingPulse : UiKitDiagRuntPulses,
                   gaps ? "Pulses missing" : "Weak pulses", NULL,
                   "Irregular pulse widths", "were captured.",
                   gaps ? "Check source" : "Check drive",
                   gaps ? "Source" : "Drive", true);
        (void)snprintf(o->line1, sizeof(o->line1), "Gaps: %u, runt: %u",
                       (unsigned)r->gap_count, (unsigned)r->runt_count);
        (void)snprintf(o->line2, sizeof(o->line2), "Cycles: %u",
                       (unsigned)r->complete_cycles);
    } else if(flags & LABMATE_SYMPTOM_PERIOD_SPREAD) {
        const uint32_t sp = r->spread_permille > 9999U ? 9999U : r->spread_permille;
        result_set(o, UiKitDiagJitter, "Timing varies", NULL,
                   "Periods vary in time.", "Check clock stability.",
                   "Check clock", "Clock", true);
        (void)snprintf(o->line1, sizeof(o->line1), "Period spread %lu.%lu%%",
                       (unsigned long)(sp / 10U), (unsigned long)(sp % 10U));
        (void)snprintf(o->line2, sizeof(o->line2), "Across %u cycles",
                       (unsigned)r->complete_cycles);
    } else {
        /* Same conservative fallback as the original symptom text. No
         * 'healthy' certification: the claim is confined to this capture. */
        result_set(o, UiKitDiagHealthy, "No issue seen", NULL,
                   "No anomaly observed", "in this capture.",
                   "Test under load", "Test load", true);
        (void)snprintf(o->line1, sizeof(o->line1), "%u cycles reviewed",
                       (unsigned)r->complete_cycles);
        (void)snprintf(o->line2, sizeof(o->line2), "%u edges reviewed",
                       (unsigned)r->edge_count);
    }
    result_second(o);
}

bool labmate_doctor_result_draw(
    Canvas* c, LabMateDoctorResultPage page, const char* pin,
    const LabMateDoctorResultPresentation* presentation) {
    if(!c || !presentation ||
       (page != LabMateDoctorResultSignal && page != LabMateDoctorResultScope))
        return false;
    /* No black header/footer bars. The pin is only displayed when its
     * provenance was confirmed by a stored snapshot, never guessed. */
    canvas_set_font(c, FontSecondary);
    const char* title = page == LabMateDoctorResultSignal ? "Signal" : "Scope";
    if(canvas_string_width(c, title) > 79U) return false;
    if(pin && canvas_string_width(c, pin) > 23U) return false;
    if(!ui_kit_result_card(c, &presentation->card)) return false;

    canvas_set_font(c, FontSecondary);
    canvas_set_color(c, ColorBlack);
    canvas_draw_line(c, 7, 2, 4, 5);
    canvas_draw_line(c, 4, 5, 7, 8);
    canvas_draw_str(c, 12, 9, title);
    if(pin) canvas_draw_str(c, 72, 9, pin);
    for(uint8_t i = 0; i < 4U; ++i) {
        const uint8_t x = (uint8_t)(99U + i * 8U);
        if(i == (uint8_t)page) canvas_draw_box(c, x, 4, 3, 3);
        else canvas_draw_line(c, x, 5, x + 2U, 5);
    }
    return true;
}
