/* Step 4 E11 Compare / Sample A-B source-linked 128x64 review.
 * Links REAL pair-save, metrics, compare and renderer C; Canvas/UI chrome
 * are host-only bounded mocks. NO device, IRQ, HAL, or filesystem writes.
 */
#include "labmate_scope_pair_view.h"
#include "ui_kit.h"
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
struct Canvas {
    Font font; Color ink;
    unsigned faults,paint,texts,frames,empty_wave,cue,pages;
    uint8_t page_index;
    char title[16];
    char lines[24][32];
    int16_t x[24], y[24];
};
void canvas_set_font(Canvas* c,Font f){c->font=f;}
uint16_t canvas_string_width(Canvas* c,const char* s){
    return (uint16_t)(strlen(s)*(c->font==FontPrimary?8U:6U));
}
void canvas_set_color(Canvas* c,Color cl){c->ink=cl;}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* s){
    int w=canvas_string_width(c,s);
    int h=c->font==FontPrimary?10:8;
    if(w<=0||x<0||x+w>128||y<0||y>=64||y-h+1<0)c->faults++;
    if(c->texts<24U){
        snprintf(c->lines[c->texts],sizeof(c->lines[0]),"%s",s);
        c->x[c->texts]=(int16_t)x;c->y[c->texts]=(int16_t)y;
    } else c->faults++;
    c->texts++;c->paint++;
}
void canvas_draw_rframe(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t radius) {
    (void)radius;
    if(w<=0||h<=0||x<0||y<0||x+w>128||y+h>64)c->faults++;
    c->frames++;c->paint++;
}
bool ui_kit_pixel_header(Canvas* c,const char* title,bool chip,
                         UiKitInstrumentState state,bool pulse) {
    (void)state;(void)pulse;
    if(!title||chip)return false;
    canvas_set_font(c,FontPrimary);
    if(9U+canvas_string_width(c,title)>127U)return false;
    snprintf(c->title,sizeof(c->title),"%s",title);
    c->paint++;return true;
}
bool ui_kit_scope_page_dots(Canvas* c,uint8_t i) {
    if(i>=4U)return false;
    c->pages++;c->page_index=i;c->paint++;return true;
}
bool ui_kit_pulse_line_dotted(Canvas* c,uint8_t x,uint8_t y,uint8_t w) {
    if(x+w>=128||y>=64)return false;
    c->empty_wave++;c->paint++;return true;
}
void ui_kit_next_cue(Canvas* c){c->cue++;c->paint++;}
static bool has(const Canvas* c,const char* text){
    for(unsigned j=0;j<c->texts&&j<24U;j++)
        if(!strcmp(c->lines[j],text))return true;
    return false;
}
static bool begins(const Canvas* c,const char* start) {
    for(unsigned j=0;j<c->texts&&j<24U;j++)
        if(!strncmp(c->lines[j],start,strlen(start)))return true;
    return false;
}
static Canvas fresh(void){Canvas c={0};c.ink=ColorBlack;return c;}
static void good(const Canvas* c) {
    assert(c->faults==0U&&c->ink==ColorBlack&&c->pages==1U&&c->cue==1U);
}
static LabMateScopeMetrics capture(uint32_t high,uint32_t low) {
    const LabMateScopeEdge e[]={
        {.tick=100U,.high=true},
        {.tick=100U+high,.delta_ticks=high,.high=false},
        {.tick=100U+high+low,.delta_ticks=low,.high=true},
        {.tick=100U+2U*high+low,.delta_ticks=high,.high=false},
        {.tick=100U+2U*(high+low),.delta_ticks=low,.high=true}
    };
    LabMateScopeMetrics m=labmate_scope_metrics_from_edges(e,5U,1000000U);
    assert(m.status==LabMateScopeMetricsReady && m.completed_cycles==2U);
    return m;
}
int main(void){
    LabMateScopePair p={0};
    Canvas c=fresh();
    assert(labmate_scope_pair_view_draw(&c,&p,false,0U));good(&c);
    assert(!strcmp(c.title,"Compare")&&c.page_index==1U&&c.frames==2U);
    assert(has(&c,"Pin PC1")&&has(&c,"A")&&has(&c,"B"));
    assert(has(&c,"Empty")&&has(&c,"Capture then save"));
    assert(!begins(&c,"dF")&&!begins(&c,"Frequency")&&c.empty_wave==0U);
    c=fresh();
    assert(labmate_scope_pair_view_draw(&c,&p,true,0U));good(&c);
    assert(has(&c,"LEFT saves A"));
    c=fresh();
    assert(labmate_scope_pair_view_draw(&c,&p,false,1U));good(&c);
    assert(!strcmp(c.title,"Sample A")&&c.page_index==2U&&c.empty_wave==1U);
    assert(has(&c,"No sample A")&&has(&c,"Capture then save"));
    c=fresh();
    assert(labmate_scope_pair_view_draw(&c,&p,false,2U));good(&c);
    assert(has(&c,"No sample B")&&c.empty_wave==1U);
    const LabMateScopeMetrics a=capture(5000U,5000U);/* 100Hz, 50%, 5ms */
    assert(labmate_scope_pair_save_a(&p,&a,1U));
    assert(p.has_a&&!p.has_b);
    c=fresh();
    assert(labmate_scope_pair_view_draw(&c,&p,false,0U));good(&c);
    assert(has(&c,"100.00Hz")&&has(&c,"Capture new B")&&has(&c,"Empty"));
    assert(!begins(&c,"dF"));
    c=fresh();
    assert(labmate_scope_pair_view_draw(&c,&p,false,1U));good(&c);
    assert(!strcmp(c.title,"Sample A")&&c.empty_wave==0U&&c.frames==0U);
    assert(has(&c,"Frequency")&&has(&c,"100.00Hz")&&has(&c,"Duty"));
    assert(has(&c,"50.0%")&&has(&c,"High")&&has(&c,"Low"));
    assert(has(&c,"5.00ms")&&!has(&c,"PERIOD"));
    const LabMateScopeMetrics b=capture(500U,500U);/* 1kHz, 50%, 500us */
    assert(!labmate_scope_pair_save_b(&p,&b,1U));
    assert(p.notice==LabMateScopePairNeedFreshB&&!p.has_b);
    assert(labmate_scope_pair_save_b(&p,&b,2U));
    assert(p.has_a&&p.has_b&&p.delta.comparable);
    assert(p.delta.frequency_delta_millihz==900000LL);
    assert(p.delta.duty_delta_permille==0);
    LabMateScopePair copy=p;
    c=fresh();
    assert(labmate_scope_pair_view_draw(&c,&p,true,0U));good(&c);
    assert(!memcmp(&p,&copy,sizeof(p)));
    assert(has(&c,"100.00Hz")&&has(&c,"1.00kHz"));
    assert(has(&c,"Frequency")&&has(&c,"+900.00Hz"));
    assert(!has(&c,"+900.00%")&&c.empty_wave==0U);
    c=fresh();
    assert(labmate_scope_pair_view_draw(&c,&p,true,2U));good(&c);
    assert(!strcmp(c.title,"Sample B")&&has(&c,"1.00kHz")&&has(&c,"500us"));
    assert(c.empty_wave==0U);
    /* Negative B-A follows real metrics; never relabel as percent. */
    LabMateScopePair neg={0};
    assert(labmate_scope_pair_save_a(&neg,&b,1U));
    assert(labmate_scope_pair_save_b(&neg,&a,2U));
    c=fresh();
    assert(labmate_scope_pair_view_draw(&c,&neg,false,0U));good(&c);
    assert(has(&c,"-900.00Hz"));
    /* Corrupt or incomplete captures must not become plausible samples. */
    p.a.truncated=true;
    c=fresh();
    assert(!labmate_scope_pair_view_draw(&c,&p,false,0U));
    assert(c.paint==0U);
    p.a.truncated=false;
    p.generation_b=p.generation_a;
    c=fresh();
    assert(!labmate_scope_pair_view_draw(&c,&p,false,0U));
    assert(c.paint==0U);
    p.generation_b=2U;p.has_a=false;
    c=fresh();
    assert(!labmate_scope_pair_view_draw(&c,&p,false,0U));
    assert(c.paint==0U);
    c=fresh();
    assert(!labmate_scope_pair_view_draw(&c,&p,false,3U));
    assert(c.paint==0U);
    assert(!labmate_scope_pair_view_draw(NULL,&p,false,0U));
    puts("E11 COMPARE/SAMPLE STEP4 SOURCE-LINKED HOST PASS: empty/A/B/delta/invalid");
    return 0;
}
