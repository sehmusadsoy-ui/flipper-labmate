#include "labmate_generator.h"
#include <furi_hal_pwm.h>
#include <furi_hal_resources.h>

/* E11: the matched native PWM HAL acquires the sole TIM1+PA7 claim.
 * LabMate must NEVER preclaim the same mask: doing so would make the
 * native HAL reject its own START (self-deadlock).
 * This retained handle is used only for STOP release verification.
 */
static uint32_t labmate_pwm_pa7_release_probe;

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
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1)
    if(app->generator_release_fault ||
       !furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7)) {
        app->generator_blocked = true;
        app->generator_release_fault = true;
        return; /* Native PWM no longer reports an active owner. */
    }
    const uint32_t hz = labmate_generator_frequency(app);
    if(labmate_pwm_settings_valid(hz, app->generator_duty_percent)) {
        /* Only the already-acquired owner may retune a running TIM1. */
        furi_hal_pwm_set_params(
            FuriHalPwmOutputIdTim1PA7, hz, app->generator_duty_percent);
    }
#else
    app->generator_blocked = true; /* mismatched stock SDK: fail closed */
#endif
}

void labmate_generator_stop(LabMateApp* app) {
    if(!app->generator_running) return; /* STOP without RUN is a no-op. */
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1)
    if(app->generator_release_fault ||
       !furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7)) {
        /* Do not STOP a timer that may have been seized externally. */
        app->generator_blocked = true;
        app->generator_release_fault = true;
        return;
    }
    /* Native HAL stops its own TIM1 and releases its own sole lease. */
    furi_hal_pwm_stop(FuriHalPwmOutputIdTim1PA7);
    app->generator_running = false;
    app->generator_state = false;
    /* A void HAL STOP cannot report failed release. Probe the exact
     * shared claim only AFTER HAL STOP, without GPIO or timer writes.
     * If another service claims in between, conservatively stay ERR.
     */
    labmate_pwm_pa7_release_probe =
        furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7);
    if(!labmate_pwm_pa7_release_probe) {
        app->generator_release_fault = true;
        app->generator_blocked = true;
        return;
    }
    if(!furi_hal_resource_lease_release(
           labmate_pwm_pa7_release_probe, FURI_HAL_LEASE_PWM_PA7)) {
        app->generator_release_fault = true;
        app->generator_blocked = true;
        return; /* Keep the failed probe token to deny restart. */
    }
    labmate_pwm_pa7_release_probe = 0U;
    app->generator_blocked = false;
#else
    /* A stock-SDK DEV build could not have acquired TIM1 in START. */
    app->generator_blocked = true;
#endif
}

void labmate_generator_start(LabMateApp* app) {
    if(app->generator_running || app->generator_editing) return;
    if(app->generator_release_fault || labmate_pwm_pa7_release_probe != 0U) {
        app->generator_blocked = true;
        return;
    }
    const uint32_t hz = labmate_generator_frequency(app);
    if(!labmate_pwm_settings_valid(hz, app->generator_duty_percent)) return;
#if defined(FURI_HAL_RESOURCE_LEASE_API_V1)
    /* Native HAL is the only TIM1/PA7 lease owner. A second
     * preclaim from LabMate would reject this exact START request.
     */
    if(furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7)) {
        app->generator_blocked = true;
        return; /* Other PWM user: no mutation. */
    }
    furi_hal_pwm_start(FuriHalPwmOutputIdTim1PA7, hz, app->generator_duty_percent);
    if(!furi_hal_pwm_is_running(FuriHalPwmOutputIdTim1PA7)) {
        app->generator_blocked = true;
        return; /* Denied by occupied pin, clock or native lease. */
    }
    app->generator_running = true;
    app->generator_state = false;
    app->generator_blocked = false;
#else
    app->generator_blocked = true; /* never use unsafe direct HAL on stock SDK */
#endif
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
