#pragma once
#include "labmate_internal.h"

/* App-thread measurement state: no file I/O and no GPIO lifecycle. */
void measurement_reset(LabMateApp* app);
void frequency_stats_reset(LabMateApp* app);
void pulse_stats_reset(LabMateApp* app);
void pulse_stats_window_reset(LabMateApp* app);
void measurement_update(LabMateApp* app);
