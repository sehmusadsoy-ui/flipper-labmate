#include "labmate_scope_display.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

struct Canvas {
    unsigned separators;
    unsigned frame;
    unsigned grid;
    unsigned trace;
    unsigned labels;
    bool found_wait;
    bool found_no_trigger;
    bool found_live;
    bool found_busy;
    bool found_zoom;
    bool found_footer;
};
void canvas_set_font(Canvas* c, Font f) {(void)c; assert(f == FontSecondary);}
void canvas_draw_str(Canvas* c, int32_t x, int32_t y, const char* text) {
    assert(x >= 0 && x < 128 && y >= 0 && y < 64 && text);
    assert((size_t)x + strlen(text) * 6U <= 128U);
    ++c->labels;
    if(strstr(text, "WAIT PC1 EDGE")) c->found_wait = true;
    if(strstr(text, "NO TRIGGER")) c->found_no_trigger = true;
    if(strstr(text, "LIVE")) c->found_live = true;
    if(strstr(text, "BUSY")) c->found_busy = true;
    if(strstr(text, "ZOOM")) c->found_zoom = true;
    if(strstr(text, "BK:EXIT")) c->found_footer = true;
    if(strstr(text, " EDGES ")) {
        assert(y == 50);
        assert(LABMATE_SCOPE_PLOT_Y_LOW <= (uint8_t)(y - 11));
    }
}
void canvas_draw_line(Canvas* c, int32_t x0, int32_t y0, int32_t x1, int32_t y1) {
    assert(x0 >= 0 && x0 < 128 && x1 >= 0 && x1 < 128);
    assert(y0 >= 0 && y0 < 64 && y1 >= 0 && y1 < 64);
    if(y0 == 13 && y1 == 13) {
        assert(x0 == 0 && x1 == 127);
        ++c->separators;
    } else if(y0 == 53 && y1 == 53) {
        assert(x0 == 0 && x1 == 127);
        ++c->separators;
    } else if((x0 == 1 && x1 == 126 && (y0 == 15 || y0 == 40) && y0 == y1) ||
              ((x0 == 1 || x0 == 126) && x0 == x1 && y0 == 15 && y1 == 40)) {
        ++c->frame;
    } else if((x0 == x1 && (x0 == 26 || x0 == 51 || x0 == 76 || x0 == 101) &&
               ((y0 == 17 && y1 == 18) ||
                (y0 == 26 && y1 == 27) ||
                (y0 == 37 && y1 == 38))) ||
              (y0 == 28 && y1 == 28 && x1 == x0 + 2)) {
        assert(x0 >= 2 && x1 <= 125 && y0 >= 16 && y1 <= 39);
        ++c->grid;
    } else {
        /* Only the original hardware-observed rising/falling trace can be
         * drawn here, inside the boxed viewport's two digital levels. */
        assert(x0 >= LABMATE_SCOPE_PLOT_X_LEFT && x0 <= LABMATE_SCOPE_PLOT_X_RIGHT);
        assert(x1 >= LABMATE_SCOPE_PLOT_X_LEFT && x1 <= LABMATE_SCOPE_PLOT_X_RIGHT);
        assert((y0 == LABMATE_SCOPE_PLOT_Y_HIGH || y0 == LABMATE_SCOPE_PLOT_Y_LOW) &&
               (y1 == LABMATE_SCOPE_PLOT_Y_HIGH || y1 == LABMATE_SCOPE_PLOT_Y_LOW));
        ++c->trace;
    }
}
int main(void) {
    struct Canvas c = {0};
    LabMateScopeDisplay d = {.state = LabMateScopeDisplayArmed,
                             .plot = {.result = LabMateScopePlotNoEdges}};
    assert(labmate_scope_display_draw(&c, &d));
    assert(c.found_wait && c.found_footer);
    assert(c.separators == 2 && c.frame == 4 && c.grid == 0 && c.trace == 0);
    c = (struct Canvas){0};
    d.state = LabMateScopeDisplayNoTrigger;
    assert(labmate_scope_display_draw(&c, &d));
    assert(c.found_no_trigger && c.grid == 0 && c.trace == 0);
    c = (struct Canvas){0};
    LabMateScopeEdge edges[] = {{.tick=10,.high=true},{.tick=20,.high=false,.delta_ticks=10}};
    LabMateScopePlotLine lines[2];
    d.plot = labmate_scope_plot_project(edges, 2, false, lines, 2);
    d.lines = lines;
    d.total_edges = 2;
    d.state = LabMateScopeDisplayRunning;
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.separators == 2 && c.frame == 4 &&
           c.grid == 19 && c.trace == 2 && c.found_live);
    c = (struct Canvas){0};
    d.state = LabMateScopeDisplayBusy;
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.frame == 4 && c.grid == 0 && c.trace == 0 && c.found_busy);
    c = (struct Canvas){0};
    d.state = LabMateScopeDisplayRunning;
    lines[0].x0 = 255;
    assert(!labmate_scope_display_draw(&c,&d) && c.labels == 0 && c.trace == 0);
    lines[0].x0 = LABMATE_SCOPE_PLOT_X_LEFT;
    c = (struct Canvas){0};
    d.total_edges = LABMATE_SCOPE_MAX_EDGES + 1U;
    assert(!labmate_scope_display_draw(&c,&d) && c.labels == 0 && c.frame == 0);
    d.total_edges = LABMATE_SCOPE_MAX_EDGES;
    d.plot.cropped_old_edges = true;
    d.state = LabMateScopeDisplayNoTrigger;
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.labels > 0 && c.frame == 4 && c.found_footer);
    c = (struct Canvas){0};
    d.state = LabMateScopeDisplayStopped;
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.found_zoom && c.trace == 2);
    c = (struct Canvas){0};
    d.state = LabMateScopeDisplayUnsupported;
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.frame == 4 && c.grid == 0 && c.trace == 0);
    c = (struct Canvas){0};
    d.state = (LabMateScopeDisplayState)-1;
    assert(!labmate_scope_display_draw(&c,&d) && c.frame == 0);
    d.state = LabMateScopeDisplayRunning;
    d.plot.visible_edges = 0U;
    assert(!labmate_scope_display_draw(&c,&d) && c.frame == 0);
    d.plot.visible_edges = 2U;
    d.plot.line_count = 1U;
    assert(!labmate_scope_display_draw(&c,&d) && c.frame == 0);
    d.plot.line_count = 2U;
    d.total_edges = 1U;
    assert(!labmate_scope_display_draw(&c,&d) && c.frame == 0);
    d.total_edges = 256U;
    d.plot.result = LabMateScopePlotOneEdge;
    assert(!labmate_scope_display_draw(&c,&d) && c.frame == 0);
    assert(!labmate_scope_display_draw(NULL,&d));
    assert(!labmate_scope_display_draw(&c,NULL));
    puts("v1.9 boxed grid/focus, status/help and fail-closed Canvas host PASS");
    return 0;
}
