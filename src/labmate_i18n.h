#pragma once
/* LabMate UI translation layer (presentation only).
 *
 * Renderers keep their English literals and approved geometry. When a UI
 * source includes this header AFTER its other includes, its text calls are
 * routed through a lookup that swaps a literal for its translation and draws
 * Turkish letters that the ASCII-only Flipper fonts lack (base glyph plus a
 * procedural mark). Unknown strings, numbers and units pass through as-is.
 *
 * The hooks are weak references: a host test that links a production UI file
 * without labmate_i18n.c simply gets the original canvas calls.
 */
#include <gui/gui.h>
#include <stdint.h>

void labmate_i18n_set_language(uint8_t language);
uint8_t labmate_i18n_language(void);
/* Translation of an English UI literal, or the input when none exists. */
const char* labmate_i18n_tr(const char* text);

void labmate_i18n_draw_str(Canvas* c, int32_t x, int32_t y, const char* s)
    __attribute__((weak));
void labmate_i18n_draw_str_aligned(
    Canvas* c, int32_t x, int32_t y, int h, int v, const char* s) __attribute__((weak));
uint16_t labmate_i18n_string_width(Canvas* c, const char* s) __attribute__((weak));
void labmate_i18n_set_font(Canvas* c, int font) __attribute__((weak));
void labmate_i18n_frame_begin(Canvas* c) __attribute__((weak));

#ifndef LABMATE_I18N_IMPL
#define canvas_draw_str(c, x, y, s)                                  \
    (labmate_i18n_draw_str ? labmate_i18n_draw_str((c), (x), (y), (s)) : \
                             (canvas_draw_str)((c), (x), (y), (s)))
#define canvas_draw_str_aligned(c, x, y, h, v, s)                                      \
    (labmate_i18n_draw_str_aligned ?                                                   \
         labmate_i18n_draw_str_aligned((c), (x), (y), (int)(h), (int)(v), (s)) :       \
         (canvas_draw_str_aligned)((c), (x), (y), (h), (v), (s)))
#define canvas_string_width(c, s) \
    (labmate_i18n_string_width ? labmate_i18n_string_width((c), (s)) : \
                                 (canvas_string_width)((c), (s)))
#define canvas_set_font(c, f) \
    (labmate_i18n_set_font ? labmate_i18n_set_font((c), (int)(f)) : (canvas_set_font)((c), (f)))
#endif
