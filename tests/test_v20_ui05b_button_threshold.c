/* UI-05B: real draw_button/draw_alerts bodies, passive host Canvas.
 * The launcher extracts production functions exactly; this file supplies
 * only GUI/App type stubs. Measured physical accuracy is not covered.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "labmate_threshold.h"

typedef enum { FontSecondary=0, FontPrimary=1 } Font;
typedef enum { AlignRight=0, AlignBottom=0 } Align;
typedef struct {int32_t x0,y0,x1,y1;} Rect;
typedef struct Canvas Canvas;
struct Canvas {
    Font font;
    Rect labels[32];
    char strings[32][48];
    unsigned n, faults;
    int32_t badge_x,badge_y,badge_w;
};
static bool intersect(Rect a,Rect b) {
    return !(a.x1 < b.x0 || b.x1 < a.x0 || a.y1 < b.y0 || b.y1 < a.y0);
}
static void text(Canvas* c,int32_t x,int32_t y,const char* s) {
    assert(c && s && c->n<32U);
    const int32_t width=(int32_t)strlen(s)*(c->font==FontPrimary?8:6);
    const int32_t h=c->font==FontPrimary?11:8;
    const Rect a={x,y-h+1,x+width-1,y};
    if(width<1 || a.x0<0 || a.y0<0 || a.x1>127 || a.y1>63) {
        fprintf(stderr,"LCD BOUNDS '%s' at (%ld,%ld), right=%ld\n",
                s,(long)x,(long)y,(long)a.x1); ++c->faults;
    }
    for(unsigned i=0;i<c->n;i++)if(intersect(a,c->labels[i])){
        fprintf(stderr,"LCD OVERLAP '%s' and '%s'\n",s,c->strings[i]);
        ++c->faults;
    }
    if(c->badge_w>0 && x==c->badge_x+4 && y==c->badge_y+8 &&
       a.x1 >= c->badge_x+c->badge_w) {
        fprintf(stderr,"BADGE OVERFLOW '%s'\n",s); ++c->faults;
    }
    c->labels[c->n]=a;
    (void)snprintf(c->strings[c->n],sizeof(c->strings[0]),"%s",s);
    ++c->n;
}
void canvas_set_font(Canvas* c,Font f) {assert(c);c->font=f;}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* s){text(c,x,y,s);}
void canvas_draw_str_aligned(Canvas* c,int32_t x,int32_t y,Align a,Align b,const char* s){
    assert(a==AlignRight && b==AlignBottom);
    const int32_t w=(int32_t)strlen(s)*(c->font==FontPrimary?8:6);
    text(c,x-w,y,s);
}
void canvas_draw_line(Canvas* c,int32_t x0,int32_t y0,int32_t x1,int32_t y1){
    assert(c);
    if(x0<0 || x0>127 || x1<0 || x1>127 || y0<0 || y0>63 || y1<0 || y1>63)++c->faults;
}
void canvas_draw_frame(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h){
    assert(c);
    if(x<0 || y<0 || w<1 || h<1 || x+w>128 || y+h>64)++c->faults;
}
void ui_draw_header(Canvas* c,const char* name) {
    canvas_set_font(c,FontPrimary);canvas_draw_str(c,2,10,name);
    canvas_draw_line(c,0,13,127,13);
}
void ui_badge(Canvas* c,uint8_t x,uint8_t y,uint8_t w,const char* value,bool filled){
    (void)filled; if((unsigned)x+w>128U||(unsigned)y+11U>64U)++c->faults;
    c->badge_x=x;c->badge_y=y;c->badge_w=w;
    canvas_set_font(c,FontSecondary);canvas_draw_str(c,x+4,y+8,value);
}
void ui_footer_pair(Canvas* c,const char* a,const char* b,const char* d,const char* e){
    char label[32];int n=snprintf(label,sizeof(label),"(%s) %s",a,b);
    if(n>10)n=snprintf(label,sizeof(label),"(%s)%s",a,b);
    assert(n>=1&&n<=10);
    canvas_draw_line(c,0,52,127,52);
    canvas_set_font(c,FontSecondary);canvas_draw_str(c,2,61,label);
    n=snprintf(label,sizeof(label),"(%s) %s",d,e);
    if(n>10)n=snprintf(label,sizeof(label),"(%s)%s",d,e);
    assert(n>=1&&n<=10);canvas_draw_str(c,66,61,label);
}
typedef struct {
    bool pending,stable_level;
    uint32_t presses,releases;
    uint16_t last_bounce_edges;
} LabMateButtonStats;
typedef struct {
    LabMateThreshold threshold;
    bool capture_blocked,button_active,button_details_view,button_session_started;
    uint8_t button_quiet_ms;
    LabMateButtonStats button_stats;
    uint32_t button_bounce_us,button_settle_ms,button_hold_ms;
} LabMateApp;

#include "draw_button_body.inc"
#include "draw_alerts_body.inc"

static bool has(const Canvas* c,const char* s){
    for(unsigned i=0;i<c->n;i++)if(!strcmp(s,c->strings[i]))return true;
    return false;
}
static unsigned check_button(void) {
    const uint8_t quiet[]={5,10,20,50}; /* actual hardware control choices */
    unsigned cases=0;
    for(unsigned q=0;q<4;q++)
    for(unsigned details=0;details<2;details++)
    for(unsigned status=0;status<3;status++)
    for(unsigned big=0;big<2;big++)
    for(unsigned pending=0;pending<2;pending++) {
        LabMateApp a={0};Canvas c={0};
        a.button_quiet_ms=quiet[q];a.button_details_view=(details!=0);
        a.button_active=status==1;
        a.capture_blocked=status==2;
        a.button_session_started=true;
        a.button_stats.pending=(pending!=0);
        a.button_stats.stable_level=(pending==0);
        a.button_stats.presses=big?UINT32_MAX:12U;
        a.button_stats.releases=big?UINT32_MAX:10U;
        a.button_stats.last_bounce_edges=big?UINT16_MAX:2U;
        a.button_bounce_us=big?UINT32_MAX:1000U;
        a.button_settle_ms=big?UINT32_MAX:12U;
        a.button_hold_ms=big?UINT32_MAX:50U;
        a.threshold.source=LabMateAlertButtonSettle;
        a.threshold.armed=(status==2);a.threshold.latched=(status==2);
        LabMateApp before;
        memcpy(&before,&a,sizeof(a));
        draw_button(&c,&a);
        assert(memcmp(&a,&before,sizeof(a))==0);
        if(c.faults) {
            fprintf(stderr,"BUTTON case q=%u details=%u status=%u big=%u pending=%u\n",
                   q,details,status,big,pending);
            return 0;
        }
        assert(has(&c,details?"(DOWN)MAIN":"(DOWN)MORE"));
        cases++;
    }
    return cases;
}
static unsigned check_threshold(void) {
    /* Real configured maxima from src/labmate_threshold.c, not fake UINT32_MAX limits. */
    const uint32_t maximum[]={50000U,95U,1000000U,1000U};
    unsigned cases=0;
    for(unsigned source=0;source<LabMateAlertSourceCount;source++)
    for(unsigned arm=0;arm<3;arm++)
    for(unsigned sample=0;sample<2;sample++)
    for(unsigned big=0;big<2;big++){
        LabMateApp a={0};Canvas c={0};
        a.threshold.source=(LabMateAlertSource)source;
        a.threshold.limit=big?maximum[source]:100U;
        a.threshold.armed=arm!=0;
        a.threshold.latched=arm==2;
        a.threshold.has_sample=sample!=0;
        a.threshold.active=sample!=0;
        LabMateApp before;
        memcpy(&before,&a,sizeof(a));
        draw_alerts(&c,&a);
        assert(memcmp(&a,&before,sizeof(a))==0);
        if(c.faults) {
            fprintf(stderr,"THRESHOLD case source=%u arm=%u sample=%u big=%u\n",
                   source,arm,sample,big);
            return 0;
        }
        cases++;
    }
    return cases;
}
int main(void) {
    const unsigned b=check_button();
    const unsigned t=check_threshold();
    if(b!=96U || t!=48U) return 1;
    printf("UI-05B Button/Threshold host PASS: %u + %u states\n",b,t);
    return 0;
}
