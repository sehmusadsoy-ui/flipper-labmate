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

/* Compact two-action footer for 128x64 screens, using parenthesized
 * key labels: (OK) START, (BACK)EXIT. 10 secondary glyphs max per 62px
 * cell; long actions use no intervening space to prevent clipping.
 * Visual-only: all existing button meanings remain unchanged.
 */
void ui_footer_pair(
    Canvas* canvas,
    const char* left_key,
    const char* left_action,
    const char* right_key,
    const char* right_action);

/* Tool-specific monochrome pictograms. */
void ui_draw_menu_icon(
    Canvas* canvas,
    uint8_t item,
    uint8_t x,
    uint8_t y);

/* Stateless instrument-style title and separator line. */
void ui_draw_header(Canvas* canvas, const char* title);
