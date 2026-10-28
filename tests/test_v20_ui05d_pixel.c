/* v2.0 E11 exact Frequency/Pulse/PWM renderer test; no HAL or SD.
 * Exact production ui_kit rendering helpers are also source-linked.
 * Only device Canvas, clock conversion and generator selection are mocks.
 */
#include "ui_kit.h"
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>

typedef enum {AlignRight=0,AlignBottom=0} Align;
typedef enum {LabMateAlertFrequency=0,LabMateAlertPulseDuty=1} AlertSource;
typedef struct {AlertSource source; bool armed,latched;} Threshold;
#define GPIO_COUNT 8U
#define LABMATE_PWM_CUSTOM_INDEX 15U
static const uint32_t presets[]={1,2,5,10,20,50,100,200,500,1000,2000,5000,10000,20000,50000};
static const uint32_t steps[]={1,10,100,1000};
static const char* const labmate_gpio_names[]={"PC0","PC1","PC3","PB2","PB3","PA4","PA6","PA7"};
typedef struct {
    uint8_t gpio_index,generator_freq_index,generator_duty_percent,generator_custom_step_index;
    uint8_t ui_pulse_phase,ui_frequency_trace_count,ui_frequency_trace_head,ui_frequency_trace[100];
    bool hold,capture_blocked,capture_release_fault,frequency_valid,frequency_stats_valid;
    uint32_t frequency_millihz,frequency_min_millihz,frequency_max_millihz,edges;
    Threshold threshold;
    bool generator_editing,generator_running,generator_blocked,generator_release_fault;
    uint32_t generator_custom_hz,generator_custom_draft_hz;
    bool pulse_stats_view,pulse_high_valid,pulse_low_valid,pulse_period_valid,pulse_stats_valid;
    uint32_t pulse_high_cycles,pulse_low_cycles,pulse_period_cycles,pulse_duty_permille;
    uint32_t pulse_min_high_cycles,pulse_max_high_cycles,pulse_min_low_cycles,pulse_max_low_cycles;
    uint32_t pulse_min_period_cycles,pulse_max_period_cycles;
    uint32_t pulse_min_duty_permille,pulse_max_duty_permille;
} LabMateApp;
typedef struct {char value[40];int32_t x,y;} DrawText;
struct Canvas {
    Font font;Color ink; unsigned faults,paint,count,lines,dots,frames;
    DrawText text[40];
};
void canvas_set_font(Canvas* c,Font f){c->font=f;}
void canvas_set_color(Canvas* c,Color x){c->ink=x;}
uint8_t canvas_current_font_height(Canvas* c){
    return c->font==FontBigNumbers?21U:c->font==FontPrimary?11U:8U;
}
uint16_t canvas_string_width(Canvas* c,const char* s){
    return (uint16_t)(strlen(s)*(c->font==FontBigNumbers?10U:
                                   c->font==FontPrimary?8U:6U));
}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* s) {
    unsigned w=canvas_string_width(c,s);
    if(x<0||y<0||y>=64||y<(int32_t)canvas_current_font_height(c)-1||
       x+(int32_t)w>128||!w)c->faults++;
    if(c->count<40U){
        DrawText* item=&c->text[c->count++];
        item->x=x;item->y=y;
        snprintf(item->value,sizeof(item->value),"%s",s);
    }else c->faults++;
    c->paint++;
}
void canvas_draw_str_aligned(Canvas* c,int32_t x,int32_t y,Align h,Align v,const char* s){
    assert(h==AlignRight&&v==AlignBottom);
    canvas_draw_str(c,x-(int32_t)canvas_string_width(c,s),y,s);
}
void canvas_draw_line(Canvas* c,int32_t x,int32_t y,int32_t a,int32_t b){
    if(x<0||a<0||x>127||a>127||y<0||b<0||y>63||b>63)c->faults++;
    c->paint++;c->lines++;
}
void canvas_draw_dot(Canvas* c,int32_t x,int32_t y){
    if(x<0||x>127||y<0||y>63)c->faults++;
    c->dots++;c->paint++;
}
void canvas_draw_rframe(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t r){
    (void)r;
    if(x<0||y<0||w<=0||h<=0||x+w>128||y+h>64)c->faults++;
    c->paint++;c->frames++;
}
void canvas_draw_rbox(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t r){
    canvas_draw_rframe(c,x,y,w,h,r);
}
void canvas_draw_box(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h){
    canvas_draw_rframe(c,x,y,w,h,0);
}
uint32_t labmate_generator_frequency(const LabMateApp* a){
    if(a->generator_freq_index==LABMATE_PWM_CUSTOM_INDEX)
        return a->generator_editing?a->generator_custom_draft_hz:a->generator_custom_hz;
    return a->generator_freq_index<15U?presets[a->generator_freq_index]:0U;
}
uint32_t labmate_generator_custom_step_hz(const LabMateApp* a){
    return steps[a->generator_custom_step_index<4U?a->generator_custom_step_index:0U];
}
uint64_t pulse_cycles_to_us(uint32_t cycles){
    return ((uint64_t)cycles*1000000ULL+32000000ULL)/64000000ULL;
}
#include "ui_kit_rect.inc"
#include "ui_kit_text.inc"
#include "ui_kit_center_text.inc"
#include "ui_kit_back_title.inc"
#include "ui_kit_pulse_line.inc"
#include "ui_kit_sparkline.inc"
#include "frequency_format_compact.inc"
#include "frequency_format_tiny.inc"
#include "frequency_hero_text.inc"
#include "draw_frequency.inc"
#include "draw_generator.inc"
#include "pulse_ui_format_value.inc"
#include "draw_pulse_stats.inc"
#include "draw_pulse.inc"
static bool has(const Canvas* c,const char* value){
    for(unsigned i=0;i<c->count;i++)if(!strcmp(c->text[i].value,value))return true;
    return false;
}
static void check(const Canvas* c,const LabMateApp* a,const LabMateApp* before){
    if(c->faults)fprintf(stderr,"pixel faults=%u texts=%u\n",c->faults,c->count);
    assert(c->faults==0U&&c->paint>0U&&c->ink==ColorBlack);
    assert(memcmp(a,before,sizeof(*a))==0);
}
static unsigned frequency_test(void){
    static const uint32_t values[]={0U,1U,9999U,10000U,999999U,1000000U,9999999U,
                                    10000000U,99999999U,100000000U,1000000000U,UINT32_MAX};
    unsigned cases=0;
    for(unsigned ix=0;ix<12U;ix++)for(unsigned mode=0;mode<2U;mode++)
    for(unsigned state=0;state<6U;state++)for(unsigned stats=0;stats<2U;stats++){
        LabMateApp a={0};Canvas c={0};
        a.gpio_index=(uint8_t)(mode?4U:1U);
        a.frequency_valid=ix!=0U;
        a.frequency_stats_valid=stats!=0U;
        a.frequency_millihz=a.frequency_min_millihz=a.frequency_max_millihz=values[ix];
        a.ui_pulse_phase=135U;
        a.threshold.source=LabMateAlertFrequency;
        a.threshold.armed=a.threshold.latched=state==3U;
        a.hold=state==1U;
        a.capture_blocked=state==2U;
        a.capture_release_fault=state==4U;
        if(stats&&ix>0U){
            a.ui_frequency_trace_count=4U;a.ui_frequency_trace_head=4U;
            a.ui_frequency_trace[0]=0;a.ui_frequency_trace[1]=255U;
            a.ui_frequency_trace[2]=40U;a.ui_frequency_trace[3]=180U;
        }
        LabMateApp before=a;
        draw_frequency(&c,&a);check(&c,&a,&before);
        assert(has(&c,"Frequency")&&has(&c,mode?"PB3":"PC1"));
        assert(has(&c,"Min")&&has(&c,"Max")&&c.frames>=1U);
        const char* status=a.threshold.latched?"Alert":a.capture_blocked?"Busy":
            a.hold?"Held":!a.frequency_valid?"No signal":"Stable";
        assert(has(&c,status));
        if(!a.frequency_valid)assert(has(&c,"No signal"));
        cases++;
    }
    return cases;
}
static unsigned generator_test(void){
    unsigned cases=0;
    for(unsigned choice=0;choice<16U;choice++)for(unsigned duty=0;duty<3U;duty++)
    for(unsigned status=0;status<4U;status++)for(unsigned editing=0;editing<2U;editing++){
        LabMateApp a={0};Canvas c={0};
        a.generator_freq_index=(uint8_t)choice;
        a.generator_duty_percent=(uint8_t)(duty==0?5U:duty==1?50U:95U);
        a.generator_custom_hz=49999U;a.generator_custom_draft_hz=50000U;
        a.generator_custom_step_index=(uint8_t)(choice%4U);
        a.generator_editing=choice==15U&&editing!=0U;
        a.generator_running=status==1U;
        a.generator_blocked=status==2U;
        a.generator_release_fault=status==3U;
        LabMateApp before=a;
        draw_generator(&c,&a);check(&c,&a,&before);
        assert(has(&c,"PWM studio")&&has(&c,"PA7")&&has(&c,"Duty")&&c.lines>=5U);
        const char* label=a.generator_release_fault?"Error":
            a.generator_blocked?"Busy":a.generator_editing?"Editing":
            a.generator_running?"Running":"Stopped";
        assert(has(&c,label));
        char d[12];snprintf(d,sizeof(d),"%u%%",a.generator_duty_percent);
        assert(has(&c,d));cases++;
    }
    return cases;
}
static unsigned pulse_test(void){
    static const uint32_t durations[]={0U,1U,63936U,64000U,640000U,64000000U,UINT32_MAX};
    static const uint32_t duties[]={0U,500U,1000U};
    unsigned cases=0;
    for(unsigned pin=0;pin<8U;pin++)for(unsigned page=0;page<2U;page++)
    for(unsigned valid=0;valid<2U;valid++)for(unsigned period=0;period<7U;period++)
    for(unsigned duty=0;duty<3U;duty++)for(unsigned state=0;state<6U;state++){
        LabMateApp a={0};Canvas c={0};
        a.gpio_index=(uint8_t)pin;a.pulse_stats_view=page!=0U;
        a.pulse_high_valid=a.pulse_low_valid=a.pulse_period_valid=valid!=0U;
        a.pulse_stats_valid=valid!=0U;
        a.pulse_high_cycles=a.pulse_low_cycles=a.pulse_period_cycles=durations[period];
        a.pulse_min_high_cycles=a.pulse_max_high_cycles=durations[period];
        a.pulse_min_low_cycles=a.pulse_max_low_cycles=durations[period];
        a.pulse_min_period_cycles=a.pulse_max_period_cycles=durations[period];
        a.pulse_min_duty_permille=a.pulse_max_duty_permille=a.pulse_duty_permille=duties[duty];
        a.hold=state==1U;a.capture_blocked=state==2U;
        a.capture_release_fault=state==4U;
        a.threshold.source=LabMateAlertPulseDuty;
        a.threshold.armed=a.threshold.latched=state==3U;
        LabMateApp before=a;
        draw_pulse(&c,&a);check(&c,&a,&before);
        assert(has(&c,"Pulse")&&has(&c,labmate_gpio_names[pin]));
        if(page){
            assert(has(&c,"TYPE")&&has(&c,"MIN")&&has(&c,"MAX"));
            assert(has(&c,"HIGH")&&has(&c,"LOW")&&has(&c,"PER")&&has(&c,"DUTY"));
            assert(has(&c,"vRST")&&has(&c,"^BACK"));
            assert(has(&c,a.hold?"OK LIVE":"OK HOLD"));
            if(!valid)assert(has(&c,"---"));
        }else{
            assert(has(&c,"High")&&has(&c,"Low"));
            const char* label=a.capture_blocked?"Busy":a.hold?"Held":
                a.pulse_period_valid?"Live":"No signal";
            assert(has(&c,label));
            if(!valid)assert(has(&c,"No signal"));
        }
        cases++;
    }
    return cases;
}
int main(void){
    const unsigned f=frequency_test(),g=generator_test(),p=pulse_test();
    assert(f==288U&&g==384U&&p==4032U);
    printf("E11 UI05D EXACT RENDER PASS: frequency=%u PWM=%u pulse=%u total=%u\n",f,g,p,f+g+p);
    return 0;
}
