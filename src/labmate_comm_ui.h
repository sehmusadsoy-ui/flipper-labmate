#pragma once

/* Shared 128x64 presentation for communication tools. Display-only:
 * no UART/I2C/OneWire access, GPIO writes, lease changes or input handling. */
#include "ui_kit.h"

static inline void labmate_comm_ui_header(
    Canvas* canvas, const char* title, const char* status, bool emphasized) {
    if(!canvas || !title || !status) return;
    canvas_set_font(canvas, FontSecondary);
    const uint16_t label_width = canvas_string_width(canvas, status);
    if(!label_width || label_width > 38U) return;
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

static inline void labmate_comm_ui_keys(
    Canvas* canvas, UiKitKey primary_key, const char* primary,
    UiKitKey secondary_key, const char* secondary) {
    (void)ui_kit_key_hint(canvas, 4U, primary_key, primary);
    (void)ui_kit_key_hint(canvas, 74U, secondary_key, secondary);
}
