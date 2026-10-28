/* E11 UI05 current Logger production renderer under strict 128x64 host Canvas.
 * Host logic validates displays only; actual capture/storage is never emulated.
 * Legacy pre-pixel test_v20_ui05_logger.c stays as a historical fixture.
 */
#include "labmate_pixel_ui.h"
#include <assert.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef enum {AlignRight=0} Align;
typedef enum {AlignBottom=0} AlignVertical;
typedef enum {LoggerFrequencyLow=0, LoggerFrequencyHigh, LoggerPulse} LabMateLoggerSource;
typedef struct {
    LabMateLoggerSource logger_source;
    bool pulse_period_valid, frequency_valid, logger_busy, logger_busy_stopping;
    bool capture_blocked, logger_error, logger_recording;
    uint32_t pulse_period_cycles, pulse_duty_permille, frequency_millihz, logger_rows;
    char logger_path[80];
} LabMateApp;
typedef struct {
    unsigned x;
    UiKitKey key;
    char name[20];
} KeySnapshot;
struct Canvas {
    Font font;
    Color ink;
    unsigned faults, paint, texts, headers, chips, keys;
    bool emphasized;
    char title[20], badge[16], labels[16][48];
    KeySnapshot hints[2];
};
void canvas_set_font(Canvas* c, Font f) {c->font=f;}
void canvas_set_color(Canvas* c, Color color) {c->ink=color;}
uint16_t canvas_string_width(Canvas* c, const char* s) {
    return (uint16_t)(strlen(s)*(c->font==FontPrimary?8U:
                                    c->font==FontBigNumbers?10U:6U));
}
void canvas_draw_str(Canvas* c, int32_t x, int32_t y, const char* s) {
    assert(c && s);
    unsigned w=canvas_string_width(c,s);
    unsigned h=c->font==FontPrimary?11U:8U;
    if(w==0U || x<0 || x+(int32_t)w>128 || y<(int32_t)h-1 || y>=64) c->faults++;
    if(c->texts<16U) snprintf(c->labels[c->texts],sizeof(c->labels[0]),"%s",s);
    else c->faults++;
    c->texts++;c->paint++;
}
void canvas_draw_str_aligned(
    Canvas* c,int32_t x,int32_t y,Align horizontal,AlignVertical vertical,const char* s) {
    assert(horizontal==AlignRight && vertical==AlignBottom);
    canvas_draw_str(c,x-(int32_t)canvas_string_width(c,s),y,s);
}
void canvas_draw_line(Canvas* c,int32_t x,int32_t y,int32_t xx,int32_t yy) {
    if(x<0||x>=128||xx<0||xx>=128||y<0||y>=64||yy<0||yy>=64)c->faults++;
    c->paint++;
}
void canvas_draw_rbox(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t r) {
    (void)r;
    if(x<0||y<0||w<=0||h<=0||x+w>128||y+h>64)c->faults++;
    c->chips++;c->emphasized=true;c->paint++;
}
void canvas_draw_rframe(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t r) {
    (void)r;
    if(x<0||y<0||w<=0||h<=0||x+w>128||y+h>64)c->faults++;
    c->chips++;c->paint++;
}
void ui_kit_back_title(Canvas* c,const char* name,const char* unused,const char* pin) {
    (void)unused; (void)pin;
    c->headers++;
    snprintf(c->title,sizeof(c->title),"%s",name);
    canvas_set_font(c,FontSecondary);
    canvas_draw_line(c,7,2,4,5);
    canvas_draw_line(c,4,5,7,8);
    canvas_draw_str(c,12,9,name);
}
bool ui_kit_text(Canvas* c,int16_t x,int16_t y,uint8_t width,
                 const char* label,const char* short_label) {
    if(!label)return false;
    canvas_set_font(c,FontSecondary);
    const char* chosen=label;
    if(canvas_string_width(c,chosen)>width)chosen=short_label;
    if(!chosen || canvas_string_width(c,chosen)>width)return false;
    canvas_draw_str(c,x,y,chosen);
    return true;
}
uint8_t ui_kit_key_hint_compact(Canvas* c,uint8_t x,UiKitKey key,const char* label) {
    if(!label || c->keys>=2U) {c->faults++;return 0U;}
    unsigned width=key==UiKitKeyOk?19U:key==UiKitKeyLeftRight?18U:16U;
    unsigned end=x+width+3U+6U*(unsigned)strlen(label);
    if(end>127U)c->faults++;
    KeySnapshot* hint=&c->hints[c->keys++];
    hint->x=x; hint->key=key;
    snprintf(hint->name,sizeof(hint->name),"%s",label);
    c->paint++;
    return (uint8_t)end;
}
/* Controlled conversion values chosen solely to exercise UI scale boundaries. */
uint64_t pulse_cycles_to_us(uint32_t cycles) {return (uint64_t)cycles;}
#include "logger_e11_current.inc"

static bool has(const Canvas* c,const char* s) {
    for(unsigned i=0;i<c->texts && i<16U;i++)
        if(!strcmp(c->labels[i],s))return true;
    return false;
}
static bool key(const Canvas* c,unsigned i,unsigned x,UiKitKey code,const char* name) {
    return i<c->keys && c->hints[i].x==x && c->hints[i].key==code &&
           !strcmp(c->hints[i].name,name);
}
static unsigned check(unsigned source,unsigned valid,unsigned state,unsigned scale) {
    static const uint32_t frequencies[]={0U,999999U,1000000U,UINT32_MAX};
    static const uint32_t pulse_us[]={800U,1000U,1000000U,UINT32_MAX};
    static const char* const f_expected[]={
        "0.000Hz","999.999Hz","1.000kHz","4294.967kHz"
    };
    static const char* const p_expected[]={
        "800us / 50.0%","1ms / 50.0%","1s / 50.0%","4295s / 100.0%"
    };
    LabMateApp a={0};
    Canvas c={0};
    a.logger_source=(LabMateLoggerSource)source;
    a.frequency_valid=valid!=0U; a.pulse_period_valid=valid!=0U;
    a.frequency_millihz=frequencies[scale];
    a.pulse_period_cycles=pulse_us[scale];
    a.pulse_duty_permille=scale==3U?1000U:500U;
    a.logger_rows=scale==3U?UINT32_MAX:3U;
    switch(state) {
    case 1: a.logger_busy=true; break;
    case 2: a.logger_busy=true; a.logger_busy_stopping=true; break;
    case 3: a.capture_blocked=true; break;
    case 4: a.logger_error=true; break;
    case 5: a.logger_recording=true; break;
    case 6: snprintf(a.logger_path,sizeof(a.logger_path),"%s","/ext/apps_data/labmate/log_1.csv"); break;
    case 7: a.logger_busy=true; a.logger_recording=true; break;
    case 8: a.capture_blocked=true; a.logger_error=true; break;
    case 9: a.logger_error=true; a.logger_recording=true; break;
    default: break;
    }
    const LabMateApp before=a;
    draw_logger(&c,&a);
    assert(!memcmp(&before,&a,sizeof(a)));
    assert(c.faults==0U && c.ink==ColorBlack);
    assert(c.headers==1U && c.chips==1U && !strcmp(c.title,"Logger"));
    const char* badge=a.logger_busy?"WAIT":
        a.capture_blocked?"BUSY":
        a.logger_error?"ERR":
        a.logger_recording?"REC":
        a.logger_path[0]?"DONE":"READY";
    assert(c.emphasized==a.logger_recording);
    assert(has(&c,badge));
    assert(has(&c,"MODE") && has(&c,"LIVE"));
    const char* mode=source==LoggerPulse?"PULSE / PC1":
        source==LoggerFrequencyHigh?"FREQ / PB3 HIGH":"FREQ / PC1 LOW";
    assert(has(&c,mode));
    const char* live=!valid?source==LoggerPulse?"NO VALID PULSE":"NO VALID FREQ":
        source==LoggerPulse?p_expected[scale]:f_expected[scale];
    assert(has(&c,live));
    if(a.logger_busy) {
        assert(has(&c,a.logger_busy_stopping?"SAVING TO SD":"OPENING SD"));
        assert(has(&c,"SD BUSY - WAIT") && c.keys==0U);
    } else {
        assert(c.keys==2U);
        if(a.capture_blocked) assert(has(&c,"CAPTURE BLOCKED"));
        else if(a.logger_error) assert(has(&c,"SD WRITE ERROR"));
        else if(a.logger_recording) {
            char status[32];
            snprintf(status,sizeof(status),"REC %lu ROWS",(unsigned long)a.logger_rows);
            assert(has(&c,status));
        } else if(a.logger_path[0]) {
            char status[32];
            snprintf(status,sizeof(status),"SAVED %lu",(unsigned long)a.logger_rows);
            assert(has(&c,status));
        } else assert(has(&c,"READY / 1 SEC SAMPLE"));
        if(a.logger_recording) {
            assert(key(&c,0U,4U,UiKitKeyOk,"Stop"));
            assert(key(&c,1U,66U,UiKitKeyBack,"Save"));
        } else {
            assert(key(&c,0U,4U,UiKitKeyLeftRight,"Source"));
            assert(key(&c,1U,66U,UiKitKeyOk,"Record"));
        }
    }
    return 1U;
}
int main(void) {
    unsigned total=0U;
    for(unsigned source=0;source<3U;source++)
    for(unsigned valid=0;valid<2U;valid++)
    for(unsigned state=0;state<10U;state++)
    for(unsigned scale=0;scale<4U;scale++)
        total+=check(source,valid,state,scale);
    assert(total==240U);
    printf("E11 UI05 EXACT LOGGER PIXEL PASS: %u source/valid/state/scale cases, read-only\n",total);
    return 0;
}
