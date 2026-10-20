#include "labmate_scope_display.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Real LCD geometry mock, not a screenshot claim. FontPrimary is bounded to
 * 8px/cell and 11px high; secondary to 6px/cell and 8px high. */
typedef struct {int32_t x0,y0,x1,y1;} Rect;
struct Canvas {
    Font font;
    unsigned labels;
    unsigned strokes;
    unsigned frame;
    unsigned ticks;
    unsigned trace;
    bool saw_ready;
    bool saw_no_signal;
    bool saw_wave_state;
    bool saw_focus;
    bool saw_back;
    bool saw_ok;
    bool saw_busy;
    Rect text[32];
};

void canvas_set_font(Canvas* c, Font font) {
    assert(c && (font == FontPrimary || font == FontSecondary));
    c->font = font;
}
void canvas_draw_str(Canvas* c, int32_t x, int32_t y, const char* s) {
    assert(c && s && x >= 0 && y >= 0 && y < 64);
    const size_t n = strlen(s);
    const int32_t w = (int32_t)n * (c->font == FontPrimary ? 8 : 6);
    const int32_t h = c->font == FontPrimary ? 11 : 8;
    assert(n > 0 && x + w <= 128 && y - h + 1 >= 0);
    assert(c->labels < 32U);
    const Rect next = {x, y-h+1, x+w-1, y};
    for(unsigned i = 0; i < c->labels; ++i) {
        const Rect prev = c->text[i];
        const bool disjoint =
            next.x1 < prev.x0 || next.x0 > prev.x1 ||
            next.y1 < prev.y0 || next.y0 > prev.y1;
        assert(disjoint && "overlapping LCD text rectangles");
    }
    c->text[c->labels++] = next;
    if(strstr(s, "READY")) c->saw_ready=true;
    if(strstr(s, "NO SIGNAL")) c->saw_no_signal=true;
    if(strstr(s, "LIVE")) c->saw_wave_state=true;
    if(strstr(s, "ZOOM")) c->saw_focus=true;
    if(strstr(s, "BACK")) c->saw_back=true;
    if(strstr(s, "OK RUN") || strstr(s, "OK STOP")) c->saw_ok=true;
    if(strstr(s, "BUSY")) c->saw_busy=true;
}
void canvas_draw_line(Canvas* c,int32_t x0,int32_t y0,int32_t x1,int32_t y1) {
    assert(c && x0>=0 && x1>=0 && x0<128 && x1<128 &&
           y0>=0 && y1>=0 && y0<64 && y1<64);
    ++c->strokes;
    if((x0==2 && x1==125 && y0==y1 && (y0==15 || y0==42)) ||
       ((x0==2 || x0==125) && x0==x1 && y0==15 && y1==42)) {
        ++c->frame;
    } else if(x0==x1 && (x0==33 || x0==64 || x0==95) &&
              ((y0==16 && y1==18) || (y0==39 && y1==41))) {
        ++c->ticks;
    } else if((x0==0 && x1==127 && y0==y1 && (y0==13 || y0==54)) ||
              ((x0==46 || x0==92) && x0==x1 && y0==56 && y1==63)) {
        /* header/footer navigation strokes */
    } else {
        assert(x0>=(int32_t)LABMATE_SCOPE_PLOT_X_LEFT &&
               x0<=(int32_t)LABMATE_SCOPE_PLOT_X_RIGHT &&
               x1>=(int32_t)LABMATE_SCOPE_PLOT_X_LEFT &&
               x1<=(int32_t)LABMATE_SCOPE_PLOT_X_RIGHT &&
               (y0==LABMATE_SCOPE_PLOT_Y_HIGH ||
                y0==LABMATE_SCOPE_PLOT_Y_LOW) &&
               (y1==LABMATE_SCOPE_PLOT_Y_HIGH ||
                y1==LABMATE_SCOPE_PLOT_Y_LOW));
        ++c->trace;
    }
}
int main(void) {
    struct Canvas c={0};
    LabMateScopeDisplay d={.state=LabMateScopeDisplayStopped,
                            .plot={.result=LabMateScopePlotNoEdges}};
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.frame==4 && c.ticks==6 && c.trace==0);
    assert(c.saw_ready && c.saw_ok && c.saw_back);
    c=(struct Canvas){0};
    d.state=LabMateScopeDisplayArmed;
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.trace==0);
    c=(struct Canvas){0};
    d.state=LabMateScopeDisplayNoTrigger;
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.saw_no_signal && c.trace==0);
    LabMateScopeEdge edges[] = {
        {.tick=100,.high=true},
        {.tick=200,.delta_ticks=100,.high=false}
    };
    LabMateScopePlotLine segments[2];
    d.plot=labmate_scope_plot_project(edges,2,false,segments,2);
    d.lines=segments;d.total_edges=2;
    d.state=LabMateScopeDisplayRunning;
    c=(struct Canvas){0};
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.frame==4 && c.ticks==6 && c.trace==2);
    assert(c.saw_wave_state && c.saw_ok);
    d.state=LabMateScopeDisplayStopped;
    d.plot.cropped_old_edges=true;
    c=(struct Canvas){0};
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.trace==2 && c.saw_focus);
    d.state=LabMateScopeDisplayBusy;
    c=(struct Canvas){0};
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.saw_busy && c.trace==0);
    d.state=LabMateScopeDisplayUnsupported;
    c=(struct Canvas){0};
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.trace==0);
    d.state=LabMateScopeDisplayRunning;
    c=(struct Canvas){0};
    segments[0].x0=255U;
    assert(!labmate_scope_display_draw(&c,&d) && c.strokes==0 && c.labels==0);
    segments[0].x0=LABMATE_SCOPE_PLOT_X_LEFT;
    d.total_edges=LABMATE_SCOPE_MAX_EDGES+1U;
    assert(!labmate_scope_display_draw(&c,&d) && c.labels==0);
    d.total_edges=2U;
    d.plot.line_count=1U;
    assert(!labmate_scope_display_draw(&c,&d) && c.labels==0);
    d.plot.line_count=2U;
    d.plot.visible_edges=0U;
    assert(!labmate_scope_display_draw(&c,&d) && c.labels==0);
    assert(!labmate_scope_display_draw(NULL,&d));
    assert(!labmate_scope_display_draw(&c,NULL));
    puts("v1.9 calm Scope host geometry/font/real-edge guard PASS");
    return 0;
}
