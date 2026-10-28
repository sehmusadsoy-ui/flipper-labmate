/* UI-05E E11 GPIO: exact approved renderer, state/pin/label host matrix.
 * The waveform and trace helpers are deliberately stubbed: this test is
 * NOT the earlier 104-bit history regression or actual pin/IRQ testing.
 * No E11 SDK, hardware, storage, GPIO writes or capture acquisition.
 */
#include "ui_kit.h"
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
enum { GPIO_COUNT=8 };
typedef struct {
    uint8_t gpio_index;
    uint32_t edges;
    bool monitor_release_fault,monitor_blocked,monitor_active;
    bool hold,gpio_state;
} LabMateApp;
typedef struct { unsigned touched; } LabMateGpioUiTrace;
static LabMateGpioUiTrace labmate_gpio_trace;
struct Canvas {
    Font font;
    Color color;
    unsigned faults,text_count,chips,keys,pins,levels,panels;
    bool sampled_valid,panel_hold,level_high;
    uint8_t pin_index;
    UiKitInstrumentState chip_state;
    struct { int x,y,w; char label[32]; } text[16];
    struct { uint8_t x; UiKitKey key; char label[10]; } hints[2];
};
static uint32_t tick=1000U;
uint32_t furi_get_tick(void){return tick;}
void canvas_set_font(Canvas* c,Font f){c->font=f;}
void canvas_set_color(Canvas* c,Color v){c->color=v;}
uint16_t canvas_string_width(Canvas* c,const char* s) {
    const unsigned w=c->font==FontSecondary?5U:c->font==FontPrimary?6U:12U;
    return (uint16_t)(strlen(s)*w);
}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* s) {
    int w=(int)canvas_string_width(c,s);
    int h=c->font==FontPrimary?10:8;
    if(w<=0||x<0||x+w>128||y-h+1<0||y>=64)c->faults++;
    if(c->text_count>=16U){c->faults++;return;}
    unsigned n=c->text_count++;
    c->text[n].x=x;c->text[n].y=y;c->text[n].w=w;
    snprintf(c->text[n].label,32,"%s",s);
}
void canvas_draw_line(Canvas* c,int32_t x,int32_t y,int32_t xx,int32_t yy) {
    if(x<0||xx<0||x>=128||xx>=128||y<0||yy<0||y>=64)c->faults++;
}
uint8_t ui_kit_state_chip_width(Canvas* c,UiKitInstrumentState state) {
    (void)c;(void)state;return 45U;
}
bool ui_kit_state_chip_compact(Canvas* c,UiKitInstrumentState state,bool pulse) {
    (void)pulse;c->chip_state=state;c->chips++;return true;
}
uint8_t ui_kit_key_hint_compact(Canvas* c,uint8_t x,UiKitKey k,const char* s) {
    const unsigned width=k==UiKitKeyLeftRight?18U:19U;
    const unsigned end=x+width+3U+5U*strlen(s);
    if(end>127U)c->faults++;
    if(c->keys>=2U){c->faults++;return 0;}
    c->hints[c->keys].x=x;c->hints[c->keys].key=k;
    snprintf(c->hints[c->keys].label,10,"%s",s);
    c->keys++;
    return (uint8_t)end;
}
static void labmate_gpio_trace_update(LabMateGpioUiTrace* t,LabMateApp* app,
                                      uint32_t now,bool valid) {
    (void)app;(void)now;t->touched++;
    (void)valid;
}
static void labmate_gpio_pin_strip(Canvas* c,uint8_t pin) {
    c->pins++;c->pin_index=pin;
}
static void labmate_gpio_signal_panel(Canvas* c,const LabMateGpioUiTrace* trace,
                                      bool valid,bool hold,bool pulse) {
    (void)trace;(void)pulse;c->panels++;c->sampled_valid=valid;c->panel_hold=hold;
}
static void labmate_gpio_level_marker(Canvas* c,bool high) {
    c->levels++;c->level_high=high;
}
#include "draw_gpio.inc"
static bool key(const Canvas* c,UiKitKey k,const char* label){
    for(unsigned i=0;i<c->keys;i++)
        if(c->hints[i].key==k&&!strcmp(c->hints[i].label,label))return true;
    return false;
}
static bool has(const Canvas* c,const char* s){
    for(unsigned i=0;i<c->text_count;i++)
        if(strcmp(c->text[i].label,s)==0)return true;
    return false;
}
int main(void) {
    const uint32_t counts[]={0U,1U,145U,9999U,UINT32_MAX};
    unsigned total=0U;
    for(unsigned pin=0;pin<8;pin++)
    for(unsigned level=0;level<2;level++)
    for(unsigned flags=0;flags<16;flags++)
    for(unsigned j=0;j<5;j++) {
        Canvas c={0};LabMateApp a={0};
        a.gpio_index=(uint8_t)pin;a.edges=counts[j];
        a.gpio_state=level!=0;a.monitor_active=(flags&1U)!=0;
        a.hold=(flags&2U)!=0;a.monitor_blocked=(flags&4U)!=0;
        a.monitor_release_fault=(flags&8U)!=0;
        LabMateApp before=a;
        draw_gpio(&c,&a);
        assert(memcmp(&before,&a,sizeof(a))==0);
        assert(c.faults==0U&&c.color==ColorBlack);
        assert(c.chips==1U&&c.pins==1U&&c.panels==1U);
        assert(c.pin_index==pin&&labmate_gpio_trace.touched>0U);
        const bool valid=a.monitor_active&&!a.monitor_blocked&&!a.monitor_release_fault;
        assert(c.sampled_valid==valid&&c.panel_hold==a.hold);
        assert(c.levels==(valid?1U:0U));
        if(valid)assert(c.level_high==a.gpio_state);
        const UiKitInstrumentState expect=a.monitor_release_fault?UiKitInstrumentError:
            a.monitor_blocked?UiKitInstrumentBusy:!a.monitor_active?UiKitInstrumentReady:
            a.hold?UiKitInstrumentHeld:UiKitInstrumentLive;
        assert(c.chip_state==expect);
        assert(c.keys==2U&&c.hints[0].x==4&&c.hints[1].x==70);
        assert(key(&c,UiKitKeyLeftRight,"Pin"));
        assert(key(&c,UiKitKeyOk,a.hold?"Resume":"Hold"));
        assert(has(&c,valid?(a.gpio_state?"High":"Low"):"-"));
        /* Count and level never overlap inside y=52, even at UINT32_MAX. */
        for(unsigned i=0;i<c.text_count;i++)if(c.text[i].y==52)
            for(unsigned k=i+1;k<c.text_count;k++)if(c.text[k].y==52)
                assert(c.text[i].x+c.text[i].w<=c.text[k].x||
                       c.text[k].x+c.text[k].w<=c.text[i].x);
        total++;
    }
    assert(total==1280U);
    printf("E11 GPIO PRODUCTION RENDER HOST PASS: %u pin/state/level/count cases\n",total);
    return 0;
}
