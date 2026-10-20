#include "labmate_scope_pair_view.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {int32_t x0,y0,x1,y1;} Rect;
struct Canvas {
    Font font;
    Rect labels[32];
    unsigned label_count, stroke_count;
    bool saw_a, saw_b, saw_freq_diff, saw_duty_diff, saw_high,
         saw_low, saw_period, saw_unsaved, saw_save_hint,
         saw_ref_hint, saw_partial;
};
void canvas_set_font(Canvas* c,Font f) {
    assert(c && (f==FontPrimary || f==FontSecondary));
    c->font=f;
}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* s) {
    assert(c && s && x>=0 && y>=0 && y<64);
    const size_t n=strlen(s);
    const int32_t width=(int32_t)n*(c->font==FontPrimary ? 8 : 6);
    const int32_t h=c->font==FontPrimary ? 11 : 8;
    assert(n>0 && x+width<=128 && y-h+1>=0);
    assert(c->label_count < 32U);
    const Rect next={x,y-h+1,x+width-1,y};
    for(unsigned i=0;i<c->label_count;++i) {
        const Rect prev=c->labels[i];
        assert(next.x1<prev.x0 || next.x0>prev.x1 ||
               next.y1<prev.y0 || next.y0>prev.y1);
    }
    c->labels[c->label_count++]=next;
    if(s[0]=='A' && (s[1]=='\0' || s[1]=='*')) c->saw_a=true;
    if(s[0]=='B' && (s[1]=='\0' || s[1]=='*')) c->saw_b=true;
    if(strstr(s,"F change")) c->saw_freq_diff=true;
    if(strstr(s,"D change")) c->saw_duty_diff=true;
    if(!strcmp(s,"HIGH")) c->saw_high=true;
    if(!strcmp(s,"LOW")) c->saw_low=true;
    if(!strcmp(s,"PERIOD")) c->saw_period=true;
    if(strstr(s,"NOT SAVED")) c->saw_unsaved=true;
    if(strstr(s,"save A") || strstr(s,"Capture B")) c->saw_save_hint=true;
    if(strstr(s,"v PAGE")) c->saw_ref_hint=true;
    if(s[0]=='A' && s[1]=='*') c->saw_partial=true;
}
void canvas_draw_line(Canvas* c,int32_t x0,int32_t y0,int32_t x1,int32_t y1) {
    assert(c && x0>=0 && x1>=0 && x0<128 && x1<128 &&
           y0>=0 && y1>=0 && y0<64 && y1<64);
    ++c->stroke_count;
}
static LabMateScopeMetrics measure(uint64_t freq,uint16_t duty,
                                   uint64_t high,uint64_t low) {
    return (LabMateScopeMetrics){
        .status=LabMateScopeMetricsReady,.completed_cycles=2U,
        .edge_count=5U,.timebase_hz=64000000U,
        .frequency_millihz=freq,.duty_permille=duty,
        .total_high_ticks=high,.total_low_ticks=low,
        .min_period_ticks=100,.max_period_ticks=100
    };
}
int main(void) {
    struct Canvas c={0};
    LabMateScopePair p={0};
    assert(labmate_scope_pair_view_draw(&c,&p,false,0U));
    assert(c.saw_a && c.saw_b && c.saw_save_hint && c.saw_ref_hint);
    assert(!c.saw_freq_diff);
    c=(struct Canvas){0};
    assert(labmate_scope_pair_view_draw(&c,&p,false,1U));
    assert(c.saw_unsaved); /* renderer safe if invoked outside guarded navigation */
    c=(struct Canvas){0};
    const LabMateScopeMetrics a=measure(100000U,500U,640000U,640000U);
    assert(labmate_scope_pair_save_a(&p,&a,1U));
    assert(labmate_scope_pair_view_draw(&c,&p,false,0U));
    assert(c.saw_a && c.saw_b && !c.saw_freq_diff && c.saw_ref_hint);
    c=(struct Canvas){0};
    const LabMateScopeMetrics b=measure(1000000U,250U,32000U,96000U);
    assert(labmate_scope_pair_save_b(&p,&b,2U));
    assert(labmate_scope_pair_view_draw(&c,&p,true,0U));
    assert(c.saw_a && c.saw_b && c.saw_freq_diff && c.saw_duty_diff);
    c=(struct Canvas){0};
    assert(labmate_scope_pair_view_draw(&c,&p,true,1U));
    assert(c.saw_high && c.saw_low && c.saw_period);
    c=(struct Canvas){0};
    assert(labmate_scope_pair_view_draw(&c,&p,true,2U));
    assert(c.saw_high && c.saw_low && c.saw_period);
    c=(struct Canvas){0};
    p.a.truncated=true;
    p.b.truncated=true;
    assert(labmate_scope_pair_view_draw(&c,&p,true,0U));
    assert(c.saw_partial && c.saw_freq_diff);
    c=(struct Canvas){0};
    assert(!labmate_scope_pair_view_draw(&c,&p,false,3U));
    assert(c.label_count==0U && c.stroke_count==0U);
    p.has_a=false;
    assert(!labmate_scope_pair_view_draw(&c,&p,false,0U));
    assert(c.label_count==0U);
    assert(!labmate_scope_pair_view_draw(NULL,&p,false,0U));
    puts("v1.9 A/B compact readings, timings, font bounds and no-overlap PASS");
    return 0;
}
