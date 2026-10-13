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
