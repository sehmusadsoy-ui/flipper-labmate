#pragma once
#include <stdbool.h>
#include <stdint.h>

/* v1.7 PWM Studio: conservative ranges for TIM1/PA7.
 * Separate from GPIO capture and portable for host tests.
 */
#define LABMATE_PWM_PRESET_COUNT 15U
#define LABMATE_PWM_CUSTOM_INDEX 15U
#define LABMATE_PWM_MIN_HZ 1U
#define LABMATE_PWM_MAX_HZ 50000U
#define LABMATE_PWM_MIN_DUTY 5U
#define LABMATE_PWM_MAX_DUTY 95U
#define LABMATE_PWM_DEFAULT_DUTY 50U

bool labmate_pwm_settings_valid(uint32_t hz, uint8_t duty);
uint32_t labmate_pwm_adjust_hz(uint32_t current, int8_t direction, uint32_t step);
uint8_t labmate_pwm_adjust_duty(uint8_t current, int8_t direction);
