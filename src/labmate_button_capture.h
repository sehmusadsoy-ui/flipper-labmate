#pragma once
#include "labmate_internal.h"

/* Active-low dry-contact testing on PC1 with internal pull-up. External
 * digital sources must never exceed the Flipper's 3.3V GPIO logic level.
 * The firmware's OK/DOWN EXTI3/6 lines are never claimed.
 */
void labmate_button_capture_start(LabMateApp* app);
void labmate_button_capture_poll(LabMateApp* app);
void labmate_button_capture_stop(LabMateApp* app);
void labmate_button_capture_reset(LabMateApp* app);
void labmate_button_capture_change_quiet(LabMateApp* app, int8_t direction);
