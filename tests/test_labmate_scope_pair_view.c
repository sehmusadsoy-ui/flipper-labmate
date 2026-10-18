#include "labmate_scope_pair_view.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

struct Canvas {
    unsigned labels;
    unsigned lines;
    bool saw_a;
    bool saw_b;
    bool saw_delta;
    bool saw_need;
};
void canvas_set_font(Canvas* c, Font f) { assert(c && f==FontSecondary); }
void canvas_draw_str(Canvas* c, int32_t x, int32_t y, const char* s) {
    assert(c && s && x>=0 && y>=0 && y<64);
    assert((size_t)x+strlen(s)*6U <= 128U); /* Flipper secondary glyph cell */
    ++c->labels;
    if(s[0]=='A' && s[1]==' ') c->saw_a=true;
    if(s[0]=='B' && s[1]==' ') c->saw_b=true;
    if(!strncmp(s,"dF ",3)) c->saw_delta=true;
    if(strstr(s,"NEED")) c->saw_need=true;
}
void canvas_draw_line(Canvas* c, int32_t x0,int32_t y0,int32_t x1,int32_t y1) {
    assert(c && x0>=0 && x1<128 && y0>=0 && y1<64);
    ++c->lines;
}
static LabMateScopeMetrics measure(uint64_t f,uint16_t d) {
    return (LabMateScopeMetrics){
        .status=LabMateScopeMetricsReady,.completed_cycles=2,
        .edge_count=5,.timebase_hz=64000000U,
        .frequency_millihz=f,.duty_permille=d,
        .min_period_ticks=100U,.max_period_ticks=100U
    };
}
int main(void) {
    struct Canvas c={0};
    LabMateScopePair p={0};
    assert(labmate_scope_pair_view_draw(&c,&p,false));
    assert(c.saw_need && !c.saw_delta);
    c=(struct Canvas){0};
    LabMateScopeMetrics a=measure(100000U,500U);
    assert(labmate_scope_pair_save_a(&p,&a,1U));
    assert(labmate_scope_pair_view_draw(&c,&p,false));
    assert(c.saw_a && !c.saw_b);
    c=(struct Canvas){0};
    LabMateScopeMetrics b=measure(1000000U,250U);
    assert(labmate_scope_pair_save_b(&p,&b,2U));
    assert(labmate_scope_pair_view_draw(&c,&p,true));
    assert(c.saw_a && c.saw_b && c.saw_delta);
    c=(struct Canvas){0};
    p.a.frequency_millihz=UINT64_C(32000000000);
    p.b.frequency_millihz=UINT64_C(31900000000);
    p.b.duty_permille=1000U;
    p.delta=labmate_scope_compare_metrics(&p.a,&p.b);
    assert(labmate_scope_pair_view_draw(&c,&p,true)); /* large MHz, 100% duty */
    c=(struct Canvas){0};
    p.has_a=false;
    assert(!labmate_scope_pair_view_draw(&c,&p,false));
    assert(c.labels==0 && c.lines==0);
    assert(!labmate_scope_pair_view_draw(NULL,&p,false));
    puts("v1.9 A/B display bounds and truthful missing reference PASS");
    return 0;
}
