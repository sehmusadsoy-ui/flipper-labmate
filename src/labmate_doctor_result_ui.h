#pragma once

/* Doctor Step 3: pure, display-only projection of existing sealed assessments.
 * No capture, diagnosis, threshold, clock, resource or storage changes. */
#include "labmate_doctor_panel.h"
#include "labmate_doctor_symptoms.h"
#include "ui_kit.h"

typedef enum {
    LabMateDoctorResultSignal = 2,
    LabMateDoctorResultScope = 3,
} LabMateDoctorResultPage;

typedef struct {
    UiKitResultCard card;
    char line1[32];
    char line2[32];
} LabMateDoctorResultPresentation;

/* These cover every legacy result state, including no/unsafe/insufficient
 * evidence. The caller retains presentation storage until drawing finishes. */
void labmate_doctor_result_signal(
    const LabMateDoctorPanelAssessment* assessment,
    const LabMateDoctorPanel* panel,
    const LabMateDashboardStore* store,
    LabMateDoctorResultPresentation* output);

void labmate_doctor_result_scope(
    const LabMateDoctorSymptomReport* report,
    LabMateDoctorResultPresentation* output);

/* Header, four page dots and a fitted result card; pin may be NULL.
 * An advisory badge appears only when a valid assessed finding exists. */
bool labmate_doctor_result_draw(
    Canvas* canvas, LabMateDoctorResultPage page,
    const char* pin, const LabMateDoctorResultPresentation* presentation);
