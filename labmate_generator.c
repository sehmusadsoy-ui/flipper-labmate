#include "labmate_generator.h"

#include <furi_hal_pwm.h>

/* Keep v1.6.1's tested presets and 50% duty unchanged during extraction. */
const uint32_t labmate_generator_frequencies[] = {
    1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000,
};
#define LABMATE_GENERATOR_PRESET_COUNT \
    (sizeof(labmate_generator_frequencies) / sizeof(labmate_generator_frequencies[0]))

void labmate_generator_stop(LabMateApp* app) {
    if(app->generator_running) {
        furi_hal_pwm_stop(FuriHalPwmOutputIdTim1PA7);
    }
    app->generator_running = false;
    app->generator_state = false;
}

void labmate_generator_start(LabMateApp* app) {
    if(app->generator_running || app->generator_freq_index >= LABMATE_GENERATOR_PRESET_COUNT) {
        return;
    }
    const uint32_t freq = labmate_generator_frequencies[app->generator_freq_index];
    if(freq == 0U) return;

    /* PA7 / TIM1 hardware PWM: no per-edge ISR or CPU polling. */
    furi_hal_pwm_start(FuriHalPwmOutputIdTim1PA7, freq, 50U);
    app->generator_running = true;
    app->generator_state = false;
}

void labmate_generator_change_frequency(LabMateApp* app, int8_t direction) {
    /* Preserve the existing 15-item circular key navigation. */
    if(direction > 0) {
        app->generator_freq_index++;
        if(app->generator_freq_index >= LABMATE_GENERATOR_PRESET_COUNT) {
            app->generator_freq_index = 0U;
        }
    } else if(direction < 0) {
        if(app->generator_freq_index == 0U) {
            app->generator_freq_index = LABMATE_GENERATOR_PRESET_COUNT - 1U;
        } else {
            app->generator_freq_index--;
        }
    } else {
        return;
    }

    /* Do not reset/re-acquire TIM1/PA7 while PWM is running. */
    if(app->generator_running) {
        furi_hal_pwm_set_params(
            FuriHalPwmOutputIdTim1PA7,
            labmate_generator_frequencies[app->generator_freq_index],
            50U);
    }
}
