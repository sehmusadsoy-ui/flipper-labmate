#pragma once
#include <furi.h>
#include <gui/gui.h>
#include <input/input.h>
#include "labmate_internal.h"

/* Read-only GUI rendering and rate control; never performs SD/IRQ work. */
void labmate_view_render_callback(Canvas* canvas, void* ctx);
void labmate_view_input_callback(InputEvent* input_event, void* ctx);
bool labmate_screen_uses_gpio(LabMateScreen screen);
typedef struct {
    uint32_t pulse_redraw_interval;
    uint32_t pulse_busy_redraw_interval;
    uint32_t pulse_fast_period_cycles;
    uint32_t pulse_redraw_last_tick;
    uint32_t normal_redraw_interval;
    uint32_t normal_redraw_last_tick;
} LabMateRedrawThrottle;
void labmate_redraw_init(LabMateRedrawThrottle* state);
void labmate_redraw_maybe(LabMateRedrawThrottle* state, LabMateApp* app,
                          FuriStatus status, InputEvent event, ViewPort* viewport);
