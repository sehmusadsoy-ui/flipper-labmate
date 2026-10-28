/* Step1 source-linked 128x64 components — host Canvas mock only. */
#include "ui_kit.h"
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
struct Canvas {
    Font font; Color ink; unsigned faults, paints, text_count, dots, lines, boxes, frames;
    int16_t first_text_x; const char* first_text;
    int16_t leftmost, rightmost, topmost, bottommost;
};
static void pos(Canvas* c,int32_t x,int32_t y) {
    if(x<0||x>=128||y<0||y>=64)c->faults++;
    else {if(x<c->leftmost)c->leftmost=x;if(x>c->rightmost)c->rightmost=x;
          if(y<c->topmost)c->topmost=y;if(y>c->bottommost)c->bottommost=y;}
    c->paints++;
}
void canvas_set_font(Canvas* c,Font f){c->font=f;}
uint16_t canvas_string_width(Canvas* c,const char* s){
    return (uint16_t)(strlen(s)*(c->font==FontPrimary?8U:6U));
}
void canvas_set_color(Canvas* c,Color color){c->ink=color;}
void canvas_draw_dot(Canvas* c,int32_t x,int32_t y){pos(c,x,y);c->dots++;}
void canvas_draw_line(Canvas* c,int32_t x,int32_t y,int32_t x2,int32_t y2){
    pos(c,x,y);pos(c,x2,y2);c->lines++;
}
void canvas_draw_box(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h){
    if(w<1||h<1)c->faults++;
    pos(c,x,y);pos(c,x+w-1,y+h-1);c->boxes++;
}
void canvas_draw_rframe(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t r){
    (void)r;pos(c,x,y);pos(c,x+w-1,y+h-1);c->frames++;
}
void canvas_draw_rbox(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t r){
    canvas_draw_rframe(c,x,y,w,h,r);
}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* str){
    if(!c->text_count){c->first_text_x=x;c->first_text=str;}
    int w=(int)canvas_string_width(c,str);
    if(!w||y<8) c->faults++;
    else {pos(c,x,y);pos(c,x+w-1,y);}
    c->text_count++;
}
static Canvas fresh(void){
    Canvas c={0};c.leftmost=128;c.topmost=64;c.ink=ColorBlack;return c;
}

/* The .inc is extracted VERBATIM from production ui_kit.c at CI time. */
#undef ui_kit_stat_row
#include "uikit_step1_exact.inc"

static void test_header(void) {
    Canvas c=fresh();
    assert(ui_kit_pixel_header(&c,"Button",true,UiKitInstrumentLive,false));
    assert(c.faults==0U&&c.frames==1U&&c.text_count==2U);
    assert(c.first_text_x==9 && strcmp(c.first_text,"Button")==0);
    assert(c.ink==ColorBlack);
    c=fresh();
    assert(ui_kit_pixel_header(&c,"Scope",true,UiKitInstrumentHeld,true));
    assert(c.faults==0U);
    c=fresh();
    assert(ui_kit_pixel_header(&c,"Reference",false,UiKitInstrumentReady,false));
    assert(c.text_count==1U&&c.faults==0U);
    c=fresh();
    assert(!ui_kit_pixel_header(&c,"Reference",true,UiKitInstrumentWaiting,false));
    assert(c.paints==0U); /* Don't silently clip or move >2px. */
    c=fresh();
    assert(!ui_kit_pixel_header(&c,"Reference",true,UiKitInstrumentMatch,false));
    assert(c.paints==0U);
    c=fresh();
    assert(ui_kit_pixel_header(&c,"Reference",true,UiKitInstrumentOff,false));
    assert(c.faults==0U);
}
static void test_states(void) {
    const UiKitInstrumentState states[]={
        UiKitInstrumentReady,UiKitInstrumentLive,UiKitInstrumentHeld,
        UiKitInstrumentStopped,UiKitInstrumentBusy,UiKitInstrumentError,
        UiKitInstrumentWaiting,UiKitInstrumentMatch,UiKitInstrumentOff};
    for(unsigned j=0;j<sizeof(states)/sizeof(states[0]);j++){
        Canvas c=fresh();
        uint8_t w=ui_kit_state_chip_width(&c,states[j]);
        assert(w>=29U&&w<=90U);
        assert(ui_kit_state_chip_compact(&c,states[j],j%2U));
        assert(c.frames==1U&&c.text_count==1U&&c.faults==0U&&c.ink==ColorBlack);
    }
    Canvas c=fresh();
    assert(!ui_kit_state_chip_compact(&c,(UiKitInstrumentState)99,false));
    assert(c.paints==0U);
}
static void test_keys(void) {
    Canvas c=fresh();
    uint8_t end=ui_kit_key_hint_compact(&c,4U,UiKitKeyDown,"Details");
    assert(end<=127U && end>4U && c.frames==1U && c.faults==0U);
    c=fresh();
    assert(ui_kit_key_hint_compact(&c,70U,UiKitKeyDown,"Next"));
    assert(c.faults==0U);
    c=fresh();
    assert(ui_kit_key_hint_compact(&c,70U,UiKitKeyOk,"Stop"));
    assert(c.faults==0U);
    c=fresh();
    assert(!ui_kit_key_hint_compact(&c,120U,UiKitKeyDown,"Next"));
    assert(c.paints==0U);
}
static void test_rows(void) {
    struct {const char* l;const char* v;const char* u;uint8_t y;} const rows[]={
        {"Bounce time","120"," us",23U},{"Settle time","8"," ms",32U},
        {"Hold time","340"," ms",41U},{"Bounces","3",NULL,50U},
        {"Frequency","1.00"," kHz",42U},{"Duty","50.0"," %",51U}};
    for(unsigned i=0;i<sizeof(rows)/sizeof(rows[0]);i++){
        Canvas c=fresh();
        assert(ui_kit_stat_row_unit(&c,rows[i].y,rows[i].l,rows[i].v,rows[i].u));
        assert(c.faults==0U && c.text_count==(rows[i].u?3U:2U));
    }
    Canvas c=fresh();
    assert(!ui_kit_stat_row_unit(&c,23U,"A very long metric title","120"," us"));
    assert(c.paints==0U);
    c=fresh();
    assert(!ui_kit_stat_row_unit(&c,23U,"Bounce time","120","us"));
    assert(c.paints==0U);
    c=fresh();
    assert(ui_kit_stat_row(&c,21U,"A","1")); /* legacy 4-arg ABI */
    assert(c.faults==0U);
}
static void test_dotted(void) {
    Canvas c=fresh();
    assert(ui_kit_pulse_line_dotted(&c,10U,33U,108U));
    assert(c.faults==0U&&c.dots>40U&&c.lines==0U);
    assert(c.leftmost==10&&c.rightmost<=118&&c.topmost<=29);
    c=fresh();
    assert(!ui_kit_pulse_line_dotted(&c,120U,33U,108U));
    assert(c.paints==0U);
}
static void test_trace(void) {
    const uint8_t valid[]={1,1,0,0,1,1,0,0};
    Canvas c=fresh();
    assert(ui_kit_mini_trace(&c,8U,25U,112U,5U,valid,8U));
    assert(c.faults==0U&&c.leftmost==8U&&c.rightmost==119U);
    assert(c.bottommost==29U && c.topmost==25U);
    const uint8_t quick[]={1,0,1,0,1,0,1,0};
    c=fresh();
    assert(ui_kit_mini_trace(&c,8U,25U,2U,5U,quick,8U));
    assert(c.lines>=2U && c.faults==0U); /* min/max transition retention */
    uint8_t invalid[]={1,0,2,1};
    c=fresh();
    assert(!ui_kit_mini_trace(&c,8U,25U,20U,5U,invalid,4U));
    assert(c.paints==0U);
    c=fresh();
    assert(!ui_kit_mini_trace(&c,8U,25U,20U,5U,NULL,0U));
    assert(c.paints==0U);
}
static void test_paging(void) {
    for(uint8_t i=0;i<4U;i++){
        Canvas c=fresh();
        assert(ui_kit_scope_page_dots(&c,i));
        assert(c.faults==0U&&c.boxes==3U&&c.lines==5U);
        assert(c.leftmost>=98 && c.leftmost<=99 && c.rightmost<=123);
    }
    Canvas c=fresh();
    assert(!ui_kit_scope_page_dots(&c,4U));
    assert(c.paints==0U);
    c=fresh();ui_kit_next_cue(&c);
    assert(c.lines==2U&&c.dots==1U);
    assert(c.leftmost==61&&c.rightmost==65&&c.topmost==59&&c.bottommost==61);
}
int main(void){
    test_header();test_states();test_keys();test_rows();
    test_dotted();test_trace();test_paging();
    puts("BUTTON/SCOPE STEP1 UI-KIT SOURCE-LINKED HOST PASS: headers, states,");
    puts("keys, stat rows, dotted empty, min/max traces, 4-page dots and next cue");
    return 0;
}
