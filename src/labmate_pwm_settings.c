#include "labmate_pwm_settings.h"

bool labmate_pwm_settings_valid(uint32_t hz, uint8_t duty) {
    return hz >= LABMATE_PWM_MIN_HZ && hz <= LABMATE_PWM_MAX_HZ &&
           duty >= LABMATE_PWM_MIN_DUTY && duty <= LABMATE_PWM_MAX_DUTY;
}

uint32_t labmate_pwm_adjust_hz(uint32_t current, int8_t direction, uint32_t step) {
    if(current < LABMATE_PWM_MIN_HZ) current = LABMATE_PWM_MIN_HZ;
    if(current > LABMATE_PWM_MAX_HZ) current = LABMATE_PWM_MAX_HZ;
    if(direction > 0) {
        if(step > LABMATE_PWM_MAX_HZ - current) return LABMATE_PWM_MAX_HZ;
        return current + step;
    }
    if(direction < 0) {
        if(step >= current) return LABMATE_PWM_MIN_HZ;
        return current - step;
    }
    return current;
}

uint8_t labmate_pwm_adjust_duty(uint8_t current, int8_t direction) {
    if(current < LABMATE_PWM_MIN_DUTY) current = LABMATE_PWM_MIN_DUTY;
    if(current > LABMATE_PWM_MAX_DUTY) current = LABMATE_PWM_MAX_DUTY;
    if(direction > 0) {
        return current >= LABMATE_PWM_MAX_DUTY - 5U ?
            LABMATE_PWM_MAX_DUTY : (uint8_t)(current + 5U);
    }
    if(direction < 0) {
        return current <= LABMATE_PWM_MIN_DUTY + 5U ?
            LABMATE_PWM_MIN_DUTY : (uint8_t)(current - 5U);
    }
    return current;
}
