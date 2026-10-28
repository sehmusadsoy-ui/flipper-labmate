/* Step 3 source-linked Scope + Reference host renderer acceptance.
 * Actual production display.c/reference_view.c, real plot+metrics+tolerance;
 * only Canvas and ui_kit chrome are bounded host mocks. NO GPIO/HAL/USB.
 */
#include "labmate_scope_display.h"
#include "labmate_scope_reference_view.h"
#include "ui_kit.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

struct Canvas {
    Font font; Color ink;
    unsigned faults, paint, texts, wave_lines, frames, dots;
    unsigned chip_count, page_count, key_count, placeholder_count;
    UiKitInstrumentState chip;
    uint8_t active_page;
    char title[16];
    char shown[30][32];
    struct {UiKitKey key;uint8_t x;char label[12];} keys[3];
};
static Canvas fresh(void) {
    Canvas c={0};c.ink=ColorBlack;return c;
}
void canvas_set_font(Canvas* c,Font f){c->font=f;}
uint16_t canvas_string_width(Canvas* c,const char* s) {
    return (uint16_t)(strlen(s)*(c->font==FontPrimary?8U:6U));
}
void canvas_set_color(Canvas* c,Color x){c->ink=x;}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* text){
    int32_t w=canvas_string_width(c,text);
    int32_t h=c->font==FontPrimary?11:8;
    if(!w||x<0||x+w>128||y<0||y>=64||y-h+1<0)c->faults++;
    if(c->texts<30U)snprintf(c->shown[c->texts],32,"%s",text);
    else c->faults++;
    c->texts++;c->paint++;
}
void canvas_draw_line(Canvas* c,int32_t x,int32_t y,int32_t xx,int32_t yy){
    if(x<0||xx<0||x>=128||xx>=128||y<0||yy<0||y>=64||yy>=64)c->faults++;
    if((y==27||y==42)&&(yy==27||yy==42))c->wave_lines++;
    c->paint++;
}
void canvas_draw_dot(Canvas* c,int32_t x,int32_t y){
    if(x<0||x>=128||y<0||y>=64)c->faults++;
    c->dots++;c->paint++;
}
void canvas_draw_box(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h){
    if(w<=0||h<=0||x<0||y<0||x+w>128||y+h>64)c->faults++;
    c->paint++;
}
void canvas_draw_rframe(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t radius){
    (void)radius;
    if(w<=0||h<=0||x<0||y<0||x+w>128||y+h>64)c->faults++;
    c->frames++;c->paint++;
}
uint8_t ui_kit_state_chip_width(Canvas* c,UiKitInstrumentState st){
    const char* names[]={"Ready","Live","Held","Stopped","Busy",
                         "Error","Waiting","Match","Off"};
    if((unsigned)st>=sizeof(names)/sizeof(names[0]))return 0U;
    canvas_set_font(c,FontSecondary);
    return (uint8_t)(canvas_string_width(c,names[st])+17U);
}
bool ui_kit_state_chip_compact(Canvas* c,UiKitInstrumentState st,bool pulse){
    (void)pulse;
    uint8_t w=ui_kit_state_chip_width(c,st);
    if(!w)return false;
    c->chip_count++;c->chip=st;
    canvas_draw_rframe(c,127-w,0,w,11,3);
    return true;
}
bool ui_kit_pixel_header(Canvas* c,const char* title,bool with_chip,
                         UiKitInstrumentState state,bool pulse){
    if(!c||!title)return false;
    c->font=FontPrimary;
    unsigned w=canvas_string_width(c,title);
    if(with_chip&&9U+w+2U>127U-ui_kit_state_chip_width(c,state))return false;
    snprintf(c->title,sizeof(c->title),"%s",title);
    canvas_draw_line(c,5,2,2,5);canvas_draw_line(c,2,5,5,8);
    canvas_set_font(c,FontPrimary);canvas_draw_str(c,9,9,title);
    if(with_chip)ui_kit_state_chip_compact(c,state,pulse);
    return true;
}
bool ui_kit_scope_page_dots(Canvas* c,uint8_t index){
    if(index>3U)return false;
    c->active_page=index;c->page_count++;
    for(uint8_t n=0;n<4;n++) {
        int32_t x=100+7*n;
        if(n==index)canvas_draw_dot(c,x,16);
        else canvas_draw_box(c,x-1,15,2,2);
    }
    return true;
}
bool ui_kit_pulse_line_dotted(Canvas* c,uint8_t x,uint8_t y,uint8_t w){
    if(x+w>=128||y>=64)return false;
    c->placeholder_count++;canvas_draw_dot(c,x,y);canvas_draw_dot(c,x+w,y);
    return true;
}
uint8_t ui_kit_key_hint_compact(Canvas* c,uint8_t x,UiKitKey key,const char* s){
    unsigned size=key==UiKitKeyOk?19U:16U;
    unsigned end=x+size+3U+strlen(s)*6U;
    if(end>127U)c->faults++;
    unsigned n=c->key_count++;
    if(n>=3U){c->faults++;return 0U;}
    c->keys[n].key=key;c->keys[n].x=x;
    snprintf(c->keys[n].label,sizeof(c->keys[n].label),"%s",s);
    c->paint++;
    return (uint8_t)end;
}
static bool has(const Canvas* c,const char* s){
    for(unsigned i=0;i<c->texts && i<30;i++)
        if(!strcmp(c->shown[i],s))return true;
    return false;
}
static bool key(const Canvas* c,UiKitKey k,const char* s){
    for(unsigned i=0;i<c->key_count&&i<3;i++)
        if(c->keys[i].key==k&&!strcmp(c->keys[i].label,s))return true;
    return false;
}
static void good(Canvas* c){assert(c->faults==0U&&c->ink==ColorBlack);}
static LabMateScopeMetrics complete_metrics(void){
    const LabMateScopeEdge edges[]={
        {.tick=100U,.high=true},
        {.tick=600U,.delta_ticks=500U,.high=false},
        {.tick=1100U,.delta_ticks=500U,.high=true},
        {.tick=1600U,.delta_ticks=500U,.high=false},
        {.tick=2100U,.delta_ticks=500U,.high=true},
    };
    LabMateScopeMetrics m=labmate_scope_metrics_from_edges(edges,5U,1000000U);
    assert(m.status==LabMateScopeMetricsReady&&m.completed_cycles>0U);
    return m;
}
static void test_scope(void) {
    Canvas c=fresh();
    LabMateScopeDisplay d={.state=LabMateScopeDisplayStopped,
                           .plot={.result=LabMateScopePlotNoEdges}};
    assert(labmate_scope_display_draw(&c,&d));good(&c);
    assert(c.chip==UiKitInstrumentReady && c.page_count==1U &&
           c.active_page==0U && c.placeholder_count==1U);
    assert(has(&c,"Scope")&&has(&c,"Pin PC1")&&has(&c,"Press OK to run"));
    assert(key(&c,UiKitKeyOk,"Run")&&key(&c,UiKitKeyDown,"Next"));
    const LabMateScopeEdge e[]={
        {.tick=100U,.high=true},
        {.tick=200U,.delta_ticks=100U,.high=false}
    };
    LabMateScopePlotLine lines[2];
    d.plot=labmate_scope_plot_project(e,2U,false,lines,2U);
    d.lines=lines;d.total_edges=2U;d.state=LabMateScopeDisplayRunning;
    c=fresh();assert(labmate_scope_display_draw(&c,&d));good(&c);
    assert(c.chip==UiKitInstrumentLive&&c.wave_lines==2U);
    assert(key(&c,UiKitKeyOk,"Stop")&&!key(&c,UiKitKeyDown,"Next"));
    assert(!has(&c,"1.00kHz")&&!has(&c,"50.0%"));
    LabMateScopeMetrics m=complete_metrics();
    d.completed=&m;d.state=LabMateScopeDisplayStopped;
    c=fresh();assert(labmate_scope_display_draw(&c,&d));good(&c);
    assert(c.chip==UiKitInstrumentHeld&&has(&c,"1.00kHz")&&has(&c,"50.0%"));
    assert(key(&c,UiKitKeyDown,"Next"));
    d.completed=NULL;
    d.state=LabMateScopeDisplayBusy;
    c=fresh();assert(labmate_scope_display_draw(&c,&d));good(&c);
    assert(c.chip==UiKitInstrumentBusy&&c.wave_lines==0U);
    assert(has(&c,"PC1 busy")&&!has(&c,"1.00kHz"));
    d.state=LabMateScopeDisplayNoTrigger;
    d.plot.result=LabMateScopePlotNoEdges;
    d.plot.line_count=0U;d.plot.visible_edges=0U;d.total_edges=0U;
    c=fresh();assert(labmate_scope_display_draw(&c,&d));good(&c);
    assert(c.chip==UiKitInstrumentWaiting&&has(&c,"No signal"));
    d.state=LabMateScopeDisplayError;
    c=fresh();assert(labmate_scope_display_draw(&c,&d));good(&c);
    assert(c.chip==UiKitInstrumentError&&!has(&c,"1.00kHz"));
    d.state=LabMateScopeDisplayRunning;d.plot.result=LabMateScopePlotReady;
    d.plot.visible_edges=2U;d.plot.line_count=2U;d.lines=lines;d.total_edges=2U;
    lines[0].x0=255U;c=fresh();
    assert(!labmate_scope_display_draw(&c,&d)&&c.paint==0U);
}
static void test_reference(void) {
    LabMateScopeMetrics m=complete_metrics();
    LabMateScopeReference ref={0};
    assert(labmate_scope_reference_preset(LabMateScopeReference1kHz50,&ref));
    LabMateScopeToleranceResult t=labmate_scope_tolerance_evaluate(
        &ref,&m,LabMateScopeObservationComplete);
    assert(t.verdict==LabMateScopeVerdictPass);
    Canvas c=fresh();
    assert(labmate_scope_reference_view_draw(&c,LabMateScopeReference1kHz50,t,&m));good(&c);
    assert(c.chip==UiKitInstrumentMatch&&c.active_page==3U);
    assert(has(&c,"Reference")&&has(&c,"Pin PC1")&&has(&c,"1kHz 50%"));
    assert(has(&c,"1.00kHz")&&has(&c,"50.0%"));
    assert(key(&c,UiKitKeyUp,"Target")&&key(&c,UiKitKeyDown,"Next"));
    LabMateScopeReference mismatch={0};
    assert(labmate_scope_reference_preset(LabMateScopeReference100Hz50,&mismatch));
    t=labmate_scope_tolerance_evaluate(&mismatch,&m,LabMateScopeObservationComplete);
    assert(t.verdict==LabMateScopeVerdictOutOfTolerance);
    c=fresh();assert(labmate_scope_reference_view_draw(&c,LabMateScopeReference100Hz50,t,&m));good(&c);
    assert(c.chip==UiKitInstrumentOff&&has(&c,"100Hz 50%"));
    t=labmate_scope_tolerance_evaluate(&ref,NULL,LabMateScopeObservationInvalid);
    c=fresh();assert(labmate_scope_reference_view_draw(&c,LabMateScopeReference1kHz50,t,NULL));good(&c);
    assert(c.chip==UiKitInstrumentWaiting&&has(&c,"--"));
    t=labmate_scope_tolerance_evaluate(&ref,NULL,LabMateScopeObservationNoSignalConfirmed);
    c=fresh();assert(labmate_scope_reference_view_draw(&c,LabMateScopeReference1kHz50,t,NULL));good(&c);
    assert(c.chip==UiKitInstrumentWaiting&&has(&c,"No signal"));
    t=labmate_scope_tolerance_evaluate(&ref,NULL,LabMateScopeObservationBusy);
    c=fresh();assert(labmate_scope_reference_view_draw(&c,LabMateScopeReference1kHz50,t,NULL));good(&c);
    assert(c.chip==UiKitInstrumentBusy&&has(&c,"Busy"));
    const LabMateScopeToleranceResult forged={.verdict=LabMateScopeVerdictPass};
    c=fresh();assert(!labmate_scope_reference_view_draw(&c,LabMateScopeReference1kHz50,forged,NULL));
    assert(c.paint==0U);
}
int main(void){
    test_scope();test_reference();
    puts("E11 SCOPE+REFERENCE STEP3 SOURCE-LINKED HOST PASS: ready/live/held/error,");
    puts("true edge plots, no-stale metrics, no-signal, busy, match/off/forged reject");
    return 0;
}
