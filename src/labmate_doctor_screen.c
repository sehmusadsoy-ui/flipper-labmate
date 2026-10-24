#include "labmate_doctor_screen.h"
#include "labmate_ui_primitives.h"
#include "labmate_doctor_layout.h"
#include "labmate_doctor_advice.h"
#include <stdio.h>

static void panel_row(Canvas* c, uint8_t y, bool selected,
                      const char* label, const char* value) {
    char buf[24];
    (void)snprintf(buf, sizeof(buf), "%c%s %s", selected ? '>' : ' ', label, value);
    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, LABMATE_DOCTOR_TEXT_X, y, buf);
}

void labmate_doctor_screen_draw(Canvas* c, const LabMateApp* app) {
    if(!c || !app) return;
    const LabMateDoctorPanel* p = &app->doctor_panel;
    const uint8_t page = p->field < 3U ? 0U : 1U;
    char text[22];
    ui_draw_header(c, "DOCTOR");
    if(app->doctor_show_advice) {
        ui_badge(c, 95, 1, 31, "3/3", false);
        const LabMateDoctorPanelAssessment result =
            labmate_doctor_panel_assess(p, &app->doctor_store);
        const LabMateDoctorAdvice advice = labmate_doctor_advice(&result);
        const char* finding=advice.finding;
        const char* evidence=advice.evidence;
        const char* next_check=advice.next_check;
        LabMateSnapshotV1 sealed;
        if(p->source == LABMATE_DOCTOR_MONITOR_SOURCE) {
            const LabMateLevelFinding found=labmate_level_assess(
                &app->gpio_level_witness,
                p->reference.minimum_no_signal_window_ms);
            finding=found == LabMateLevelSampledHigh ? "HIGH SAMPLED" :
                    found == LabMateLevelSampledLow ? "LOW SAMPLED" :
                    found == LabMateLevelTransitions ? "LEVEL CHANGED" :
                                                        "NO LEVEL EVIDENCE";
            evidence=found == LabMateLevelNoEvidence ? "NOT CONFIRMED" :
                                                       "GPIO POLLING ONLY";
            next_check="VERIFY WITH SCOPE";
        }
        /* Scope timing hints require the exact same real capture generation
         * and a separately verified sealed snapshot. No live reads here.
         */
        if(p->source == LabMateSnapshotScope &&
           result.status == LabMateDoctorPanelAssessed &&
           result.doctor.evidence_accepted &&
           app->scope_diagnostics.valid &&
           labmate_dashboard_store_read_measurement(
               &app->doctor_store,LabMateSnapshotScope,&sealed) &&
           sealed.capture_generation == app->scope_last_generation) {
            if(app->scope_diagnostics.gap_suspected) {
                finding="PERIOD GAP?";
                evidence="FULL CYCLES ONLY";
                next_check="CHECK SOURCE";
            } else if(app->scope_diagnostics.spread_permille >
                      p->reference.frequency_tolerance_permille) {
                finding="TIMING VARIES";
                evidence="SPREAD > SET TOL";
                next_check="RECHECK SOURCE";
            }
        }
        canvas_set_font(c, FontSecondary);
        canvas_draw_str(c, LABMATE_DOCTOR_TEXT_X, LABMATE_DOCTOR_ROW1_Y, finding);
        canvas_draw_str(c, LABMATE_DOCTOR_TEXT_X, LABMATE_DOCTOR_ROW2_Y, evidence);
        canvas_draw_str(c, LABMATE_DOCTOR_TEXT_X, LABMATE_DOCTOR_ROW3_Y, next_check);
        canvas_draw_str(c, LABMATE_DOCTOR_TEXT_X, LABMATE_DOCTOR_STATUS_Y,
                        "ADVISORY ONLY");
        ui_footer_pair(c, "OK", "EDIT", "BACK", "MENU");
        return;
    }
    ui_badge(c, 95, 1, 31, page ? "2/3" : "1/3", false);
    if(page == 0U) {
        panel_row(c, LABMATE_DOCTOR_ROW1_Y, p->field == LabMateDoctorFieldSource, "SRC",
                  p->source == LabMateSnapshotPulse ? "PULSE" :
                  p->source == LabMateSnapshotScope ? "SCOPE" :
                  p->source == LABMATE_DOCTOR_MONITOR_SOURCE ? "GPIO" : "FREQ");
        (void)snprintf(text, sizeof(text), "%luHz x%lu",
                      (unsigned long)(p->reference.frequency_millihz / 1000U),
                      (unsigned long)p->frequency_step_hz);
        panel_row(c, LABMATE_DOCTOR_ROW2_Y, p->field == LabMateDoctorFieldFrequency, "REF",
                  p->source == LABMATE_DOCTOR_MONITOR_SOURCE ? "N/A" : text);
        (void)snprintf(text, sizeof(text), "%u.%u%%",
                      (unsigned)(p->reference.frequency_tolerance_permille / 10U),
                      (unsigned)(p->reference.frequency_tolerance_permille % 10U));
        panel_row(c, LABMATE_DOCTOR_ROW3_Y, p->field == LabMateDoctorFieldFrequencyTolerance, "F TOL",
                  p->source == LABMATE_DOCTOR_MONITOR_SOURCE ? "N/A" : text);
    } else {
        (void)snprintf(text, sizeof(text), "%u.%u%%",
                      (unsigned)(p->reference.expected_duty_permille / 10U),
                      (unsigned)(p->reference.expected_duty_permille % 10U));
        panel_row(c, LABMATE_DOCTOR_ROW1_Y, p->field == LabMateDoctorFieldDuty, "DUTY",
                  p->source == LABMATE_DOCTOR_MONITOR_SOURCE ? "N/A" : text);
        (void)snprintf(text, sizeof(text), "%u.%u%%",
                      (unsigned)(p->reference.duty_tolerance_permille / 10U),
                      (unsigned)(p->reference.duty_tolerance_permille % 10U));
        panel_row(c, LABMATE_DOCTOR_ROW2_Y, p->field == LabMateDoctorFieldDutyTolerance, "D TOL",
                  p->source == LABMATE_DOCTOR_MONITOR_SOURCE ? "N/A" : text);
        (void)snprintf(text, sizeof(text), "%lums",
                      (unsigned long)p->reference.minimum_no_signal_window_ms);
        panel_row(c, LABMATE_DOCTOR_ROW3_Y, p->field == LabMateDoctorFieldSilence, "QUIET", text);
    }
    LabMateDoctorPanelAssessment a =
        labmate_doctor_panel_assess(p, &app->doctor_store);
    canvas_set_font(c, FontSecondary);
    /* Physical Phase3E screenshot exposed the old y=52 collision with
     * the shared footer divider at y=52. Keep text fully above the rule.
     */
    const char* status=labmate_doctor_panel_status_text(&a);
    if(p->source == LABMATE_DOCTOR_MONITOR_SOURCE) {
        const LabMateLevelFinding level=labmate_level_assess(
            &app->gpio_level_witness,p->reference.minimum_no_signal_window_ms);
        status=level == LabMateLevelSampledHigh ? "HIGH SAMPLED" :
               level == LabMateLevelSampledLow ? "LOW SAMPLED" :
               level == LabMateLevelTransitions ? "LEVEL CHANGED" :
                                                  "NO LEVEL EVIDENCE";
    }
    canvas_draw_str(c, LABMATE_DOCTOR_TEXT_X, LABMATE_DOCTOR_STATUS_Y, status);
    /* Three real keys are used on this screen. The shared triple footer
     * keeps all actions visible, avoiding an undiscoverable advice page.
     */
    ui_footer_triple(c, "<>FIELD", "^vEDIT",
                     (p->field == LabMateDoctorFieldFrequency &&
                      p->source != LABMATE_DOCTOR_MONITOR_SOURCE) ? "OKx" : "OKINF");
}
