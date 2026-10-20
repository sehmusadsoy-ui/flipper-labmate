#pragma once
/* Host-only stub for read-only Canvas renderer regression.
 * This stub is used ONLY by native host unit tests, not firmware.
 */
#include <stdint.h>

typedef struct Canvas Canvas;
typedef enum { FontSecondary = 0, FontPrimary = 1 } Font;
void canvas_set_font(Canvas* canvas, Font font);
void canvas_draw_str(Canvas* canvas, int32_t x, int32_t y, const char* text);
void canvas_draw_line(
    Canvas* canvas, int32_t x0, int32_t y0, int32_t x1, int32_t y1);

/* Additional host-only Canvas primitives for the shared LabMate footers. */
typedef enum { ColorBlack = 0, ColorWhite = 1 } Color;
void canvas_set_color(Canvas* canvas, Color color);
void canvas_draw_box(Canvas* canvas, int32_t x, int32_t y, int32_t w, int32_t h);
void canvas_draw_frame(Canvas* canvas, int32_t x, int32_t y, int32_t w, int32_t h);
void canvas_draw_dot(Canvas* canvas, int32_t x, int32_t y);
