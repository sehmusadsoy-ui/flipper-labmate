#include "labmate_scope_pair_view.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {int32_t x0,y0,x1,y1;} Rect;
struct Canvas {
    Font font;
    Rect labels[32];
    unsigned count, strokes;
    bool saw_a, saw_b, saw_df, saw_dd, saw_high, saw_low, saw_period;
    bool saw_empty, saw_details, saw_page, saw_exit, saw_100hz, saw_5ms;
};
void canvas_set_font(Canvas* c,Font f) {
    assert(c && (f==FontPrimary || f==FontSecondary));
    c->font=f;
}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* s) {
    assert(c && s && x>=0 && y>=0 && y<64);
    const size_t n=strlen(s);
    const int32_t w=(int32_t)n*(c->font==FontPrimary?8:6);
    const int32_t h=c->font==FontPrimary?11:8;
    assert(n>0U && x+w<=128 && y-h+1>=0 && c->count<32U);
    const Rect new_rect={x,y-h+1,x+w-1,y};
    for(unsigned i=0;i<c->count;++i) {
        const Rect p=c->labels[i];
        assert(new_rect.x1<p.x0 || new_rect.x0>p.x1 ||
               new_rect.y1<p.y0 || new_rect.y0>p.y1);
    }
    c->labels[c->count++]=new_rect;
    if(!strcmp(s,"A") || !strcmp(s,"A*")) c->saw_a=true;
    if(!strcmp(s,"B") || !strcmp(s,"B*")) c->saw_b=true;
    if(!strcmp(s,"dF")) c->saw_df=true;
    if(!strcmp(s,"dD")) c->saw_dd=true;
    if(!strcmp(s,"HIGH")) c->saw_high=true;
    if(!strcmp(s,"LOW")) c->saw_low=true;
    if(!strcmp(s,"PERIOD")) c->saw_period=true;
    if(!strcmp(s,"No saved samples") || !strcmp(s,"No sample A"))
        c->saw_empty=true;
    if(!strcmp(s,"A DETAIL") || !strcmp(s,"B DETAIL")) c->saw_details=true;
    if(!strcmp(s,"(v)Pg")) c->saw_page=true;
    if(!strcmp(s,"(B)Exit")) c->saw_exit=true;
    if(!strcmp(s,"100.00Hz")) c->saw_100hz=true;
    if(!strcmp(s,"5.00ms")) c->saw_5ms=true;
}
void canvas_draw_line(Canvas* c,int32_t x0,int32_t y0,int32_t x1,int32_t y1) {
    assert(c && x0>=0 && x0<128 && x1>=0 && x1<128 &&
           y0>=0 && y0<64 && y1>=0 && y1<64);
    ++c->strokes;
}
static LabMateScopeMetrics measurement(uint64_t f,uint16_t duty,uint64_t h,uint64_t l) {
    return (LabMateScopeMetrics){
        .status=LabMateScopeMetricsReady, .completed_cycles=2U,
        .edge_count=5U,.timebase_hz=64000000U,
        .frequency_millihz=f,.duty_permille=duty,
        .total_high_ticks=h,.total_low_ticks=l,
        .min_period_ticks=100,.max_period_ticks=100
    };
}
int main(void) {
    struct Canvas c={0};
    LabMateScopePair p={0};
    assert(labmate_scope_pair_view_draw(&c,&p,false,0U));
    assert(c.saw_empty && c.saw_page && c.saw_exit);
    assert(!c.saw_df && !c.saw_high);
    c=(struct Canvas){0};
    assert(labmate_scope_pair_view_draw(&c,&p,false,1U));
    assert(c.saw_empty && c.saw_details);

    const LabMateScopeMetrics a=measurement(100000U,500U,640000U,640000U);
    assert(labmate_scope_pair_save_a(&p,&a,1U));
    c=(struct Canvas){0};
    assert(labmate_scope_pair_view_draw(&c,&p,false,0U));
    assert(c.saw_a && c.saw_100hz && !c.saw_df);

    const LabMateScopeMetrics b=measurement(1000000U,250U,32000U,96000U);
    assert(labmate_scope_pair_save_b(&p,&b,2U));
    c=(struct Canvas){0};
    assert(labmate_scope_pair_view_draw(&c,&p,true,0U));
    assert(c.saw_a && c.saw_b && c.saw_df && c.saw_dd);
    c=(struct Canvas){0};
    assert(labmate_scope_pair_view_draw(&c,&p,true,1U));
    assert(c.saw_details && c.saw_high && c.saw_low &&
           c.saw_period && c.saw_100hz && c.saw_5ms);
    c=(struct Canvas){0};
    assert(labmate_scope_pair_view_draw(&c,&p,true,2U));
    assert(c.saw_details && c.saw_high && c.saw_low && c.saw_period);

    p.a.truncated=true;
    p.b.truncated=true;
    c=(struct Canvas){0};
    assert(labmate_scope_pair_view_draw(&c,&p,true,0U));
    assert(c.saw_a && c.saw_df);
    c=(struct Canvas){0};
    assert(!labmate_scope_pair_view_draw(&c,&p,true,3U));
    assert(c.count==0 && c.strokes==0);
    p.has_a=false;
    assert(!labmate_scope_pair_view_draw(&c,&p,true,0U));
    assert(c.count==0 && c.strokes==0);
    assert(!labmate_scope_pair_view_draw(NULL,&p,true,0U));
    puts("v1.9 A/B + details professional alignment, true metrics, paren keys PASS");
    return 0;
}
