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
        canvas_set_font(c, FontSecondary);
        canvas_draw_str(c, LABMATE_DOCTOR_TEXT_X, LABMATE_DOCTOR_ROW1_Y, advice.finding);
        canvas_draw_str(c, LABMATE_DOCTOR_TEXT_X, LABMATE_DOCTOR_ROW2_Y, advice.evidence);
        canvas_draw_str(c, LABMATE_DOCTOR_TEXT_X, LABMATE_DOCTOR_ROW3_Y, advice.next_check);
        canvas_draw_str(c, LABMATE_DOCTOR_TEXT_X, LABMATE_DOCTOR_STATUS_Y,
                        "ADVISORY ONLY");
        ui_footer_pair(c, "OK", "EDIT", "BACK", "MENU");
        return;
    }
    ui_badge(c, 95, 1, 31, page ? "2/3" : "1/3", false);
    if(page == 0U) {
        panel_row(c, LABMATE_DOCTOR_ROW1_Y, p->field == LabMateDoctorFieldSource, "SRC",
                  p->source == LabMateSnapshotPulse ? "PULSE" : "FREQ");
        (void)snprintf(text, sizeof(text), "%luHz x%lu",
                      (unsigned long)(p->reference.frequency_millihz / 1000U),
                      (unsigned long)p->frequency_step_hz);
        panel_row(c, LABMATE_DOCTOR_ROW2_Y, p->field == LabMateDoctorFieldFrequency, "REF", text);
        (void)snprintf(text, sizeof(text), "%u.%u%%",
                      (unsigned)(p->reference.frequency_tolerance_permille / 10U),
                      (unsigned)(p->reference.frequency_tolerance_permille % 10U));
        panel_row(c, LABMATE_DOCTOR_ROW3_Y, p->field == LabMateDoctorFieldFrequencyTolerance, "F TOL", text);
    } else {
        (void)snprintf(text, sizeof(text), "%u.%u%%",
                      (unsigned)(p->reference.expected_duty_permille / 10U),
                      (unsigned)(p->reference.expected_duty_permille % 10U));
        panel_row(c, LABMATE_DOCTOR_ROW1_Y, p->field == LabMateDoctorFieldDuty, "DUTY", text);
        (void)snprintf(text, sizeof(text), "%u.%u%%",
                      (unsigned)(p->reference.duty_tolerance_permille / 10U),
                      (unsigned)(p->reference.duty_tolerance_permille % 10U));
        panel_row(c, LABMATE_DOCTOR_ROW2_Y, p->field == LabMateDoctorFieldDutyTolerance, "D TOL", text);
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
    canvas_draw_str(c, LABMATE_DOCTOR_TEXT_X, LABMATE_DOCTOR_STATUS_Y,
                    labmate_doctor_panel_status_text(&a));
    /* Three real keys are used on this screen. The shared triple footer
     * keeps all actions visible, avoiding an undiscoverable advice page.
     */
    ui_footer_triple(c, "<>FIELD", "^vEDIT",
                     p->field == LabMateDoctorFieldFrequency ? "OKx" : "OKINF");
}
