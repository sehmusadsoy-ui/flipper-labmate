#pragma once
/* Phase 3B: app-thread-only reference editor and conservative status model.
 * No source may publish into the store without verified sealed evidence.
 */
#include "labmate_doctor.h"
#include "labmate_dashboard_store.h"
/* Separate witness source, intentionally outside the five numeric Snapshot
 * types: pooled GPIO polling cannot claim an edge-timed measurement.
 */
#define LABMATE_DOCTOR_MONITOR_SOURCE 250U

typedef enum {
    LabMateDoctorFieldSource = 0,
    LabMateDoctorFieldFrequency,
    LabMateDoctorFieldFrequencyTolerance,
    LabMateDoctorFieldDuty,
    LabMateDoctorFieldDutyTolerance,
    LabMateDoctorFieldSilence,
    LabMateDoctorFieldCount
} LabMateDoctorField;

typedef struct {
    LabMateDoctorReference reference;
    uint8_t source;
    uint8_t field;
    uint32_t frequency_step_hz;
} LabMateDoctorPanel;

typedef enum {
    LabMateDoctorPanelSetReference = 0,
    LabMateDoctorPanelNoData,
    LabMateDoctorPanelBusy,
    LabMateDoctorPanelUnsafe,
    LabMateDoctorPanelInsufficient,
    LabMateDoctorPanelAssessed
} LabMateDoctorPanelStatus;

typedef struct {
    LabMateDoctorPanelStatus status;
    LabMateDoctorResult doctor;
} LabMateDoctorPanelAssessment;

void labmate_doctor_panel_init(LabMateDoctorPanel* panel);
void labmate_doctor_panel_move(LabMateDoctorPanel* panel, int8_t direction);
void labmate_doctor_panel_edit(LabMateDoctorPanel* panel, int8_t direction);
void labmate_doctor_panel_step(LabMateDoctorPanel* panel);
LabMateDoctorPanelAssessment labmate_doctor_panel_assess(
    const LabMateDoctorPanel* panel, const LabMateDashboardStore* store);
const char* labmate_doctor_panel_status_text(const LabMateDoctorPanelAssessment* status);
