/* Exact production draw_button() E11 pixel integration regression.
 * Host Canvas model exercises all states, notices, actions, and measurement
 * validity; no PC1/GPIO, ISR, storage or firmware state are accessed.
 */
#include "ui_kit.h"
#include "labmate_button_logic.h"
#include "labmate_threshold.h"
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    LabMateThreshold threshold;
    bool capture_release_fault, capture_blocked, button_active;
    bool button_session_started, button_details_view;
    uint8_t ui_frame, button_quiet_ms;
    LabMateButtonStats button_stats;
    uint32_t button_bounce_us, button_settle_ms, button_hold_ms;
} LabMateApp;

typedef struct {
    char label[24], value[32], unit[12];
    unsigned y;
} Stat;
struct Canvas {
    Font font;
    Color color;
    unsigned faults, paint, frame, pill, disc, lines, text_count;
    unsigned key_count, stat_count, label_count;
    UiKitInstrumentState status;
    bool header_called, status_pulse;
    char first_text[30], context[40], contact[20];
    Stat stats[4];
    struct { unsigned x; UiKitKey key; char label[16]; } keys[3];
};
void canvas_set_font(Canvas* c,Font f) {c->font=f;}
void canvas_set_color(Canvas* c,Color v) {c->color=v;}
uint16_t canvas_string_width(Canvas* c,const char* s) {
    return (uint16_t)(strlen(s)*(c->font==FontPrimary?8U:6U));
}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* text) {
    unsigned w=canvas_string_width(c,text);
    if(x<0 || y<8 || y>=64 || x+w>128U || !w) c->faults++;
    c->paint++;
    if(!c->text_count) snprintf(c->first_text,sizeof(c->first_text),"%s",text);
    c->text_count++;
    if(!strcmp(text,"Open") || !strcmp(text,"Closed") || !strcmp(text,"Settling"))
        snprintf(c->contact,sizeof(c->contact),"%s",text);
}
void canvas_draw_line(Canvas* c,int32_t x,int32_t y,int32_t xx,int32_t yy) {
    if(x<0||xx<0||x>=128||xx>=128||y<0||yy<0||y>=64||yy>=64)c->faults++;
    c->lines++;c->paint++;
}
void canvas_draw_disc(Canvas* c,int32_t x,int32_t y,int32_t radius) {
    if(x-radius<0||x+radius>=128||y-radius<0||y+radius>=64)c->faults++;
    c->disc++;c->paint++;
}
void canvas_draw_rbox(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t rad) {
    (void)rad;
    if(x<0||y<0||x+w>128||y+h>64)c->faults++;
    c->pill++;c->paint++;
}
void canvas_draw_rframe(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t rad) {
    canvas_draw_rbox(c,x,y,w,h,rad);c->frame++;
}
bool ui_kit_pixel_header(Canvas* c,const char* title,bool chip,UiKitInstrumentState state,bool pulse) {
    if(!title || strcmp(title,"Button") || !chip)return false;
    c->status=state;c->status_pulse=pulse;c->header_called=true;
    c->paint++;
    return true;
}
bool ui_kit_text(Canvas* c,int16_t x,int16_t y,uint8_t width,
                 const char* label,const char* short_label) {
    if(!label || !width)return false;
    const char* chosen=label;
    if(canvas_string_width(c,chosen)>width)chosen=short_label;
    if(!chosen || canvas_string_width(c,chosen)>width)return false;
    if(x<0||x+canvas_string_width(c,chosen)>128||y>=64)c->faults++;
    if(y==23)snprintf(c->context,sizeof(c->context),"%s",chosen);
    c->label_count++;c->paint++;
    return true;
}
bool ui_kit_stat_row_unit(Canvas* c,uint8_t y,const char* l,const char* v,const char* u) {
    if(!l||!v||c->stat_count>=4)return false;
    c->font=FontSecondary;
    const unsigned lw=canvas_string_width(c,l);
    const unsigned uw=u?canvas_string_width(c,u):0U;
    c->font=FontPrimary;
    const unsigned vw=canvas_string_width(c,v);
    if(lw+uw+vw+8U>120U)return false;
    Stat* s=&c->stats[c->stat_count++];
    s->y=y;
    snprintf(s->label,sizeof(s->label),"%s",l);
    snprintf(s->value,sizeof(s->value),"%s",v);
    snprintf(s->unit,sizeof(s->unit),"%s",u?u:"");
    c->paint++;
    return true;
}
uint8_t ui_kit_key_hint_compact(Canvas* c,uint8_t x,UiKitKey k,const char* txt) {
    if(!txt||c->key_count>=3U)return 0;
    const unsigned kw=k==UiKitKeyOk?19U:16U;
    const unsigned end=x+kw+3U+6U*strlen(txt);
    if(end>127U)c->faults++;
    unsigned i=c->key_count++;
    c->keys[i].x=x;c->keys[i].key=k;
    snprintf(c->keys[i].label,sizeof(c->keys[i].label),"%s",txt);
    c->paint++;
    return (uint8_t)end;
}
#include "draw_button_exact.inc"

static bool key(const Canvas* c,unsigned i,unsigned x,UiKitKey id,const char* name) {
    return i<c->key_count&&c->keys[i].x==x&&c->keys[i].key==id&&
        !strcmp(c->keys[i].label,name);
}
static void run(unsigned flags,unsigned sample,unsigned quiet) {
    Canvas c={0};LabMateApp a={0};
    a.button_active=(flags&1U)!=0;
    a.button_session_started=(flags&2U)!=0;
    a.capture_blocked=(flags&4U)!=0;
    a.capture_release_fault=(flags&8U)!=0;
    a.button_details_view=(flags&16U)!=0;
    a.button_stats.pending=(flags&32U)!=0;
    a.button_stats.stable_level=(flags&64U)!=0;
    a.threshold.armed=(flags&128U)!=0;
    a.threshold.latched=(flags&128U)!=0;
    a.threshold.source=LabMateAlertButtonSettle;
    a.button_quiet_ms=quiet==0?5U:quiet==1?10U:quiet==2?20U:50U;
    a.ui_frame=flags&1U?16U:0U;
    a.button_stats.presses=sample==0?0U:sample==1?12U:1U;
    a.button_stats.releases=sample==1?11U:sample==3?1U:0U;
    a.button_stats.last_bounce_edges=sample?3U:0U;
    a.button_bounce_us=120U;
    a.button_settle_ms=8U;
    a.button_hold_ms=340U;
    const LabMateApp copy=a;
    draw_button(&c,&a);
    assert(!memcmp(&copy,&a,sizeof(a)));
    assert(c.faults==0U&&c.color==ColorBlack&&c.header_called);
    UiKitInstrumentState expected=a.capture_release_fault?UiKitInstrumentError:
        a.capture_blocked?UiKitInstrumentBusy:a.button_active?UiKitInstrumentLive:
        a.button_session_started?UiKitInstrumentStopped:UiKitInstrumentReady;
    assert(c.status==expected);
    assert(c.key_count==2U);
    assert(key(&c,0,4U,UiKitKeyDown,a.button_details_view?"Summary":"Details"));
    const char* action=a.button_active?"Stop":a.capture_blocked?"Retry":
                        a.button_session_started?"Resume":"Start";
    if(a.capture_release_fault)
        assert(key(&c,1,66U,UiKitKeyBack,"Exit"));
    else assert(key(&c,1,66U,UiKitKeyOk,action));
    if(!a.button_details_view) {
        assert(c.disc==2U&&c.pill==1U);
        assert(!strcmp(c.contact,a.button_stats.pending?"Settling":
                       a.button_stats.stable_level?"Open":"Closed"));
        assert(strstr(c.context,a.threshold.armed?"ALRT":"Pull-up"));
        assert(c.stat_count==0U&&c.label_count>=3U);
    } else {
        assert(c.disc==0U&&c.pill==0U);
        assert(c.stat_count==4U);
        assert(c.stats[0].y==24U&&c.stats[1].y==33U&&
               c.stats[2].y==42U&&c.stats[3].y==51U);
        const bool completed=a.button_stats.presses||a.button_stats.releases;
        assert(!strcmp(c.stats[0].value,completed?"120":"--"));
        assert(!strcmp(c.stats[1].value,completed?"8":"--"));
        assert(!strcmp(c.stats[2].value,a.button_stats.releases?"340":"--"));
        assert(!strcmp(c.stats[3].value,completed?"3":"--"));
        assert(!strcmp(c.stats[0].unit,completed?" us":""));
        assert(!strcmp(c.stats[2].unit,a.button_stats.releases?" ms":""));
    }
}
int main(void) {
    for(unsigned flags=0;flags<256U;flags++)
        for(unsigned sample=0;sample<4U;sample++)
            for(unsigned quiet=0;quiet<4U;quiet++)
                run(flags,sample,quiet);
    puts("E11 BUTTON STEP2 PRODUCTION RENDER PASS: 4096 scenarios, no state mutation");
    return 0;
}
