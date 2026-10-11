#include "labmate_pwm_settings.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    assert(labmate_pwm_settings_valid(1U, 5U));
    assert(labmate_pwm_settings_valid(50000U, 95U));
    assert(!labmate_pwm_settings_valid(0U, 50U));
    assert(!labmate_pwm_settings_valid(50001U, 50U));
    assert(!labmate_pwm_settings_valid(1000U, 4U));
    assert(!labmate_pwm_settings_valid(1000U, 96U));
    assert(labmate_pwm_adjust_hz(1000U, 1, 1U) == 1001U);
    assert(labmate_pwm_adjust_hz(1000U, -1, 10U) == 990U);
    assert(labmate_pwm_adjust_hz(49995U, 1, 1000U) == 50000U);
    assert(labmate_pwm_adjust_hz(3U, -1, 1000U) == 1U);
    assert(labmate_pwm_adjust_hz(1234U, 0, 100U) == 1234U);
    assert(labmate_pwm_adjust_hz(1U, -1, 1U) == 1U);
    assert(labmate_pwm_adjust_duty(50U, 1) == 55U);
    assert(labmate_pwm_adjust_duty(50U, -1) == 45U);
    assert(labmate_pwm_adjust_duty(95U, 1) == 95U);
    assert(labmate_pwm_adjust_duty(5U, -1) == 5U);
    assert(labmate_pwm_adjust_duty(50U, 0) == 50U);
    puts("PWM Studio portable settings tests PASS");
    return 0;
}
