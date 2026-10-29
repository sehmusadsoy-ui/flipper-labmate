/* E11 UI-05B migration: production draw_alerts() and labmate_pixel_ui.h
 * with real threshold source names, 128x64 host Canvas, no GPIO/SD.
 * Button is tested separately by the existing Step2 exact-source harness.
 */
#include "labmate_threshold.h"
#include "labmate_pixel_ui.h"
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

typedef enum {AlignRight, AlignBottom} Align;
typedef struct {LabMateThreshold threshold;} LabMateApp;
struct Canvas {
    Font font;
    Color ink;
    unsigned faults, paints, text_count, boxes, key_count, header;
    char messages[16][40];
    struct {UiKitKey key; uint8_t x; char label[20];} keys[2];
};
void canvas_set_font(Canvas* c,Font f){c->font=f;}
uint16_t canvas_string_width(Canvas* c,const char* s) {
    const unsigned width=c->font==FontPrimary?8U:
        c->font==FontBigNumbers?10U:6U;
    return (uint16_t)(strlen(s)*width);
}
void canvas_set_color(Canvas* c,Color v){c->ink=v;}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* t) {
    const int w=canvas_string_width(c,t);
    const int h=c->font==FontPrimary?10:8;
    if(!w||x<0||x+w>128||y<0||y>=64||y-h+1<0)c->faults++;
    if(c->text_count<16U)
        snprintf(c->messages[c->text_count],40,"%s",t);
    else c->faults++;
    c->text_count++;c->paints++;
}
void canvas_draw_str_aligned(Canvas* c,int32_t x,int32_t y,Align h,Align v,const char* t) {
    assert(h==AlignRight&&v==AlignBottom);
    canvas_draw_str(c,x-(int32_t)canvas_string_width(c,t),y,t);
}
void canvas_draw_line(Canvas* c,int32_t x,int32_t y,int32_t xx,int32_t yy) {
    if(x<0||x>=128||xx<0||xx>=128||y<0||y>=64||yy<0||yy>=64)c->faults++;
    c->paints++;
}
void canvas_draw_rbox(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t r) {
    (void)r;
    if(x<0||y<0||x+w>128||y+h>64||w<=0||h<=0)c->faults++;
    c->boxes++;c->paints++;
}
void canvas_draw_rframe(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t r) {
    canvas_draw_rbox(c,x,y,w,h,r);
}
void ui_kit_back_title(Canvas* c,const char* name,const char* unused,const char* pin) {
    (void)unused;(void)pin;
    c->header++;
    /* Mirror real ui_kit_back_title font and coordinates. */
    canvas_set_color(c,ColorBlack);
    canvas_set_font(c,FontSecondary);
    canvas_draw_line(c,7,2,4,5);
    canvas_draw_line(c,4,5,7,8);
    canvas_draw_str(c,12,9,name);
}
void ui_kit_panel(Canvas* c,uint8_t x,uint8_t y,uint8_t w,uint8_t h) {
    canvas_draw_rframe(c,x,y,w,h,3);
}
bool ui_kit_text(Canvas* c,int16_t x,int16_t baseline,uint8_t w,
                 const char* label,const char* short_label) {
    canvas_set_font(c,FontSecondary);
    const char* chosen=label;
    if(canvas_string_width(c,chosen)>w)chosen=short_label;
    if(!chosen||canvas_string_width(c,chosen)>w)return false;
    canvas_draw_str(c,x,baseline,chosen);
    return true;
}
uint8_t ui_kit_key_hint_compact(Canvas* c,uint8_t x,UiKitKey k,const char* s) {
    unsigned width=k==UiKitKeyOk?19U:16U;
    unsigned right=x+width+3U+strlen(s)*6U;
    if(!s||right>127U||c->key_count>=2U){c->faults++;return 0U;}
    unsigned idx=c->key_count++;
    c->keys[idx].x=x;c->keys[idx].key=k;
    snprintf(c->keys[idx].label,20,"%s",s);
    c->paints++;
    return (uint8_t)right;
}

/* Unmodified draw_alerts() is extracted by the runner at CI time. */
#include "draw_alerts_e11_current.inc"
static bool text(const Canvas* c,const char* t) {
    for(unsigned i=0;i<c->text_count&&i<16U;i++)
        if(!strcmp(c->messages[i],t))return true;
    return false;
}
static bool key(const Canvas* c,unsigned idx,UiKitKey k,const char* t) {
    return idx<c->key_count&&c->keys[idx].key==k&&
        !strcmp(c->keys[idx].label,t);
}
static void verify(LabMateApp* a,const char* status,const char* state,
                   UiKitKey key1,const char* act1,UiKitKey key2,const char* act2) {
    Canvas c={0};c.ink=ColorBlack;
    LabMateApp before=*a;
    draw_alerts(&c,a);
    assert(!memcmp(&before,a,sizeof(*a)));
    assert(c.faults==0U&&c.ink==ColorBlack);
    assert(c.header==1U && c.boxes==2U && c.key_count==2U);
    assert(text(&c,"Alerts") && text(&c,"SOURCE")&&text(&c,"LIMIT"));
    assert(text(&c,status) && text(&c,state));
    assert(text(&c,labmate_threshold_source_name(a->threshold.source)));
    assert(key(&c,0U,key1,act1) && key(&c,1U,key2,act2));
}
int main(void) {
    LabMateApp a={0};
    unsigned cases=0U;
    for(unsigned source=0U;source<LabMateAlertSourceCount;source++) {
        for(unsigned limit=0U;limit<3U;limit++) {
            memset(&a,0,sizeof(a));
            a.threshold.source=(LabMateAlertSource)source;
            a.threshold.limit=limit==0U?1U:limit==1U?50U:UINT32_MAX;
            verify(&a,"OFF","DISARMED",UiKitKeyLeftRight,"Source",
                   UiKitKeyOk,"Arm");cases++;
            a.threshold.armed=true;
            verify(&a,"ARM","WAITING FOR INPUT",UiKitKeyOk,"Off",
                   UiKitKeyBack,"Exit");cases++;
            a.threshold.has_sample=true;
            verify(&a,"ARM","BELOW LIMIT",UiKitKeyOk,"Off",
                   UiKitKeyBack,"Exit");cases++;
            a.threshold.active=true;
            verify(&a,"ARM","LIMIT REACHED",UiKitKeyOk,"Off",
                   UiKitKeyBack,"Exit");cases++;
            a.threshold.latched=true;
            verify(&a,"ALRT","ALERT LATCHED",UiKitKeyDown,"Ack",
                   UiKitKeyOk,"Off");cases++;
            a.threshold.active=false;
            verify(&a,"ALRT","ALERT LATCHED",UiKitKeyDown,"Ack",
                   UiKitKeyOk,"Off");cases++;
        }
    }
    assert(cases==72U);
    puts("E11 UI05B CURRENT ALERTS EXACT RENDER PASS: 72 source/limit/state cases");
    return 0;
}
