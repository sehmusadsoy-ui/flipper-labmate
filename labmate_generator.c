#include "labmate_generator.h"
#include <furi_hal_pwm.h>

/* Existing 15 verified presets are unmodified, followed by CUSTOM in UI. */
const uint32_t labmate_generator_frequencies[] = {
    1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000,
};
static const uint32_t labmate_custom_steps[] = {1U, 10U, 100U, 1000U};

uint32_t labmate_generator_frequency(const LabMateApp* app) {
    if(app->generator_freq_index == LABMATE_PWM_CUSTOM_INDEX) {
        return app->generator_editing ?
            app->generator_custom_draft_hz : app->generator_custom_hz;
    }
    if(app->generator_freq_index >= LABMATE_PWM_PRESET_COUNT) return 0U;
    return labmate_generator_frequencies[app->generator_freq_index];
}

static void labmate_generator_apply_running(LabMateApp* app) {
    if(!app->generator_running) return;
    const uint32_t hz = labmate_generator_frequency(app);
    if(labmate_pwm_settings_valid(hz, app->generator_duty_percent)) {
        /* TIM1 remains owned by PA7; update without stop/restart. */
        furi_hal_pwm_set_params(
            FuriHalPwmOutputIdTim1PA7, hz, app->generator_duty_percent);
    }
}

void labmate_generator_stop(LabMateApp* app) {
    if(app->generator_running) furi_hal_pwm_stop(FuriHalPwmOutputIdTim1PA7);
    app->generator_running = false;
    app->generator_state = false;
}

void labmate_generator_start(LabMateApp* app) {
    if(app->generator_running || app->generator_editing) return;
    const uint32_t hz = labmate_generator_frequency(app);
    if(!labmate_pwm_settings_valid(hz, app->generator_duty_percent)) return;
    /* Dedicated TIM1 hardware PWM: no per-edge GPIO ISR. */
    furi_hal_pwm_start(FuriHalPwmOutputIdTim1PA7, hz, app->generator_duty_percent);
    app->generator_running = true;
    app->generator_state = false;
}

void labmate_generator_change_frequency(LabMateApp* app, int8_t direction) {
    if(app->generator_editing || direction == 0) return;
    const uint8_t count = LABMATE_PWM_CUSTOM_INDEX + 1U;
    if(direction > 0) {
        app->generator_freq_index = (uint8_t)((app->generator_freq_index + 1U) % count);
    } else {
        app->generator_freq_index =
            (uint8_t)((app->generator_freq_index + count - 1U) % count);
    }
    labmate_generator_apply_running(app);
}

void labmate_generator_change_duty(LabMateApp* app, int8_t direction) {
    if(app->generator_editing) return;
    app->generator_duty_percent =
        labmate_pwm_adjust_duty(app->generator_duty_percent, direction);
    labmate_generator_apply_running(app);
}

bool labmate_generator_begin_custom_edit(LabMateApp* app) {
    /* An unfinished edit must never change a running generator. */
    if(app->generator_running || app->generator_editing) return false;
    app->generator_edit_original_index = app->generator_freq_index;
    app->generator_custom_draft_hz = app->generator_custom_hz;
    app->generator_custom_step_index = 0U;
    app->generator_freq_index = LABMATE_PWM_CUSTOM_INDEX;
    app->generator_editing = true;
    return true;
}

uint32_t labmate_generator_custom_step_hz(const LabMateApp* app) {
    const uint8_t i = app->generator_custom_step_index;
    return labmate_custom_steps[i < 4U ? i : 0U];
}

void labmate_generator_custom_adjust(LabMateApp* app, int8_t direction) {
    if(!app->generator_editing || app->generator_running) return;
    app->generator_custom_draft_hz = labmate_pwm_adjust_hz(
        app->generator_custom_draft_hz, direction, labmate_generator_custom_step_hz(app));
}

void labmate_generator_custom_step(LabMateApp* app, int8_t direction) {
    if(!app->generator_editing || app->generator_running) return;
    if(direction > 0 && app->generator_custom_step_index < 3U) {
        ++app->generator_custom_step_index;
    } else if(direction < 0 && app->generator_custom_step_index > 0U) {
        --app->generator_custom_step_index;
    }
}

void labmate_generator_finish_custom_edit(LabMateApp* app, bool save) {
    if(!app->generator_editing) return;
    if(!app->generator_running && save &&
       labmate_pwm_settings_valid(app->generator_custom_draft_hz,
                                  app->generator_duty_percent)) {
        app->generator_custom_hz = app->generator_custom_draft_hz;
    } else {
        app->generator_freq_index = app->generator_edit_original_index;
    }
    app->generator_editing = false;
}
