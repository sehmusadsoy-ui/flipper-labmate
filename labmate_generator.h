#pragma once

/* TIM1 / PA7 generator hardware lifecycle.
 * The app owns state transitions; this module owns PWM HAL calls and presets.
 * PWM must stay stopped on app exit and preserve PA7 reservation while RUN.
 */
#include "labmate_internal.h"

void labmate_generator_start(LabMateApp* app);
void labmate_generator_stop(LabMateApp* app);
void labmate_generator_change_frequency(LabMateApp* app, int8_t direction);
