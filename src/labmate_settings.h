#pragma once
#include <gui/gui.h>
#include <input/input.h>
#include "labmate_internal.h"
#include "labmate_deferred.h"

void labmate_settings_draw(Canvas* canvas, const LabMateApp* app);
void labmate_settings_input(
    LabMateApp* app, InputEvent event, LabMateDeferredWork* work);

