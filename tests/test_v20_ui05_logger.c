/* UI-05: real Logger renderer body under read-only 128x64 Canvas host model.
 * No GPIO/SD access or device emulation is claimed.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>

typedef enum {FontSecondary=0, FontPrimary=1} Font;
typedef enum {AlignRight=0, AlignBottom=0} Align;
typedef struct Canvas Canvas;
typedef struct {int32_t x0,y0,x1,y1;} Rect;
struct Canvas {
    Font font;
    Rect text_bounds[32];
    char labels[32][48];
    unsigned count, faults;
    int badge_x, badge_y, badge_w;
};
static bool intersects(Rect a, Rect b) {
    return !(a.x1<b.x0 || b.x1<a.x0 || a.y1<b.y0 || b.y1<a.y0);
}
static void host_text(Canvas* c,int32_t x,int32_t y,const char* s) {
    assert(c && s && c->count<32);
    const int w=(int)strlen(s)*(c->font==FontPrimary?8:6);
    const int h=c->font==FontPrimary?11:8;
    const Rect rect={x,y-h+1,x+w-1,y};
    if(!w||rect.x0<0||rect.y0<0||rect.x1>=128||rect.y1>=64){
        fprintf(stderr,"TEXT OUTSIDE 128x64: '%s' at x=%d y=%d right=%d\n",s,x,y,rect.x1);
        ++c->faults;
    }
    for(unsigned j=0;j<c->count;j++)if(intersects(rect,c->text_bounds[j])) {
        fprintf(stderr,"TEXT COLLISION: '%s' with '%s'\n",s,c->labels[j]);
        ++c->faults;
    }
    if(c->badge_w && x==c->badge_x+4 && y==c->badge_y+8 && rect.x1>=c->badge_x+c->badge_w){
        fprintf(stderr,"BADGE TEXT CLIP: '%s'\n",s); ++c->faults;
    }
    c->text_bounds[c->count]=rect;
    snprintf(c->labels[c->count],sizeof(c->labels[0]),"%s",s);
    ++c->count;
}
void canvas_set_font(Canvas* c,Font f){assert(c);c->font=f;}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* s){host_text(c,x,y,s);}
void canvas_draw_str_aligned(Canvas* c,int32_t x,int32_t y,Align h,Align v,const char* s){
    assert(h==AlignRight && v==AlignBottom);
    host_text(c,x-(int32_t)strlen(s)*(c->font==FontPrimary?8:6),y,s);
}
void canvas_draw_line(Canvas* c,int32_t x0,int32_t y0,int32_t x1,int32_t y1){
    assert(c);if(x0<0||x0>=128||x1<0||x1>=128||y0<0||y0>=64||y1<0||y1>=64)++c->faults;
}
void ui_draw_header(Canvas* c,const char* s){
    canvas_set_font(c,FontPrimary);canvas_draw_str(c,2,10,s);canvas_draw_line(c,0,13,127,13);
}
void ui_badge(Canvas* c,uint8_t x,uint8_t y,uint8_t w,const char* s,bool filled){
    (void)filled;
    if((int)x+(int)w>128||y+11>64)++c->faults;
    c->badge_x=x;c->badge_y=y;c->badge_w=w;
    canvas_set_font(c,FontSecondary);canvas_draw_str(c,x+4,y+8,s);
}
void ui_footer_pair(Canvas* c,const char* lk,const char* la,const char* rk,const char* ra){
    char label[24];int n=snprintf(label,sizeof(label),"(%s) %s",lk,la);
    if(n>10)n=snprintf(label,sizeof(label),"(%s)%s",lk,la);
    assert(n>0&&n<=10);
    canvas_draw_line(c,0,52,127,52);canvas_set_font(c,FontSecondary);
    canvas_draw_str(c,2,61,label);
    n=snprintf(label,sizeof(label),"(%s) %s",rk,ra);
    if(n>10)n=snprintf(label,sizeof(label),"(%s)%s",rk,ra);
    assert(n>0&&n<=10);canvas_draw_str(c,66,61,label);
}
typedef enum {LoggerFrequencyLow=0,LoggerFrequencyHigh=1,LoggerPulse=2} LabMateLoggerSource;
typedef struct {
    LabMateLoggerSource logger_source;
    bool pulse_period_valid,frequency_valid,logger_busy,logger_busy_stopping;
    bool capture_blocked,logger_error,logger_recording;
    uint32_t pulse_period_cycles, pulse_duty_permille, frequency_millihz,logger_rows;
    char logger_path[80];
} LabMateApp;
/* Deterministic host-only time model. Values only affect display formatting. */
uint64_t pulse_cycles_to_us(uint32_t cycles){return (uint64_t)cycles;}
#include "logger_body.inc"

static unsigned run(void){
    unsigned cases=0,invalid=0;
    for(unsigned source=0;source<3;source++)
    for(unsigned valid=0;valid<2;valid++)
    for(unsigned state=0;state<10;state++)
    for(unsigned limit=0;limit<2;limit++){
        LabMateApp app={0}; Canvas canvas={0};
        app.logger_source=(LabMateLoggerSource)source;
        app.frequency_valid=(valid!=0);app.pulse_period_valid=(valid!=0);
        app.frequency_millihz=limit?UINT32_MAX:1000000U;
        app.pulse_period_cycles=limit?UINT32_MAX:1000U;
        app.pulse_duty_permille=limit?1000U:500U;
        app.logger_rows=limit?UINT32_MAX:3U;
        if(state==1)app.logger_busy=true;
        if(state==2){app.logger_busy=true;app.logger_busy_stopping=true;}
        if(state==3)app.capture_blocked=true;
        if(state==4)app.logger_error=true;
        if(state==5)app.logger_recording=true;
        if(state==6)strcpy(app.logger_path,"/ext/apps_data/labmate/log_1.csv");
        if(state==7){app.logger_busy=true;app.logger_recording=true;}
        if(state==8){app.capture_blocked=true;app.logger_error=true;}
        if(state==9){app.logger_error=true;app.logger_recording=true;}
        const LabMateApp before=app;
        draw_logger(&canvas,&app);
        assert(memcmp(&before,&app,sizeof(app))==0);
        if(canvas.faults){
            fprintf(stderr,"UI-05 LOGGER failure: source=%u valid=%u state=%u extreme=%u (%u faults)\n",
                    source,valid,state,limit,canvas.faults);
            ++invalid;
        }
        ++cases;
    }
    printf("UI-05 Logger host: %u source/state fixtures, %u failing fixtures\n",cases,invalid);
    return invalid;
}
int main(void){return run()?1:0;}
