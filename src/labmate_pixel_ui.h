#pragma once

/* Shared LabMate E11 pixel UI: visual-only, no state, I/O, GPIO or capture.
 * Draw a monochrome state pill and measured header text at y=0..11.
 * The action hints match the GPIO/Counter instrument hint geometry. */
#include "ui_kit.h"

static inline void labmate_pixel_header(
    Canvas* canvas, const char* title, const char* status, bool emphasized) {
    if(!canvas || !title || !status) return;
    canvas_set_font(canvas, FontSecondary);
    const uint16_t label_width = canvas_string_width(canvas, status);
    /* A seven-character status (e.g. DELETED) must not disappear.
     * The subsequent measured title/chip collision guard still applies. */
    if(!label_width || label_width > 60U) return;
    const uint8_t chip_width = (uint8_t)(label_width + 12U);
    const uint8_t x = (uint8_t)(127U - chip_width);
    if(canvas_string_width(canvas, title) + 15U >= x) return;
    ui_kit_back_title(canvas, title, NULL, NULL);
    canvas_set_color(canvas, ColorBlack);
    if(emphasized) {
        canvas_draw_rbox(canvas, x, 0U, chip_width, 11U, 3U);
        canvas_set_color(canvas, ColorWhite);
    } else {
        canvas_draw_rframe(canvas, x, 0U, chip_width, 11U, 3U);
    }
    canvas_draw_str(canvas, x + 6U, 8U, status);
    canvas_set_color(canvas, ColorBlack);
}

static inline void labmate_pixel_keys(
    Canvas* canvas, UiKitKey primary_key, const char* primary,
    UiKitKey secondary_key, const char* secondary) {
    (void)ui_kit_key_hint(canvas, 4U, primary_key, primary);
    (void)ui_kit_key_hint(canvas, 66U, secondary_key, secondary);
}
