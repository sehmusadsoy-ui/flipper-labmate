/* UI-05C: original Counter drawing function, real pure counter formatter. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include "labmate_threshold.h"
#include "labmate_counter_math.h"
typedef enum {FontSecondary=0,FontPrimary=1} Font;
typedef enum {AlignRight=0,AlignCenter=1} Align;
typedef enum {AlignBottom=0} VerticalAlign;
typedef struct {int x0,y0,x1,y1;} Rect;
typedef struct Canvas Canvas;
struct Canvas { Font font; Rect texts[32]; char strings[32][32]; unsigned n,errors; int bx,by,bw;};
static bool overlap(Rect a,Rect b) {return !(a.x1<b.x0||b.x1<a.x0||a.y1<b.y0||b.y1<a.y0);}
static void canvas_text(Canvas* c,int x,int y,const char* s){
    assert(c&&s&&c->n<32);
    int width=(int)strlen(s)*(c->font==FontPrimary?8:6);
    int height=c->font==FontPrimary?11:8;
    Rect rc={x,y-height+1,x+width-1,y};
    if(width<1||rc.x0<0||rc.y0<0||rc.x1>=128||rc.y1>=64){
        fprintf(stderr,"OUT OF LCD: %s x=%d y=%d\n",s,x,y); c->errors++;
    }
    if(c->bw && x==c->bx+4 && y==c->by+8 && rc.x1>=c->bx+c->bw){
        fprintf(stderr,"BADGE CLIP: %s\n",s);c->errors++;
    }
    for(unsigned i=0;i<c->n;i++)if(overlap(rc,c->texts[i])){
        fprintf(stderr,"OVERLAP: %s and %s\n",s,c->strings[i]);c->errors++;
    }
    c->texts[c->n]=rc;snprintf(c->strings[c->n],sizeof(c->strings[0]),"%s",s);c->n++;
}
void canvas_set_font(Canvas* c,Font f){c->font=f;}
void canvas_draw_str(Canvas* c,int x,int y,const char* s){canvas_text(c,x,y,s);}
void canvas_draw_str_aligned(Canvas* c,int x,int y,Align a,VerticalAlign v,const char* s){
    assert(v==AlignBottom);
    int w=(int)strlen(s)*(c->font==FontPrimary?8:6);
    canvas_text(c,a==AlignRight?x-w:x-w/2,y,s);
}
void canvas_draw_line(Canvas* c,int a,int b,int d,int e){
    if(a<0||d<0||b<0||e<0||a>=128||d>=128||b>=64||e>=64)c->errors++;
}
void ui_draw_header(Canvas* c,const char* t){canvas_set_font(c,FontPrimary);canvas_draw_str(c,2,10,t);canvas_draw_line(c,0,13,127,13);}
void ui_badge(Canvas* c,uint8_t x,uint8_t y,uint8_t w,const char* s,bool selected){
    (void)selected;if(x+w>128||y+11>64)c->errors++;c->bx=x;c->by=y;c->bw=w;
    canvas_set_font(c,FontSecondary);canvas_draw_str(c,x+4,y+8,s);
}
void ui_footer_pair(Canvas* c,const char* lk,const char* la,const char* rk,const char* ra){
    char label[32];int n=snprintf(label,sizeof(label),"(%s) %s",lk,la);
    if(n>10)n=snprintf(label,sizeof(label),"(%s)%s",lk,la);
    assert(n>=1&&n<=10);canvas_draw_line(c,0,52,127,52);
    canvas_set_font(c,FontSecondary);canvas_draw_str(c,2,61,label);
    n=snprintf(label,sizeof(label),"(%s) %s",rk,ra);
    if(n>10)n=snprintf(label,sizeof(label),"(%s)%s",rk,ra);
    assert(n>=1&&n<=10);canvas_draw_str(c,66,61,label);
}
typedef struct {
    uint64_t counter_total,counter_elapsed_ticks;
    uint32_t counter_elapsed_seconds;
    bool counter_active,capture_blocked;
    LabMateThreshold threshold;
} LabMateApp;
#include "draw_counter_body.inc"
static bool contains(Canvas* c,const char* s){for(unsigned i=0;i<c->n;i++)if(!strcmp(s,c->strings[i]))return true;return false;}
int main(void){
    const uint64_t counts[]={0,1,9,10,999,9999999,10000000,99999999999ULL,100000000000ULL,18446744073709551615ULL};
    const uint32_t seconds[]={0,59,60,3599,3600,359999,360000,UINT32_MAX};
    unsigned cases=0,failed=0;
    for(unsigned i=0;i<sizeof(counts)/sizeof(counts[0]);i++)
    for(unsigned j=0;j<sizeof(seconds)/sizeof(seconds[0]);j++)
    for(unsigned scenario=0;scenario<8;scenario++){
        LabMateApp a={0};Canvas c={0};
        a.counter_total=counts[i];a.counter_elapsed_seconds=seconds[j];
        a.counter_elapsed_ticks=counts[i]?1:0;
        a.counter_active=(scenario&1U)!=0;
        a.capture_blocked=(scenario&2U)!=0;
        a.threshold.source=LabMateAlertCounter;
        a.threshold.armed=(scenario&4U)!=0;
        a.threshold.latched=(scenario&4U)!=0;
        LabMateApp before;memcpy(&before,&a,sizeof(a));
        draw_counter(&c,&a);
        assert(memcmp(&before,&a,sizeof(a))==0);
        if(i==9)assert(contains(&c,"18446744073709551615"));
        if(c.errors){fprintf(stderr,"COUNTER ERROR value=%llu seconds=%u scenario=%u\n",(unsigned long long)counts[i],seconds[j],scenario);failed++;}
        cases++;
    }
    printf("UI-05C Counter host: %u cases, %u failures\n",cases,failed);
    return failed?1:0;
}
