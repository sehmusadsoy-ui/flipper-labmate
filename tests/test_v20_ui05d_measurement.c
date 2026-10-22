/* UI-05D: exact-source Frequency, Pulse and PWM draw functions.
 * Host fonts are conservative rectangles, not physical Flipper rasters.
 * The producer's GPIO/IRQ/SD/timer code is NOT linked or invoked.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include "labmate_ui_layout.h"

typedef enum { FontSecondary=0, FontPrimary=1 } Font;
typedef enum { AlignRight=0, AlignBottom=0 } Align;
/* The extracted production three-action footer now fills its action band
 * with an inverse color. Model the real Canvas API, not a no-op workaround.
 */
typedef enum { ColorBlack=0, ColorWhite=1 } Color;
typedef struct { int32_t x0,y0,x1,y1; } Rect;
typedef struct Canvas Canvas;
struct Canvas {
    Font font;
    Rect labels[40];
    char values[40][48];
    unsigned count, faults;
    Color color;
    unsigned boxes;
    int badge_x, badge_y, badge_w;
};
static bool intersection(Rect a, Rect b) {
    return !(a.x1<b.x0 || b.x1<a.x0 || a.y1<b.y0 || b.y1<a.y0);
}
static void host_str(Canvas* c,int32_t x,int32_t y,const char* s) {
    assert(c && s && c->count < 40);
    const int32_t w=(int32_t)strlen(s)*(c->font==FontPrimary?8:6);
    const int32_t h=c->font==FontPrimary?11:8;
    const Rect rect={x,y-h+1,x+w-1,y};
    if(w<1 || rect.x0<0 || rect.y0<0 || rect.x1>=128 || rect.y1>=64){
        fprintf(stderr,"OUTSIDE (%ld,%ld) '%s' x1=%ld\n",(long)x,(long)y,s,(long)rect.x1);
        ++c->faults;
    }
    for(unsigned i=0;i<c->count;i++) if(intersection(rect,c->labels[i])) {
        fprintf(stderr,"OVERLAP '%s' + '%s'\n",s,c->values[i]);
        ++c->faults;
    }
    if(c->badge_w && x==c->badge_x+4 && y==c->badge_y+8 &&
       rect.x1>=c->badge_x+c->badge_w) {
        fprintf(stderr,"BADGE CLIP '%s'\n",s);
        ++c->faults;
    }
    c->labels[c->count]=rect;
    (void)snprintf(c->values[c->count],sizeof(c->values[0]),"%s",s);
    ++c->count;
}
void canvas_set_font(Canvas* c,Font f) { assert(c);c->font=f; }
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* s) {host_str(c,x,y,s);}
void canvas_draw_str_aligned(Canvas* c,int32_t x,int32_t y,Align horizontal,Align vertical,const char* s) {
    assert(horizontal==AlignRight && vertical==AlignBottom);
    host_str(c,x-(int32_t)strlen(s)*(c->font==FontPrimary?8:6),y,s);
}
void canvas_draw_line(Canvas* c,int32_t x0,int32_t y0,int32_t x1,int32_t y1) {
    assert(c);
    if(x0<0||x0>=128||x1<0||x1>=128||y0<0||y0>=64||y1<0||y1>=64)++c->faults;
}
void canvas_draw_box(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h) {
    assert(c);
    if(x<0||y<0||w<=0||h<=0||x+w>128||y+h>64)++c->faults;
    ++c->boxes;
}
void canvas_set_color(Canvas* c,Color color) {
    assert(c);
    assert(color==ColorBlack||color==ColorWhite);
    c->color=color;
}
/* Exact shared header semantics: left rail, primary title and rule.
 * This is the real primitive geometry, not a dummy accept-all stub.
 */
void ui_draw_header(Canvas* c,const char* title) {
    canvas_draw_box(c,0,1,1,10);
    canvas_set_font(c,FontPrimary);
    canvas_draw_str(c,2,10,title);
    canvas_draw_line(c,0,13,127,13);
}
void ui_badge(Canvas* c,uint8_t x,uint8_t y,uint8_t w,const char* value,bool fill) {
    (void)fill;
    if((unsigned)x+w>128U||(unsigned)y+11U>64U) ++c->faults;
    c->badge_x=x;c->badge_y=y;c->badge_w=w;
    canvas_set_font(c,FontSecondary); canvas_draw_str(c,x+4,y+8,value);
}
/* Source-linked real shared pair action band, including key formatting
 * and inverse Canvas operations. No longer accept a mock that never
 * paints the physical footer.
 */
#include "pair_validator.inc"
#include "pair_key.inc"
#include "pair_action.inc"
#include "pair_footer.inc"

/* Exact source functions extracted from the production shared UI primitives. */
#include "triple_validator.inc"
#include "triple_footer.inc"

typedef enum { LabMateAlertFrequency=0, LabMateAlertPulseDuty=1 } LabMateAlertSource;
typedef struct {LabMateAlertSource source;bool armed,latched;} LabMateThreshold;
#define LABMATE_PWM_CUSTOM_INDEX 15U
static const uint32_t presets[]={1,2,5,10,20,50,100,200,500,1000,2000,5000,10000,20000,50000};
static const uint32_t custom_steps[]={1,10,100,1000};
static const char* const labmate_gpio_names[]={"PC0","PC1","PC3","PB2","PB3","PA4","PA6","PA7"};
typedef struct {
    uint8_t gpio_index, generator_freq_index, generator_duty_percent, generator_custom_step_index;
    bool hold, capture_blocked, frequency_valid,frequency_stats_valid;
    uint32_t frequency_millihz,frequency_min_millihz,frequency_max_millihz,edges;
    LabMateThreshold threshold;
    bool generator_editing,generator_running,generator_blocked,generator_release_fault;
    uint32_t generator_custom_hz,generator_custom_draft_hz;
    bool pulse_stats_view,pulse_high_valid,pulse_low_valid,pulse_period_valid,pulse_stats_valid;
    uint32_t pulse_high_cycles,pulse_low_cycles,pulse_period_cycles,pulse_duty_permille;
    uint32_t pulse_min_high_cycles,pulse_max_high_cycles,pulse_min_low_cycles,pulse_max_low_cycles;
    uint32_t pulse_min_period_cycles,pulse_max_period_cycles;
    uint32_t pulse_min_duty_permille,pulse_max_duty_permille;
} LabMateApp;
static uint32_t labmate_generator_frequency(const LabMateApp* app) {
    if(app->generator_freq_index==LABMATE_PWM_CUSTOM_INDEX)
        return app->generator_editing?app->generator_custom_draft_hz:app->generator_custom_hz;
    return app->generator_freq_index<15U?presets[app->generator_freq_index]:0U;
}
static uint32_t labmate_generator_custom_step_hz(const LabMateApp* app) {
    return custom_steps[app->generator_custom_step_index<4U?app->generator_custom_step_index:0U];
}
/* Host-only 64-MHz model of CPU-cycle to time conversion. This helper is
 * for UI value-format bounds only: hardware clock/metrology is not tested. */
static uint64_t pulse_cycles_to_us(uint32_t cycles) {
    return ((uint64_t)cycles*1000000ULL+32000000ULL)/64000000ULL;
}
#include "frequency_compact.inc"
#include "frequency_edges.inc"
#include "draw_frequency.inc"
#include "draw_generator.inc"
#include "pulse_format.inc"
#include "pulse_metric.inc"
#include "pulse_stats.inc"
#include "draw_pulse.inc"
static bool contains(const Canvas* c,const char* s) {
    for(unsigned i=0;i<c->count;i++) if(!strcmp(c->values[i],s))return true;
    return false;
}
static unsigned frequency_test(void) {
    const uint32_t frequencies[]={0,1,9999,10000,999999,1000000,9999999,10000000,99999999,100000000,1000000000U,UINT32_MAX};
    unsigned count=0;
    for(unsigned k=0;k<12;k++)for(unsigned source=0;source<2;source++)
    for(unsigned status=0;status<4;status++)for(unsigned stats=0;stats<2;stats++){
        LabMateApp a={0}; Canvas c={0};
        a.gpio_index=source?4U:1U;
        a.frequency_valid=(k!=0);
        a.frequency_millihz=frequencies[k];
        a.frequency_stats_valid=stats!=0;
        a.frequency_min_millihz=frequencies[k];
        a.frequency_max_millihz=frequencies[k];
        a.edges=k==11?UINT32_MAX:(uint32_t)(k*100000U);
        a.threshold.source=LabMateAlertFrequency;
        a.threshold.armed=(status==3);a.threshold.latched=(status==3);
        a.capture_blocked=(status==2);a.hold=(status==1);
        LabMateApp before;memcpy(&before,&a,sizeof(a));
        draw_frequency(&c,&a);assert(memcmp(&before,&a,sizeof(a))==0);
        assert(c.color==ColorBlack && c.boxes>=1U);
        if(c.faults){fprintf(stderr,"FREQUENCY k=%u source=%u status=%u stats=%u\n",k,source,status,stats);return 0;}
        assert(contains(&c,source?"HIGH PB3":"LOW PC1"));
        ++count;
    }
    return count;
}
static unsigned generator_test(void) {
    unsigned count=0;
    for(unsigned choice=0;choice<16;choice++)for(unsigned duty=0;duty<3;duty++)
    for(unsigned status=0;status<4;status++)for(unsigned editing=0;editing<2;editing++){
        LabMateApp a={0};Canvas c={0};
        a.generator_freq_index=(uint8_t)choice;
        a.generator_custom_hz=49999;a.generator_custom_draft_hz=50000;
        a.generator_custom_step_index=(uint8_t)(choice%4U);
        a.generator_duty_percent=(uint8_t)(duty==0?5:duty==1?50:95);
        a.generator_editing=(choice==15&&editing==1);
        a.generator_running=(status==1);
        a.generator_blocked=(status==2);
        a.generator_release_fault=(status==3);
        LabMateApp before;memcpy(&before,&a,sizeof(a));
        draw_generator(&c,&a);assert(memcmp(&before,&a,sizeof(a))==0);
        assert(c.boxes >= 2U); /* Shared title rail plus production pair band. */
        /* Generator also uses the exact production inverted pair footer. */
        assert(c.color==ColorBlack);
        if(c.faults){fprintf(stderr,"GENERATOR choice=%u duty=%u status=%u edit=%u\n",choice,duty,status,editing);return 0;}
        assert(contains(&c,"OUT PA7"));
        ++count;
    }
    return count;
}
static unsigned pulse_test(void) {
    const uint32_t cycles[]={0,1,63936,64000,640000,64000000,UINT32_MAX};
    const uint32_t duty[]={0,500,1000};
    unsigned count=0;
    for(unsigned pin=0;pin<8;pin++)for(unsigned view=0;view<2;view++)
    for(unsigned valid=0;valid<2;valid++)for(unsigned ix=0;ix<7;ix++)
    for(unsigned d=0;d<3;d++)for(unsigned status=0;status<4;status++){
        LabMateApp a={0};Canvas c={0};
        a.gpio_index=(uint8_t)pin;
        a.pulse_stats_view=view!=0;
        a.pulse_high_valid=a.pulse_low_valid=a.pulse_period_valid=(valid!=0);
        a.pulse_stats_valid=valid!=0;
        a.pulse_high_cycles=a.pulse_low_cycles=a.pulse_period_cycles=cycles[ix];
        a.pulse_min_high_cycles=a.pulse_max_high_cycles=cycles[ix];
        a.pulse_min_low_cycles=a.pulse_max_low_cycles=cycles[ix];
        a.pulse_min_period_cycles=a.pulse_max_period_cycles=cycles[ix];
        a.pulse_min_duty_permille=a.pulse_max_duty_permille=a.pulse_duty_permille=duty[d];
        a.threshold.source=LabMateAlertPulseDuty;
        a.threshold.armed=(status==3);a.threshold.latched=(status==3);
        a.capture_blocked=(status==2);a.hold=(status==1);
        LabMateApp before;memcpy(&before,&a,sizeof(a));
        draw_pulse(&c,&a);assert(memcmp(&before,&a,sizeof(a))==0);
        /* Both main and STATS must use the same inverse triple footer.
         * The STATS last data baseline is y=49, clearing the y=52 rule.
         */
        assert(c.color==ColorBlack && c.boxes>=2U);
        if(view) {
            if(a.hold) {
                assert(c.boxes>=2U); /* Production pair footer is also inverse. */
                assert(contains(&c,"(UP) MAIN"));
                assert(contains(&c,"(OK) LIVE"));
                assert(!contains(&c,"vRST"));
            } else {
                assert(c.boxes>=2U);
                assert(contains(&c,"^MAIN"));
                assert(contains(&c,"vRST"));
            }
        } else assert(c.boxes>=2U);
        if(c.faults){fprintf(stderr,"PULSE pin=%u view=%u valid=%u cycles=%u duty=%u status=%u\n",pin,view,valid,ix,d,status);return 0;}
        if(view && valid && d==2)assert(contains(&c,"100.0%"));
        ++count;
    }
    return count;
}
int main(void){
    const unsigned f=frequency_test(),g=generator_test(),p=pulse_test();
    printf("UI-05D GEOMETRY: frequency=%u pwm=%u pulse=%u\n",f,g,p);
    return (f==192U && g==384U && p==2688U)?0:1;
}
