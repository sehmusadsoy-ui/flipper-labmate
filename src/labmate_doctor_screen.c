#include "labmate_doctor_screen.h"
#include "labmate_doctor_symptoms.h"
#include "labmate_doctor_setup.h"
#include "labmate_doctor_result_ui.h"

void labmate_doctor_screen_draw(Canvas* c, const LabMateApp* app) {
    if(!c || !app) return;
    const LabMateDoctorPanel* p = &app->doctor_panel;
    if(app->doctor_show_symptoms) {
        /* Only a Scope diagnosis belonging to the current stopped capture
         * may appear. A stale generation is treated as no data. */
        LabMateDoctorSymptomReport none = {0};
        const bool current = app->scope_symptoms_generation != 0U &&
            app->scope_symptoms_generation == app->scope_capture_generation;
        LabMateDoctorResultPresentation display;
        labmate_doctor_result_scope(current ? &app->scope_symptoms : &none, &display);
        (void)labmate_doctor_result_draw(
            c, LabMateDoctorResultScope, "PC1", &display);
        return;
    }
    if(app->doctor_show_advice) {
        const LabMateDoctorPanelAssessment result =
            labmate_doctor_panel_assess(p, &app->doctor_store);
        LabMateDoctorResultPresentation display;
        labmate_doctor_result_signal(&result, p, &app->doctor_store, &display);
        const char* pin = NULL;
        if(p->source <= LabMateSnapshotPulse &&
           app->doctor_store.slots[p->source].has_snapshot) {
            const uint8_t index =
                app->doctor_store.slots[p->source].latest.pin_index;
            if(index == 1U) pin = "PC1";
            else if(index == 4U) pin = "PB3";
        }
        (void)labmate_doctor_result_draw(
            c, LabMateDoctorResultSignal, pin, &display);
        return;
    }
    /* Step 2 setup stays byte-for-byte unchanged. */
    labmate_doctor_setup_draw(c, p, &app->doctor_setup_ui, app->ui_pulse_phase);
}
