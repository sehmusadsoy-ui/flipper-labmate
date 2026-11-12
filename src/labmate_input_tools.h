#pragma once
#include <input/input.h>
#include "labmate_internal.h"
#include "labmate_deferred.h"

/* Dedicated screen input handlers. Called only with app UI mutex held.
 * May queue deferred SD actions but never perform storage operations.
 */
void labmate_input_menu(LabMateApp* app, InputEvent event, LabMateDeferredWork* work);
void labmate_input_profiles(LabMateApp* app, InputEvent event, LabMateDeferredWork* work);
void labmate_input_history(LabMateApp* app, InputEvent event, LabMateDeferredWork* work);
void labmate_input_history_detail(LabMateApp* app, InputEvent event, LabMateDeferredWork* work);
void labmate_input_about(LabMateApp* app, InputEvent event, LabMateDeferredWork* work);
void labmate_input_alerts(LabMateApp* app, InputEvent event, LabMateDeferredWork* work);
void labmate_input_button(LabMateApp* app, InputEvent event, LabMateDeferredWork* work);
void labmate_input_counter(LabMateApp* app, InputEvent event, LabMateDeferredWork* work);
void labmate_input_logger(LabMateApp* app, InputEvent event, LabMateDeferredWork* work);
void labmate_input_gpio(LabMateApp* app, InputEvent event, LabMateDeferredWork* work);
void labmate_input_generator(LabMateApp* app, InputEvent event, LabMateDeferredWork* work);
void labmate_input_uart(LabMateApp* app, InputEvent event, LabMateDeferredWork* work);
void labmate_input_onewire(LabMateApp* app, InputEvent event, LabMateDeferredWork* work);
void labmate_input_i2c(LabMateApp* app, InputEvent event, LabMateDeferredWork* work);

/* Hold-to-repeat acceleration for value editors: 1x for the first repeats,
 * then 10x / 100x / 1000x the base step. A fresh Press resets the streak. */
static inline uint32_t labmate_input_repeat_multiplier(const LabMateApp* app) {
    const uint8_t streak = app ? app->ui_repeat_streak : 0U;
    return streak < 5U ? 1U : streak < 15U ? 10U : streak < 30U ? 100U : 1000U;
}
