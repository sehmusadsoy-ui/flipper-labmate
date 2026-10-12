#pragma once

/* PWM Studio: TIM1/PA7 owns the output for the full RUN lifecycle.
 * Preset/custom selection and duty state persist across menu navigation,
 * but PWM always stops on application exit.
 */
#include "labmate_internal.h"
#include "labmate_pwm_settings.h"

void labmate_generator_start(LabMateApp* app);
void labmate_generator_stop(LabMateApp* app);
void labmate_generator_change_frequency(LabMateApp* app, int8_t direction);
void labmate_generator_change_duty(LabMateApp* app, int8_t direction);
uint32_t labmate_generator_frequency(const LabMateApp* app);

bool labmate_generator_begin_custom_edit(LabMateApp* app);
void labmate_generator_custom_adjust(LabMateApp* app, int8_t direction);
void labmate_generator_custom_step(LabMateApp* app, int8_t direction);
void labmate_generator_finish_custom_edit(LabMateApp* app, bool save);
uint32_t labmate_generator_custom_step_hz(const LabMateApp* app);
