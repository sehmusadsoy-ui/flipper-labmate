#pragma once
#include <stdbool.h>
#include <stdint.h>
typedef struct Canvas Canvas;
typedef enum { FontSecondary = 0 } Font;
void canvas_set_font(Canvas* c, Font font);
void canvas_draw_str(Canvas* c, int32_t x, int32_t y, const char* text);
void canvas_draw_line(Canvas* c, int32_t x0, int32_t y0, int32_t x1, int32_t y1);
