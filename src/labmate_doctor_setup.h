#pragma once

/* Doctor Step 2: UI-only reference editor. All thresholds, source selection,
 * snapshot evaluation and CSV logic remain in their original modules. */
#include <gui/gui.h>
#include <stdbool.h>
#include <stdint.h>
#include "labmate_doctor_panel.h"

typedef enum {
    LabMateDoctorSetupUp,
    LabMateDoctorSetupDown,
    LabMateDoctorSetupLeft,
    LabMateDoctorSetupRight,
    LabMateDoctorSetupOk,
    LabMateDoctorSetupBack,
} LabMateDoctorSetupKey;

typedef enum {
    LabMateDoctorSetupStay,
    LabMateDoctorSetupOpenSignal,
    LabMateDoctorSetupExit,
} LabMateDoctorSetupAction;

typedef struct {
    bool editing;
    bool info_open;
    LabMateDoctorPanel before_edit;
} LabMateDoctorSetupUi;

/* Entering Doctor opens Frequency, preserving the user's reference settings.
 * No value is committed until explicit OK in edit mode; Back restores it. */
void labmate_doctor_setup_reset(LabMateDoctorSetupUi* ui, LabMateDoctorPanel* panel);
LabMateDoctorSetupAction labmate_doctor_setup_key(
    LabMateDoctorSetupUi* ui, LabMateDoctorPanel* panel,
    LabMateDoctorSetupKey key, bool long_press);

/* Draws only setup pages 1 and 2. The existing results pages remain separate. */
void labmate_doctor_setup_draw(
    Canvas* canvas, const LabMateDoctorPanel* panel,
    const LabMateDoctorSetupUi* ui, uint8_t pulse_phase);
