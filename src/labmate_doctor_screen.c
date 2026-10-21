#include "labmate_doctor_screen.h"
#include "labmate_ui_primitives.h"
#include <stdio.h>

static void panel_row(Canvas* c, uint8_t y, bool selected,
                      const char* label, const char* value) {
    char buf[24];
    (void)snprintf(buf, sizeof(buf), "%c%s %s", selected ? '>' : ' ', label, value);
    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, 4, y, buf);
}

void labmate_doctor_screen_draw(Canvas* c, const LabMateApp* app) {
    if(!c || !app) return;
    const LabMateDoctorPanel* p = &app->doctor_panel;
    const uint8_t page = p->field < 3U ? 0U : 1U;
    char text[22];
    ui_draw_header(c, "DOCTOR");
    ui_badge(c, 95, 1, 31, page ? "2/2" : "1/2", false);
    if(page == 0U) {
        panel_row(c, 23, p->field == LabMateDoctorFieldSource, "SRC",
                  p->source == LabMateSnapshotPulse ? "PULSE" : "FREQ");
        (void)snprintf(text, sizeof(text), "%luHz x%lu",
                      (unsigned long)(p->reference.frequency_millihz / 1000U),
                      (unsigned long)p->frequency_step_hz);
        panel_row(c, 33, p->field == LabMateDoctorFieldFrequency, "REF", text);
        (void)snprintf(text, sizeof(text), "%u.%u%%",
                      (unsigned)(p->reference.frequency_tolerance_permille / 10U),
                      (unsigned)(p->reference.frequency_tolerance_permille % 10U));
        panel_row(c, 43, p->field == LabMateDoctorFieldFrequencyTolerance, "F TOL", text);
    } else {
        (void)snprintf(text, sizeof(text), "%u.%u%%",
                      (unsigned)(p->reference.expected_duty_permille / 10U),
                      (unsigned)(p->reference.expected_duty_permille % 10U));
        panel_row(c, 23, p->field == LabMateDoctorFieldDuty, "DUTY", text);
        (void)snprintf(text, sizeof(text), "%u.%u%%",
                      (unsigned)(p->reference.duty_tolerance_permille / 10U),
                      (unsigned)(p->reference.duty_tolerance_permille % 10U));
        panel_row(c, 33, p->field == LabMateDoctorFieldDutyTolerance, "D TOL", text);
        (void)snprintf(text, sizeof(text), "%lums",
                      (unsigned long)p->reference.minimum_no_signal_window_ms);
        panel_row(c, 43, p->field == LabMateDoctorFieldSilence, "QUIET", text);
    }
    LabMateDoctorPanelAssessment a =
        labmate_doctor_panel_assess(p, &app->doctor_store);
    canvas_set_font(c, FontSecondary);
    canvas_draw_str(c, 4, 52, labmate_doctor_panel_status_text(&a));
    ui_footer_pair(c, "<>", "FIELD", "^v", "EDIT");
}
