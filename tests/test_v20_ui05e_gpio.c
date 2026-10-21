/* UI-05E: source-identical draw_gpio, on-host ASCII 128x64 Canvas model.
 * No GPIO acquisition, timers, FAP SDK, physical font raster, or SD IO.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>

typedef enum { FontSecondary=0, FontPrimary=1 } Font;
typedef enum { ColorBlack=0, ColorWhite=1 } Color;
typedef struct {int x0,y0,x1,y1;} Rect;
typedef struct Canvas Canvas;
struct Canvas {
    Font font;
    Color color;
    Rect text[32];
    char strings[32][40];
    unsigned count, errors, boxes, frames, lines;
    int bx, by, bw;
};
static bool intersect(Rect a,Rect b) {
    return !(a.x1<b.x0 || b.x1<a.x0 || a.y1<b.y0 || b.y1<a.y0);
}
static void draw_text(Canvas* c,int x,int y,const char* str) {
    assert(c && str && c->count<32);
    const int width=(int)strlen(str)*(c->font==FontPrimary?8:6);
    const int height=c->font==FontPrimary?11:8;
    const Rect r={x,y-height+1,x+width-1,y};
    if(width<=0 || r.x0<0 || r.y0<0 || r.x1>127 || r.y1>63) {
        fprintf(stderr,"SCREEN OUT: %s x=%d y=%d x1=%d\n",str,x,y,r.x1);
        c->errors++;
    }
    for(unsigned i=0;i<c->count;i++)if(intersect(r,c->text[i])) {
        fprintf(stderr,"TEXT OVERLAP: '%s' '%s'\n",str,c->strings[i]);
        c->errors++;
    }
    if(c->bw>0 && x==c->bx+4 && y==c->by+8 && r.x1>=c->bx+c->bw) {
        fprintf(stderr,"BADGE OUT: %s\n",str);c->errors++;
    }
    c->text[c->count]=r;
    snprintf(c->strings[c->count],sizeof(c->strings[0]),"%s",str);
    c->count++;
}
void canvas_set_font(Canvas* c,Font f){assert(c);c->font=f;}
void canvas_set_color(Canvas* c,Color color){assert(c);c->color=color;}
void canvas_draw_str(Canvas* c,int x,int y,const char* s){draw_text(c,x,y,s);}
void canvas_draw_line(Canvas* c,int x,int y,int x2,int y2){
    assert(c);if(x<0||x>127||x2<0||x2>127||y<0||y>63||y2<0||y2>63)c->errors++;
    c->lines++;
}
void canvas_draw_box(Canvas* c,int x,int y,int w,int h){
    assert(c);if(x<0||y<0||w<=0||h<=0||x+w>128||y+h>64)c->errors++;
    c->boxes++;
}
void canvas_draw_frame(Canvas* c,int x,int y,int w,int h){
    assert(c);if(x<0||y<0||w<=0||h<=0||x+w>128||y+h>64)c->errors++;
    c->frames++;
}
void ui_draw_header(Canvas* c,const char* t){
    canvas_set_font(c,FontPrimary);canvas_draw_str(c,2,10,t);canvas_draw_line(c,0,13,127,13);
}
void ui_badge(Canvas* c,uint8_t x,uint8_t y,uint8_t w,const char* t,bool filled){
    assert(c);if(filled){canvas_draw_box(c,x,y,w,11);canvas_set_color(c,ColorWhite);}
    else canvas_draw_frame(c,x,y,w,11);
    c->bx=x;c->by=y;c->bw=w;
    canvas_set_font(c,FontSecondary);canvas_draw_str(c,x+4,y+8,t);
    if(filled)canvas_set_color(c,ColorBlack);
}
void ui_key(Canvas* c,uint8_t x,const char* key,const char* action){
    char s[24];int n=snprintf(s,sizeof(s),"(%s) %s",key,action);
    if(n>10)n=snprintf(s,sizeof(s),"(%s)%s",key,action);
    assert(n>0&&n<=10);
    canvas_set_font(c,FontSecondary);canvas_draw_str(c,x,61,s);
}
static const char* const labmate_gpio_names[]={"PC0","PC1","PC3","PB2","PB3","PA4","PA6","PA7"};
typedef struct {
    uint8_t gpio_index;
    uint32_t edges;
    bool monitor_release_fault,monitor_blocked,hold,gpio_state,generator_running;
} LabMateApp;
#include "draw_gpio.inc"
static bool contains(const Canvas* c,const char* s) {
    for(unsigned i=0;i<c->count;i++)if(!strcmp(c->strings[i],s))return true;
    return false;
}
static void format_expected(char out[32],uint32_t edges){
    if(edges>=1000000U)snprintf(out,32,"%lu.%luM",(unsigned long)(edges/1000000U),(unsigned long)((edges%1000000U)/100000U));
    else if(edges>=10000U)snprintf(out,32,"%lu.%luk",(unsigned long)(edges/1000U),(unsigned long)((edges%1000U)/100U));
    else snprintf(out,32,"%lu",(unsigned long)edges);
}
int main(void) {
    const uint32_t edges[]={0,1,9,10,999,9999,10000,10001,99999,100000,999999,1000000,1000001,10000000,UINT32_MAX};
    unsigned count=0;
    for(unsigned pin=0;pin<8;pin++)for(unsigned index=0;index<15;index++)
    for(unsigned level=0;level<2;level++)for(unsigned status=0;status<5;status++)
    for(unsigned pwm=0;pwm<2;pwm++) {
        LabMateApp a={0};Canvas c={0};char formatted[32];
        a.gpio_index=(uint8_t)pin;a.edges=edges[index];a.gpio_state=level!=0;
        a.monitor_release_fault=status==3||status==4;
        a.monitor_blocked=status==2||status==4;
        a.hold=status==1;
        a.generator_running=pwm!=0;
        LabMateApp original;memcpy(&original,&a,sizeof(a));
        draw_gpio(&c,&a);
        assert(memcmp(&a,&original,sizeof(a))==0);
        format_expected(formatted,a.edges);
        assert(contains(&c,labmate_gpio_names[pin]));
        assert(contains(&c,level?"HIGH":"LOW"));
        assert(contains(&c,formatted));
        assert(contains(&c,pwm?"PA7 BUSY":"POLL"));
        assert(contains(&c,a.monitor_release_fault?"ERR":a.monitor_blocked?"BUSY":a.hold?"HOLD":"LIVE"));
        assert(contains(&c,a.hold?"(OK) LIVE":"(OK) HOLD"));
        assert(contains(&c,"(<>) PIN"));
        assert(c.color==ColorBlack);
        assert(c.boxes>=((level!=0)?1U:0U));
        if(c.errors){fprintf(stderr,"UI05E ERROR pin=%u edgeidx=%u level=%u status=%u pwm=%u faults=%u\n",pin,index,level,status,pwm,c.errors);return 1;}
        count++;
    }
    printf("UI-05E GPIO host PASS: %u source/level/status/PWM combinations\n",count);
    return count==2400?0:1;
}
