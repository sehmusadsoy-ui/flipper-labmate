#pragma once
/* Pure 128x64 Scope presentation chrome. No GPIO/IRQ/storage and no heap.
 * FontSecondary: host geometry upper bound 6 pixels per ASCII glyph.
 * Three visually separated controls use intentionally short parenthesized
 * key names: (OK)Run / (v)Pg / (B)Exit. (B) means hardware BACK.
 */
#include <gui/gui.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

static inline void labmate_scope_ui_text(
    Canvas* c, Font font, int32_t x, int32_t y, const char* s) {
    canvas_set_font(c, font);
    canvas_draw_str(c, x, y, s);
}

static inline bool labmate_scope_ui_header(
    Canvas* c, const char* title, const char* page) {
    if(!c || !title || !page ||
       strlen(title) > 9U || strlen(page) > 3U) return false;
    labmate_scope_ui_text(c, FontPrimary, 3, 11, title);
    labmate_scope_ui_text(c, FontSecondary, 82, 9, page);
    labmate_scope_ui_text(c, FontSecondary, 105, 9, "PC1");
    canvas_draw_line(c, 0, 13, 127, 13);
    return true;
}

/* Three independent short labels; columns [2..43], [47..76], [85..126].
 * No misleading greyed-out controls: center is blank during active capture.
 * Validate BEFORE any draw, including the caller's previous content. */
static inline bool labmate_scope_ui_footer(
    Canvas* c, const char* left, const char* center) {
    if(!c || !left || !center ||
       strlen(left) > 7U || strlen(center) > 5U) return false;
    canvas_draw_line(c, 0, 54, 127, 54);
    canvas_draw_line(c, 45, 56, 45, 63);
    canvas_draw_line(c, 82, 56, 82, 63);
    if(left[0]) labmate_scope_ui_text(c, FontSecondary, 2, 62, left);
    if(center[0]) labmate_scope_ui_text(c, FontSecondary, 47, 62, center);
    labmate_scope_ui_text(c, FontSecondary, 85, 62, "(B)Exit");
    return true;
}
