#include "labmate_ui_primitives.h"

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

static void ui_icon_gpio(
    Canvas* canvas,
    uint8_t x,
    uint8_t y) {

    canvas_draw_frame(canvas, x + 2, y + 2, 8, 8);

    canvas_draw_line(canvas, x, y + 4, x + 2, y + 4);
    canvas_draw_line(canvas, x, y + 7, x + 2, y + 7);

    canvas_draw_line(canvas, x + 10, y + 4, x + 12, y + 4);
    canvas_draw_line(canvas, x + 10, y + 7, x + 12, y + 7);
}

static void ui_icon_frequency(
    Canvas* canvas,
    uint8_t x,
    uint8_t y) {

    canvas_draw_line(canvas, x, y + 7, x + 2, y + 7);
    canvas_draw_line(canvas, x + 2, y + 7, x + 4, y + 3);
    canvas_draw_line(canvas, x + 4, y + 3, x + 6, y + 9);
    canvas_draw_line(canvas, x + 6, y + 9, x + 8, y + 4);
    canvas_draw_line(canvas, x + 8, y + 4, x + 11, y + 4);
}

static void ui_icon_pulse(
    Canvas* canvas,
    uint8_t x,
    uint8_t y) {

    canvas_draw_line(canvas, x, y + 8, x + 3, y + 8);
    canvas_draw_line(canvas, x + 3, y + 8, x + 3, y + 3);
    canvas_draw_line(canvas, x + 3, y + 3, x + 7, y + 3);
    canvas_draw_line(canvas, x + 7, y + 3, x + 7, y + 8);
    canvas_draw_line(canvas, x + 7, y + 8, x + 11, y + 8);
}

static void ui_icon_generator(
    Canvas* canvas,
    uint8_t x,
    uint8_t y) {

    canvas_draw_line(canvas, x + 5, y, x + 2, y + 6);
    canvas_draw_line(canvas, x + 2, y + 6, x + 6, y + 6);
    canvas_draw_line(canvas, x + 6, y + 6, x + 4, y + 11);
    canvas_draw_line(canvas, x + 4, y + 11, x + 10, y + 4);
    canvas_draw_line(canvas, x + 10, y + 4, x + 6, y + 4);
}

static void ui_icon_info(
    Canvas* canvas,
    uint8_t x,
    uint8_t y) {

    canvas_draw_frame(canvas, x + 1, y + 1, 10, 10);
    canvas_draw_box(canvas, x + 5, y + 3, 2, 2);
    canvas_draw_line(canvas, x + 6, y + 6, x + 6, y + 9);
}

void ui_draw_menu_icon(
    Canvas* canvas,
    uint8_t item,
    uint8_t x,
    uint8_t y) {

    switch(item) {
    case 0:
        ui_icon_gpio(canvas, x, y);
        break;
    case 1:
        ui_icon_frequency(canvas, x, y);
        break;
    case 2:
        ui_icon_pulse(canvas, x, y);
        break;
    case 3:
        ui_icon_generator(canvas, x, y);
        break;
    case 4:
        ui_icon_frequency(canvas, x, y);
        break;
    case 5:
        ui_icon_frequency(canvas, x, y);
        break;
    case 6:
        ui_icon_info(canvas, x, y);
        break;
    }
}

