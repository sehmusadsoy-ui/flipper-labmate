#pragma once

#include <gui/gui.h>
#include <stdbool.h>
#include <stdint.h>

/* Stateless 128x64 Canvas primitives: no measurement, GPIO or storage state. */
void ui_badge(
    Canvas* canvas,
    uint8_t x,
    uint8_t y,
    uint8_t w,
    const char* text,
    bool filled);

void ui_key(
    Canvas* canvas,
    uint8_t x,
    const char* key,
    const char* label);

/* The item-to-icon mapping remains identical to LabMate v1.5 Stable. */
void ui_draw_menu_icon(
    Canvas* canvas,
    uint8_t item,
    uint8_t x,
    uint8_t y);
