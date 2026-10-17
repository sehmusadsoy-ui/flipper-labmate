#include "labmate_scope_display.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
struct Canvas {uint16_t lines; uint16_t labels; bool found_wait; bool found_live; bool found_busy;};
void canvas_set_font(Canvas* c, Font f) {(void)c; assert(f == FontSecondary);}
void canvas_draw_str(Canvas* c, int32_t x, int32_t y, const char* text) {
    assert(x >= 0 && x < 128 && y >= 0 && y < 64 && text);
    ++c->labels;
    if(strstr(text, "WAIT REAL EDGE")) c->found_wait = true;
    if(strstr(text, "LIVE")) c->found_live = true;
    if(strstr(text, "BUSY")) c->found_busy = true;
}
void canvas_draw_line(Canvas* c, int32_t x0, int32_t y0, int32_t x1, int32_t y1) {
    assert(x0 >= 0 && x0 < 128 && x1 >= 0 && x1 < 128);
    assert(y0 >= 0 && y0 < 64 && y1 >= 0 && y1 < 64);
    ++c->lines;
}
int main(void) {
    struct Canvas c = {0};
    LabMateScopeDisplay d = {.state = LabMateScopeDisplayArmed,
                             .plot = {.result = LabMateScopePlotNoEdges}};
    assert(labmate_scope_display_draw(&c, &d));
    assert(c.found_wait && c.lines == 2); /* only title and footer separator */
    c = (struct Canvas){0};
    d.state = LabMateScopeDisplayNoTrigger;
    assert(labmate_scope_display_draw(&c, &d));
    assert(!c.found_wait && c.lines == 2); /* no invented waveform */
    c = (struct Canvas){0};
    LabMateScopeEdge edges[] = {{.tick=10,.high=true},{.tick=20,.high=false,.delta_ticks=10}};
    LabMateScopePlotLine lines[2];
    d.plot = labmate_scope_plot_project(edges,2,false,lines,2);
    d.lines = lines;
    d.total_edges = 2;
    d.state = LabMateScopeDisplayRunning;
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.lines == 4 && c.found_live); /* 2 waveform lines + 2 separators */
    c=(struct Canvas){0};
    d.state = LabMateScopeDisplayBusy;
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.lines==2 && c.found_busy); /* do not display stale trace as live */
    c=(struct Canvas){0};
    d.state = LabMateScopeDisplayRunning;
    lines[0].x0 = 255;
    assert(!labmate_scope_display_draw(&c,&d) && c.lines==0 && c.labels==0);
    assert(!labmate_scope_display_draw(NULL,&d));
    assert(!labmate_scope_display_draw(&c,NULL));
    puts("v1.9 Logic Scope view-only Canvas mock PASS");
    return 0;
}
