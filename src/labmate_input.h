#pragma once
#include <furi.h>
#include <input/input.h>
#include "labmate_internal.h"
#include "labmate_deferred.h"

void labmate_input_dispatch(LabMateApp* app, FuriStatus status,
                            InputEvent event, LabMateDeferredWork* work);
