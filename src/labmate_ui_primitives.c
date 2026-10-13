#include "labmate_ui_primitives.h"
#include "labmate_navigation.h"
#include <string.h>

/* ---------- STATELESS DRAWING PRIMITIVES (v1.6-dev) ---------- */

void ui_badge(
    Canvas* canvas,
    uint8_t x,
    uint8_t y,
    uint8_t w,
    const char* text,
    bool filled) {

    if(filled) {
        canvas_draw_box(canvas, x, y, w, 11);
        canvas_set_color(canvas, ColorWhite);
    } else {
        canvas_draw_frame(canvas, x, y, w, 11);
    }

    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, x + 4, y + 8, text);

    if(filled) {
        canvas_set_color(canvas, ColorBlack);
    }
}

void ui_key(
    Canvas* canvas,
    uint8_t x,
    const char* key,
    const char* label) {

    canvas_draw_frame(canvas, x, 53, 18, 10);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, x + 3, 61, key);
    canvas_draw_str(canvas, x + 21, 61, label);
}

/* Two balanced 62px footer zones with readable outlined keycaps.
 * A max 4-letter key + 4-letter action fits inside each 62px zone;
 * short keys can pair with longer actions (e.g. LR/SOURCE).
 * Avoid glyph arrows: they are not reliably legible on all LCD fonts.
 */
static void ui_footer_action(
    Canvas* canvas,
    uint8_t x,
    const char* key,
    const char* action) {
    const size_t key_chars = strlen(key);
    const uint8_t key_width = (uint8_t)(key_chars * 6U + 6U);
    canvas_draw_frame(canvas, x, 54, key_width, 10);
    canvas_set_font(canvas, FontSecondary);
    canvas_draw_str(canvas, x + 3, 62, key);
    canvas_draw_str(canvas, x + key_width + 3, 62, action);
}

void ui_footer_pair(
    Canvas* canvas,
    const char* left_key,
    const char* left_action,
    const char* right_key,
    const char* right_action) {
    canvas_draw_line(canvas, 0, 52, 127, 52);
    ui_footer_action(canvas, 2, left_key, left_action);
    ui_footer_action(canvas, 66, right_key, right_action);
}

/* Small, distinct 12x12 instrument pictograms.
 * No bitmaps/fonts; all menu icons fit inside the 16px icon gutter.
 */
static void ui_icon_gpio(Canvas* c, uint8_t x, uint8_t y) {
    canvas_draw_frame(c, x + 3, y + 2, 7, 8);
    for(uint8_t i = 0; i < 3; ++i) {
        canvas_draw_line(c, x + 1, y + 3 + i * 3, x + 3, y + 3 + i * 3);
        canvas_draw_line(c, x + 10, y + 3 + i * 3, x + 12, y + 3 + i * 3);
    }
}

static void ui_icon_frequency(Canvas* c, uint8_t x, uint8_t y) {
    /* Meter dial and pointer. */
    canvas_draw_frame(c, x + 1, y + 1, 11, 10);
    canvas_draw_line(c, x + 3, y + 8, x + 6, y + 4);
    canvas_draw_line(c, x + 6, y + 4, x + 9, y + 7);
    canvas_draw_dot(c, x + 6, y + 8);
}

static void ui_icon_pulse(Canvas* c, uint8_t x, uint8_t y) {
    /* One HIGH and one LOW interval in a digital pulse train. */
    canvas_draw_line(c, x, y + 9, x + 2, y + 9);
    canvas_draw_line(c, x + 2, y + 9, x + 2, y + 2);
    canvas_draw_line(c, x + 2, y + 2, x + 7, y + 2);
    canvas_draw_line(c, x + 7, y + 2, x + 7, y + 9);
    canvas_draw_line(c, x + 7, y + 9, x + 12, y + 9);
}

static void ui_icon_generator(Canvas* c, uint8_t x, uint8_t y) {
    /* Outgoing waveform: short square pulse ending in an arrow. */
    canvas_draw_line(c, x, y + 9, x + 2, y + 9);
    canvas_draw_line(c, x + 2, y + 9, x + 2, y + 4);
    canvas_draw_line(c, x + 2, y + 4, x + 6, y + 4);
    canvas_draw_line(c, x + 6, y + 4, x + 6, y + 9);
    canvas_draw_line(c, x + 6, y + 9, x + 11, y + 9);
    canvas_draw_line(c, x + 9, y + 7, x + 11, y + 9);
    canvas_draw_line(c, x + 9, y + 11, x + 11, y + 9);
}

static void ui_icon_logger(Canvas* c, uint8_t x, uint8_t y) {
    /* Save-to-storage symbol: disk with recorded data. */
    canvas_draw_frame(c, x + 1, y + 1, 11, 11);
    canvas_draw_frame(c, x + 3, y + 2, 7, 3);
    canvas_draw_frame(c, x + 4, y + 7, 5, 4);
}

static void ui_icon_history(Canvas* c, uint8_t x, uint8_t y) {
    /* Circular history arrow and clock hands. */
    canvas_draw_line(c, x + 3, y + 2, x + 9, y + 2);
    canvas_draw_line(c, x + 9, y + 2, x + 11, y + 5);
    canvas_draw_line(c, x + 11, y + 5, x + 11, y + 9);
    canvas_draw_line(c, x + 11, y + 9, x + 7, y + 11);
    canvas_draw_line(c, x + 7, y + 11, x + 3, y + 9);
    canvas_draw_line(c, x + 3, y + 9, x + 2, y + 6);
    canvas_draw_line(c, x + 2, y + 6, x + 4, y + 6);
    canvas_draw_line(c, x + 2, y + 6, x + 2, y + 4);
    canvas_draw_line(c, x + 7, y + 4, x + 7, y + 7);
    canvas_draw_line(c, x + 7, y + 7, x + 9, y + 8);
}

static void ui_icon_info(Canvas* c, uint8_t x, uint8_t y) {
    canvas_draw_frame(c, x + 1, y + 1, 11, 11);
    canvas_draw_box(c, x + 5, y + 3, 2, 2);
    canvas_draw_line(c, x + 6, y + 6, x + 6, y + 9);
}

static void ui_icon_profiles(Canvas* c, uint8_t x, uint8_t y) {
    /* Three layered saved presets. */
    canvas_draw_frame(c, x + 0, y + 1, 8, 8);
    canvas_draw_frame(c, x + 2, y + 3, 8, 8);
    canvas_draw_line(c, x + 5, y + 5, x + 11, y + 5);
    canvas_draw_line(c, x + 5, y + 7, x + 11, y + 7);
}

static void ui_icon_counter(Canvas* c, uint8_t x, uint8_t y) {
    /* Tally marks + a group strike-through. */
    for(uint8_t i = 0; i < 4; ++i) {
        canvas_draw_line(c, x + 2 + i * 3, y + 2, x + 2 + i * 3, y + 10);
    }
    canvas_draw_line(c, x, y + 9, x + 12, y + 3);
}

static void ui_icon_button(Canvas* c, uint8_t x, uint8_t y) {
    /* Open contact switch and push actuator. */
    canvas_draw_line(c, x + 1, y + 9, x + 4, y + 9);
    canvas_draw_line(c, x + 9, y + 9, x + 12, y + 9);
    canvas_draw_line(c, x + 4, y + 9, x + 8, y + 6);
    canvas_draw_line(c, x + 6, y + 1, x + 6, y + 4);
    canvas_draw_line(c, x + 3, y + 1, x + 9, y + 1);
}

static void ui_icon_alerts(Canvas* c, uint8_t x, uint8_t y) {
    /* Triangle warning; no overlap with the pulse waveform icon. */
    canvas_draw_line(c, x + 6, y + 1, x, y + 11);
    canvas_draw_line(c, x + 6, y + 1, x + 12, y + 11);
    canvas_draw_line(c, x, y + 11, x + 12, y + 11);
    canvas_draw_line(c, x + 6, y + 4, x + 6, y + 7);
    canvas_draw_dot(c, x + 6, y + 9);
}

static void ui_icon_uart(Canvas* c, uint8_t x, uint8_t y) {
    canvas_draw_frame(c, x, y + 1, 13, 11);
    canvas_draw_line(c, x + 2, y + 4, x + 5, y + 4);
    canvas_draw_line(c, x + 7, y + 4, x + 11, y + 4);
    canvas_draw_line(c, x + 2, y + 8, x + 6, y + 8);
    canvas_draw_line(c, x + 8, y + 8, x + 11, y + 8);
}

static void ui_icon_i2c(Canvas* c, uint8_t x, uint8_t y) {
    /* Two clock/data rails and discrete addressed-device nodes. */
    canvas_draw_line(c, x + 1, y + 3, x + 11, y + 3);
    canvas_draw_line(c, x + 1, y + 9, x + 11, y + 9);
    canvas_draw_box(c, x + 3, y + 1, 2, 5);
    canvas_draw_box(c, x + 8, y + 7, 2, 5);
}

void ui_draw_menu_icon(Canvas* canvas, uint8_t item, uint8_t x, uint8_t y) {
    switch(item) {
    case LabMateToolGpio: ui_icon_gpio(canvas, x, y); break;
    case LabMateToolFrequency: ui_icon_frequency(canvas, x, y); break;
    case LabMateToolPulse: ui_icon_pulse(canvas, x, y); break;
    case LabMateToolGenerator: ui_icon_generator(canvas, x, y); break;
    case LabMateToolLogger: ui_icon_logger(canvas, x, y); break;
    case LabMateToolHistory: ui_icon_history(canvas, x, y); break;
    case LabMateToolAbout: ui_icon_info(canvas, x, y); break;
    case LabMateToolProfiles: ui_icon_profiles(canvas, x, y); break;
    case LabMateToolCounter: ui_icon_counter(canvas, x, y); break;
    case LabMateToolButton: ui_icon_button(canvas, x, y); break;
    case LabMateToolAlerts: ui_icon_alerts(canvas, x, y); break;
    case LabMateToolUart: ui_icon_uart(canvas, x, y); break;
    case LabMateToolI2c: ui_icon_i2c(canvas, x, y); break;
    default: break;
    }
}


void ui_draw_header(
    Canvas* canvas,
    const char* title) {

    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str(canvas, 2, 10, title);

    canvas_draw_line(canvas, 0, 13, 127, 13);
}

