#pragma once
#include "labmate_internal.h"
/* UI-only screen: the panel never starts capture or accesses GPIO/SD. */
void labmate_doctor_screen_draw(Canvas* canvas, const LabMateApp* app);
