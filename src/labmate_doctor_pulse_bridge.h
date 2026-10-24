#pragma once
/* Device-thread Pulse producer. No direct IRQ writes; never start/stop HAL.
 * The caller must invoke prepare BEFORE native Pulse stop, finish AFTER.
 */
#include "labmate_internal.h"

void labmate_doctor_pulse_started(LabMateApp* app);
void labmate_doctor_pulse_observe_poll(LabMateApp* app);
void labmate_doctor_pulse_prepare_stop(LabMateApp* app);
void labmate_doctor_pulse_finish_stop(LabMateApp* app);
void labmate_doctor_pulse_abandon(LabMateApp* app);
