#pragma once
/* Deterministic advisory strings. No hardware-defect claims or hidden probes. */
#include "labmate_doctor_panel.h"
typedef struct {
    const char* finding;
    const char* evidence;
    const char* next_check;
} LabMateDoctorAdvice;
LabMateDoctorAdvice labmate_doctor_advice(
    const LabMateDoctorPanelAssessment* assessment);
