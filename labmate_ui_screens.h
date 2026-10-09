#pragma once

#include "labmate_internal.h"

/* View-only drawing: called from render_callback with the app mutex held.
 * These functions never access GPIO, timers, interrupts or microSD.
 */
void draw_about(Canvas* canvas);
void draw_history(Canvas* canvas, LabMateApp* app);
void draw_history_detail(Canvas* canvas, LabMateApp* app);
void draw_menu(Canvas* canvas, LabMateApp* app);
void draw_gpio(Canvas* canvas, LabMateApp* app);
void draw_frequency(Canvas* canvas, LabMateApp* app);
void draw_generator(Canvas* canvas, LabMateApp* app);
void draw_pulse(Canvas* canvas, LabMateApp* app);
void draw_logger(Canvas* canvas, LabMateApp* app);
