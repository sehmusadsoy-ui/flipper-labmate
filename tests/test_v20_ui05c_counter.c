/* UI-05C E11 Counter: source-identical renderer with real pure formatter.
 * Canvas/chip/hint are bounded host mocks, not framebuffer/physical fonts.
 * Source-linked status/number/time/action test, NO GPIO/TIM2/device access.
 */
#include "ui_kit.h"
#include "labmate_threshold.h"
#include "labmate_counter_math.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <limits.h>
struct Canvas {
    Font font;
    Color color;
    unsigned errors, text_count, chip_count, key_count;
    UiKitInstrumentState chip;
    struct { int x,y; char label[40]; } text[24];
    struct { unsigned x; UiKitKey key; char label[12]; } keys[3];
};
void canvas_set_font(Canvas* c,Font f){c->font=f;}
void canvas_set_color(Canvas* c,Color v){c->color=v;}
uint16_t canvas_string_width(Canvas* c,const char* s){
    const unsigned w=c->font==FontSecondary?6U:c->font==FontPrimary?7U:12U;
    return (uint16_t)(strlen(s)*w);
}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* s) {
    const int w=canvas_string_width(c,s);
    const int h=c->font==FontSecondary?8:c->font==FontPrimary?10:17;
    if(w<=0 || x<0 || y-h+1<0 || x+w>128 || y>=64) c->errors++;
    if(c->text_count>=24U) {c->errors++;return;}
    c->text[c->text_count].x=x;
    c->text[c->text_count].y=y;
    snprintf(c->text[c->text_count].label,40,"%s",s);
    c->text_count++;
}
void canvas_draw_line(Canvas* c,int32_t x,int32_t y,int32_t xx,int32_t yy) {
    if(x<0||xx<0||x>=128||xx>=128||y<0||yy<0||y>=64||yy>=64)c->errors++;
}
bool ui_kit_state_chip_compact(Canvas* c,UiKitInstrumentState s,bool pulse){
    (void)pulse;c->chip=s;c->chip_count++;return true;
}
uint8_t ui_kit_key_hint_compact(Canvas* c,uint8_t x,UiKitKey key,const char* label){
    const unsigned key_width=key==UiKitKeyOk?19U:key==UiKitKeyUp?16U:18U;
    if(x+key_width+3U+6U*strlen(label)>127U)c->errors++;
    if(c->key_count>=3U){c->errors++;return 0;}
    c->keys[c->key_count].x=x;
    c->keys[c->key_count].key=key;
    snprintf(c->keys[c->key_count].label,12,"%s",label);
    c->key_count++;
    return (uint8_t)(x+key_width+3U+6U*strlen(label));
}
static uint32_t mock_tick=1000U;
uint32_t furi_get_tick(void){return mock_tick;}
typedef struct {
    uint64_t counter_total,counter_elapsed_ticks;
    uint32_t counter_start_tick,counter_elapsed_seconds;
    bool counter_active,capture_blocked,capture_release_fault;
    LabMateThreshold threshold;
} LabMateApp;
#include "counter_count.inc"
#include "counter_time.inc"
#include "draw_counter.inc"
static bool has(const Canvas* c,const char* text){
    for(unsigned i=0;i<c->text_count;i++)
        if(strcmp(c->text[i].label,text)==0)return true;
    return false;
}
static bool key(const Canvas* c,UiKitKey id,const char* label){
    for(unsigned i=0;i<c->key_count;i++)
        if(c->keys[i].key==id&&strcmp(c->keys[i].label,label)==0)return true;
    return false;
}
static unsigned cases=0U;
static void run(uint64_t count,uint32_t secs,unsigned flags) {
    Canvas c={0};LabMateApp a={0};
    a.counter_total=count;
    a.counter_elapsed_seconds=secs;
    a.counter_start_tick=flags&1U ? 456U:0U;
    a.counter_elapsed_ticks=flags&2U ? 123U:0U;
    a.counter_active=(flags&4U)!=0;
    a.capture_blocked=(flags&8U)!=0;
    a.capture_release_fault=(flags&16U)!=0;
    a.threshold.source=LabMateAlertCounter;
    a.threshold.armed=(flags&32U)!=0;
    a.threshold.latched=(flags&32U)!=0;
    LabMateApp before=a;
    draw_counter(&c,&a);
    assert(memcmp(&before,&a,sizeof(a))==0);
    assert(c.errors==0 && c.color==ColorBlack);
    assert(c.chip_count==1U);
    assert(has(&c,"Counter")&&has(&c,"Count")&&has(&c,"Time"));
    const UiKitInstrumentState expected=a.capture_release_fault ? UiKitInstrumentError:
        a.capture_blocked ? UiKitInstrumentBusy:a.counter_active?UiKitInstrumentLive:
        a.counter_start_tick||a.counter_elapsed_ticks||a.counter_total ?
            UiKitInstrumentStopped:UiKitInstrumentReady;
    assert(c.chip==expected);
    if(expected==UiKitInstrumentError||expected==UiKitInstrumentBusy){
        assert(c.key_count==0U && has(&c,"-"));
    }else if(expected==UiKitInstrumentLive) {
        assert(c.key_count==1U&&key(&c,UiKitKeyOk,"Stop"));
    }else if(expected==UiKitInstrumentStopped) {
        assert(c.key_count==2U&&key(&c,UiKitKeyOk,"Resume")&&key(&c,UiKitKeyUp,"Reset"));
    }else{
        assert(c.key_count==1U&&key(&c,UiKitKeyOk,"Start"));
    }
    ++cases;
}
int main(void){
    const uint64_t count[]={0ULL,1ULL,145ULL,999999ULL,1000000ULL,
        123456789ULL,1000000000ULL,UINT32_MAX,UINT64_MAX};
    const uint32_t sec[]={0U,1U,59U,60U,71U,3599U,3600U,UINT32_MAX};
    for(unsigned i=0;i<sizeof(count)/sizeof(count[0]);i++)
        for(unsigned j=0;j<sizeof(sec)/sizeof(sec[0]);j++)
            for(unsigned f=0;f<64U;f++)
                run(count[i],sec[j],f);
    assert(cases==4608U);
    printf("E11 COUNTER SOURCE RENDER HOST PASS: %u state/count/time cases\n",cases);
    return 0;
}
