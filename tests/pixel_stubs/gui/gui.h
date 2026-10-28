#pragma once
/* CI-only Canvas ABI for pure pixel-header geometry tests; no firmware. */
#include <stdint.h>
typedef struct Canvas Canvas;
typedef enum { FontSecondary, FontPrimary, FontBigNumbers } Font;
typedef enum { ColorBlack, ColorWhite } Color;
void canvas_set_font(Canvas*, Font);
uint16_t canvas_string_width(Canvas*, const char*);
void canvas_set_color(Canvas*, Color);
void canvas_draw_rbox(Canvas*, int32_t, int32_t, int32_t, int32_t, int32_t);
void canvas_draw_rframe(Canvas*, int32_t, int32_t, int32_t, int32_t, int32_t);
void canvas_draw_str(Canvas*, int32_t, int32_t, const char*);
