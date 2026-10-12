#pragma once
#include "labmate_internal.h"

/* GPIO and capture transitions. Call with app mutex held.
 * Keep independent PA7/TIM1 PWM alive on screen navigation.
 */
void labmate_capture_stop_all(LabMateApp* app);
void labmate_gpio_activate(LabMateApp* app);
void labmate_gpio_change(LabMateApp* app, int8_t direction);
void labmate_logger_capture_start(LabMateApp* app);
void labmate_logger_capture_stop(LabMateApp* app);
void labmate_logger_capture_change(LabMateApp* app, int8_t direction);
