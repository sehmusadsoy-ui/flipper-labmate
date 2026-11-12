#pragma once
#include <furi.h>
#include <input/input.h>
#include "labmate_internal.h"

/* App-thread input shaping that sits in front of labmate_input_dispatch().
 * UI pacing only: no GPIO, IRQ, timer, lease or storage access.
 *
 * - Hold-to-repeat is admitted for value editors only and is handed to the
 *   screen's existing single-step path. Navigation, pin changes, RUN/STOP
 *   and confirmations never auto-repeat.
 * - The Short/Long event that belongs to the menu OK press which opened
 *   Signal Doctor is dropped, so entering the tool cannot start an edit.
 *
 * Returns false when the event must not reach the dispatcher. */
bool labmate_input_prefilter(LabMateApp* app, FuriStatus status, InputEvent* event);

/* Call after dispatch with the screen that was visible before it. */
void labmate_input_postfilter(
    LabMateApp* app, FuriStatus status, const InputEvent* event,
    LabMateScreen screen_before);
