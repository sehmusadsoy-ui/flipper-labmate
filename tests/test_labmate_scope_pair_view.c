#include "labmate_scope_pair_view.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

struct Canvas {
    unsigned labels;
    unsigned lines;
    bool saw_a;
    bool saw_b;
    bool saw_delta_freq;
    bool saw_delta_duty;
    bool saw_high;
    bool saw_low;
    bool saw_period;
    bool saw_need;
    bool saw_details;
    bool saw_help;
    bool saw_partial;
};
void canvas_set_font(Canvas* c, Font f) {assert(c && f == FontSecondary);}
void canvas_draw_str(Canvas* c, int32_t x, int32_t y, const char* s) {
    assert(c && s && x >= 0 && x < 128 && y >= 0 && y < 64);
    assert((size_t)x + strlen(s)*6U <= 128U);
    ++c->labels;
    if(s[0]=='A' && (s[1]==':' || s[1]=='*')) c->saw_a=true;
    if(s[0]=='B' && (s[1]==':' || s[1]=='*') && !strstr(s,"NOT SAVED")) c->saw_b=true;
    if(!strncmp(s,"F DIFF ",7)) c->saw_delta_freq=true;
    if(!strncmp(s,"D DIFF ",7)) c->saw_delta_duty=true;
    if(!strncmp(s,"HIGH ",5)) c->saw_high=true;
    if(!strncmp(s,"LOW ",4)) c->saw_low=true;
    if(!strncmp(s,"PERIOD ",7)) c->saw_period=true;
    if(strstr(s,"NOT SAVED") || strstr(s,"RUN, THEN STOP")) c->saw_need=true;
    if(strstr(s,"DETAILS")) c->saw_details=true;
    if(strstr(s,"UP:MORE") || strstr(s,"UP:NEXT")) c->saw_help=true;
    if(strstr(s,"*PARTIAL")) c->saw_partial=true;
}
void canvas_draw_line(Canvas* c, int32_t x0,int32_t y0,int32_t x1,int32_t y1) {
    assert(c && x0>=0 && x1<128 && y0>=0 && y1<64);
    ++c->lines;
}
static LabMateScopeMetrics measure(uint64_t f,uint16_t d, uint64_t high, uint64_t low) {
    return (LabMateScopeMetrics){
        .status=LabMateScopeMetricsReady,.completed_cycles=2,
        .edge_count=5,.timebase_hz=64000000U,
        .frequency_millihz=f,.duty_permille=d,
        .total_high_ticks=high,.total_low_ticks=low,
        .min_period_ticks=100U,.max_period_ticks=100U
    };
}
int main(void) {
    struct Canvas c={0};
    LabMateScopePair p={0};
    assert(labmate_scope_pair_view_draw(&c,&p,false,0));
    assert(c.saw_need && c.saw_help && !c.saw_delta_freq);
    c=(struct Canvas){0};
    LabMateScopeMetrics a=measure(100000U,500U,640000U,640000U);
    assert(labmate_scope_pair_save_a(&p,&a,1U));
    assert(labmate_scope_pair_view_draw(&c,&p,false,0));
    assert(c.saw_a && c.saw_need && !c.saw_b);
    c=(struct Canvas){0};
    LabMateScopeMetrics b=measure(1000000U,250U,32000U,96000U);
    assert(labmate_scope_pair_save_b(&p,&b,2U));
    assert(labmate_scope_pair_view_draw(&c,&p,true,0));
    assert(c.saw_a && c.saw_b && c.saw_delta_freq && c.saw_delta_duty);
    c=(struct Canvas){0};
    assert(labmate_scope_pair_view_draw(&c,&p,true,1));
    assert(c.saw_details && c.saw_high && c.saw_low && c.saw_period);
    c=(struct Canvas){0};
    assert(labmate_scope_pair_view_draw(&c,&p,true,2));
    assert(c.saw_details && c.saw_high && c.saw_low && c.saw_period);
    c=(struct Canvas){0};
    p.a.frequency_millihz=UINT64_C(32000000000);
    p.b.frequency_millihz=UINT64_C(31900000000);
    p.b.duty_permille=1000U;
    p.delta=labmate_scope_compare_metrics(&p.a,&p.b);
    assert(labmate_scope_pair_view_draw(&c,&p,true,0));
    c=(struct Canvas){0};
    p.a.truncated = true; p.b.truncated = true;
    assert(labmate_scope_pair_view_draw(&c,&p,true,0));
    assert(c.saw_partial && c.saw_a && c.saw_b && c.saw_delta_freq);
    c=(struct Canvas){0};
    assert(labmate_scope_pair_view_draw(&c,&p,true,1));
    assert(c.saw_details && c.saw_high);
    c=(struct Canvas){0};
    assert(!labmate_scope_pair_view_draw(&c,&p,false,3));
    assert(c.labels==0 && c.lines==0);
    p.has_a=false;
    assert(!labmate_scope_pair_view_draw(&c,&p,false,0));
    assert(c.labels==0 && c.lines==0);
    assert(!labmate_scope_pair_view_draw(NULL,&p,false,0));
    puts("v1.9 A/B readable summary, timing pages, text bounds and safe invalid PASS");
    return 0;
}
