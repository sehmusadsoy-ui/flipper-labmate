/* Real-device T02 screenshot regression: prevent y=52 status/footer collision.
 * Pure host model for the exact Doctor geometry constants and known verdicts.
 * Real Flipper font raster and end-to-end app FAP remain separately tested.
 */
#include "labmate_doctor_layout.h"
#include "labmate_doctor_panel.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

#define TOP(y) ((y) - LABMATE_DOCTOR_GLYPH_HEIGHT + 1)
#define WIDTH(s) (LABMATE_DOCTOR_TEXT_X + \
    (int)strlen(s) * LABMATE_DOCTOR_GLYPH_ADVANCE)

_Static_assert(LABMATE_UI_WIDTH == 128 && LABMATE_UI_HEIGHT == 64, "LCD geometry");
_Static_assert(TOP(LABMATE_DOCTOR_ROW1_Y) > LABMATE_UI_HEADER_RULE_Y,
               "first row must clear header");
_Static_assert(TOP(LABMATE_DOCTOR_ROW2_Y) > LABMATE_DOCTOR_ROW1_Y,
               "row 2 must not touch row 1");
_Static_assert(TOP(LABMATE_DOCTOR_ROW3_Y) > LABMATE_DOCTOR_ROW2_Y,
               "row 3 must not touch row 2");
_Static_assert(TOP(LABMATE_DOCTOR_STATUS_Y) > LABMATE_DOCTOR_ROW3_Y,
               "status must not touch fields");
/* These come from TWO distinct anonymous enums. Cast for a strict
 * -Werror=enum-compare build while retaining compile-time geometry proof.
 */
_Static_assert((int)LABMATE_DOCTOR_STATUS_Y < (int)LABMATE_UI_FOOTER_RULE_Y,
               "status cannot collide with footer rule");
_Static_assert(LABMATE_UI_FOOTER_RULE_Y < LABMATE_UI_FOOTER_BASELINE_Y,
               "footer must be below rule");
_Static_assert(TOP(LABMATE_UI_FOOTER_BASELINE_Y) > LABMATE_UI_FOOTER_RULE_Y,
               "footer glyph must clear divider");

static void check_label(const char* s) {
    assert(s && WIDTH(s) <= LABMATE_UI_WIDTH);
    for(const char* p = s; *p; ++p) assert(*p >= 32 && *p <= 126);
}

int main(void) {
    /* Maximum editable values and all conservative status names. */
    check_label(">SRC PULSE");
    check_label(">SRC GPIO");
    check_label("HIGH SAMPLED");
    check_label("LOW SAMPLED");
    check_label("NO LEVEL EVIDENCE");
    check_label(">REF 100000Hz x1000");
    check_label(">F TOL 100.0%");
    check_label(">DUTY 100.0%");
    check_label(">D TOL 100.0%");
    check_label(">QUIET 10000ms");
    const char* states[] = {
        "SET REF FIRST", "NO SEALED DATA", "BUSY - WAIT",
        "DATA UNSAFE", "INSUFFICIENT", "FREQ+DUTY", "FREQ DIFF",
        "DUTY DIFF", "IN RANGE", "NO SIG"
    };
    for(unsigned i=0;i<sizeof(states)/sizeof(states[0]);++i) check_label(states[i]);

    LabMateDoctorPanel p;
    LabMateDashboardStore s;
    labmate_doctor_panel_init(&p);
    labmate_dashboard_store_init(&s);
    LabMateDoctorPanelAssessment a = labmate_doctor_panel_assess(&p,&s);
    assert(a.status == LabMateDoctorPanelSetReference);
    assert(!strcmp(labmate_doctor_panel_status_text(&a),"SET REF FIRST"));
    labmate_doctor_panel_move(&p,1);
    labmate_doctor_panel_step(&p);
    labmate_doctor_panel_step(&p);
    labmate_doctor_panel_edit(&p,1);
    assert(p.reference.frequency_millihz==100000U);
    a=labmate_doctor_panel_assess(&p,&s);
    assert(a.status == LabMateDoctorPanelNoData);
    assert(!strcmp(labmate_doctor_panel_status_text(&a),"NO SEALED DATA"));
    puts("DOCTOR 128x64 UI GEOMETRY HOST PASS: no status/footer overlap; controls and labels bounded");
    return 0;
}
