#pragma once
#include "labmate_internal.h"
/* UI only. Never starts hardware, writes storage, or synthesizes samples. */
void labmate_dashboard_screen_draw(Canvas* canvas, const LabMateApp* app);
