#pragma once
#include "labmate_internal.h"

/* GPIO Monitor owns poll-mode pin configuration/reads.
 * PA7 remains reserved while the independent TIM1 PWM generator is running.
 */
void labmate_monitor_gpio_activate(LabMateApp* app);
void labmate_monitor_gpio_release(LabMateApp* app, uint8_t index);
bool labmate_monitor_gpio_read(uint8_t index);
