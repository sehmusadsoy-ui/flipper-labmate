#include "labmate_scope_display.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Pixel-level host geometry: secondary font 6x8, primary 8x11. */
typedef struct {int32_t x0, y0, x1, y1;} Rect;
struct Canvas {
    Font font;
    unsigned texts, frames, guides, wave, other_lines;
    Rect bounds[32];
    bool run, stop, page, exit, ready, no_signal, frequency, duty, busy;
};
void canvas_set_font(Canvas* c, Font f) {
    assert(c && (f == FontPrimary || f == FontSecondary));
    c->font=f;
}
void canvas_draw_str(Canvas* c, int32_t x, int32_t y, const char* t) {
    assert(c && t && x>=0 && y>=0 && y<64);
    const int32_t w=(int32_t)strlen(t)*(c->font==FontPrimary?8:6);
    const int32_t h=c->font==FontPrimary?11:8;
    assert(w>0 && x+w<=128 && y-h+1>=0 && c->texts<32U);
    const Rect box={x,y-h+1,x+w-1,y};
    for(unsigned i=0;i<c->texts;++i) {
        const Rect b=c->bounds[i];
        assert(box.x1<b.x0 || box.x0>b.x1 ||
               box.y1<b.y0 || box.y0>b.y1);
    }
    c->bounds[c->texts++]=box;
    if(!strcmp(t,"(OK)Run")) c->run=true;
    if(!strcmp(t,"(OK)Stop")) c->stop=true;
    if(!strcmp(t,"(v)Pg")) c->page=true;
    if(!strcmp(t,"(B)Exit")) c->exit=true;
    if(!strcmp(t,"READY")) c->ready=true;
    if(!strcmp(t,"NO SIGNAL")) c->no_signal=true;
    if(!strcmp(t,"100.00Hz")) c->frequency=true;
    if(!strcmp(t,"50.0%")) c->duty=true;
    if(!strcmp(t,"PC1 BUSY")) c->busy=true;
}
void canvas_draw_line(Canvas* c,int32_t x0,int32_t y0,int32_t x1,int32_t y1) {
    assert(c && x0>=0 && x0<128 && x1>=0 && x1<128 &&
           y0>=0 && y0<64 && y1>=0 && y1<64);
    if((x0==2 && x1==125 && y0==y1 && (y0==15 || y0==42)) ||
       ((x0==2 || x0==125) && x0==x1 && y0==15 && y1==42)) {
        ++c->frames;
    } else if((x0==x1 && ((y0==16 && y1==17) || (y0==40 && y1==41)) &&
                x0>=25 && x0<=105 && (x0-25)%20==0) ||
              (y0==y1 && x0==x1 && x0>=20 && x0<=104 &&
               (x0-20)%14==0 && (y0==22 || y0==28 || y0==34))) {
        ++c->guides;
    } else if((x0==0 && x1==127 && y0==y1 && (y0==13 || y0==54)) ||
              ((x0==45 || x0==82) && x0==x1 && y0==56 && y1==63)) {
        ++c->other_lines;
    } else {
        assert(x0>=(int32_t)LABMATE_SCOPE_PLOT_X_LEFT &&
               x1<=(int32_t)LABMATE_SCOPE_PLOT_X_RIGHT &&
               (y0==LABMATE_SCOPE_PLOT_Y_HIGH ||
                y0==LABMATE_SCOPE_PLOT_Y_LOW) &&
               (y1==LABMATE_SCOPE_PLOT_Y_HIGH ||
                y1==LABMATE_SCOPE_PLOT_Y_LOW));
        ++c->wave;
    }
}
int main(void) {
    struct Canvas c={0};
    LabMateScopeDisplay d={
        .state=LabMateScopeDisplayStopped,
        .plot={.result=LabMateScopePlotNoEdges}
    };
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.frames==4 && c.guides==10 && c.wave==0);
    assert(c.run && c.page && c.exit && c.ready);
    c=(struct Canvas){0};
    d.state=LabMateScopeDisplayNoTrigger;
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.no_signal && c.wave==0 && c.guides==10);

    LabMateScopeEdge events[]={
        {.tick=100,.high=true},
        {.tick=200,.delta_ticks=100,.high=false}
    };
    LabMateScopePlotLine segments[2];
    d.plot=labmate_scope_plot_project(events,2,false,segments,2);
    d.lines=segments;
    d.total_edges=2U;
    d.state=LabMateScopeDisplayRunning;
    c=(struct Canvas){0};
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.frames==4 && c.guides==31 && c.wave==2);
    assert(c.stop && !c.page && c.exit);
    LabMateScopeMetrics valid={
        .status=LabMateScopeMetricsReady, .completed_cycles=2,
        .timebase_hz=64000000, .frequency_millihz=100000,
        .duty_permille=500
    };
    d.completed=&valid;
    c=(struct Canvas){0};
    assert(labmate_scope_display_draw(&c,&d));
    assert(!c.frequency && !c.duty); /* no metrics while capture is active */

    d.state=LabMateScopeDisplayStopped;
    c=(struct Canvas){0};
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.frequency && c.duty && c.wave==2 && c.run && c.page);
    valid.truncated=true;
    c=(struct Canvas){0};
    assert(labmate_scope_display_draw(&c,&d));
    assert(!c.frequency && !c.duty);
    valid.truncated=false;

    d.state=LabMateScopeDisplayBusy;
    c=(struct Canvas){0};
    assert(labmate_scope_display_draw(&c,&d));
    assert(c.busy && c.wave==0);
    d.state=LabMateScopeDisplayRunning;
    segments[0].x0=255U;
    c=(struct Canvas){0};
    assert(!labmate_scope_display_draw(&c,&d) && c.texts==0 && c.frames==0);
    segments[0].x0=LABMATE_SCOPE_PLOT_X_LEFT;
    d.total_edges=LABMATE_SCOPE_MAX_EDGES+1U;
    assert(!labmate_scope_display_draw(&c,&d) && c.texts==0);
    d.total_edges=2U;
    d.plot.line_count=1U;
    assert(!labmate_scope_display_draw(&c,&d) && c.texts==0);
    d.plot.line_count=2U;
    d.plot.visible_edges=0U;
    assert(!labmate_scope_display_draw(&c,&d) && c.texts==0);
    assert(!labmate_scope_display_draw(NULL,&d));
    assert(!labmate_scope_display_draw(&c,NULL));
    puts("v1.9 scope frame, graticule, HOLD-only metrics, paren-footer, font bounds PASS");
    return 0;
}
