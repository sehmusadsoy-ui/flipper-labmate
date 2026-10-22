/* UI-04 Profiles / Log History display geometry and read-only behavior.
 * Production function bodies are extracted by the accompanying runner.
 * Canvas is host-only. 128x64 glyph widths model earlier GUI tests.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include "labmate_ui_layout.h"

typedef enum {FontSecondary = 0, FontPrimary = 1} Font;
typedef enum {ColorBlack = 0, ColorWhite = 1} Color;
typedef enum {AlignRight = 0} Align;
typedef enum {AlignBottom = 0} AlignVertical;
typedef struct Canvas Canvas;
typedef struct {int x0,y0,x1,y1;} Rect;
struct Canvas {
    Font font;
    Rect texts[32];
    char labels[32][64];
    unsigned count, faults;
    int badge_x, badge_y, badge_w;
};
static bool intersects(Rect a,Rect b) {
    return !(a.x1<b.x0 || b.x1<a.x0 || a.y1<b.y0 || b.y1<a.y0);
}
static void add_text(Canvas* c,int x,int y,const char* s) {
    assert(c && s && c->count<32);
    const int width=(int)strlen(s)*(c->font==FontPrimary?8:6);
    const int height=c->font==FontPrimary?11:8;
    Rect r={x,y-height+1,x+width-1,y};
    if(width<1 || r.x0<0 || r.x1>=128 || r.y0<0 || r.y1>=64) {
        fprintf(stderr,"BOUNDS '%s' x=%d y=%d right=%d\n",s,x,y,r.x1);
        ++c->faults;
    }
    for(unsigned i=0;i<c->count;i++) if(intersects(r,c->texts[i])) {
        fprintf(stderr,"OVERLAP '%s' and '%s'\n",s,c->labels[i]);
        ++c->faults;
    }
    if(c->badge_w && y==c->badge_y+8 && x==c->badge_x+4 &&
       r.x1>=c->badge_x+c->badge_w) {
        fprintf(stderr,"BADGE CLIP '%s'\n",s); ++c->faults;
    }
    c->texts[c->count]=r;
    (void)snprintf(c->labels[c->count],64,"%s",s);
    c->count++;
}
void canvas_set_font(Canvas* c,Font f){assert(c);c->font=f;}
void canvas_set_color(Canvas* c,Color v){assert(c);(void)v;}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* s){add_text(c,x,y,s);}
void canvas_draw_str_aligned(Canvas* c,int32_t x,int32_t y,Align a,AlignVertical v,const char* s){
    assert(a==AlignRight && v==AlignBottom);
    add_text(c,x-(int)strlen(s)*(c->font==FontPrimary?8:6),y,s);
}
void canvas_draw_line(Canvas* c,int32_t x0,int32_t y0,int32_t x1,int32_t y1) {
    assert(c);
    if(x0<0||x0>=128||x1<0||x1>=128||y0<0||y0>=64||y1<0||y1>=64)++c->faults;
}
void canvas_draw_box(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h){
    assert(c);if(x<0||y<0||w<=0||h<=0||x+w>128||y+h>64)++c->faults;
}
void ui_draw_header(Canvas* c,const char* t){
    canvas_set_font(c,FontPrimary);canvas_draw_str(c,2,10,t);canvas_draw_line(c,0,13,127,13);
}
void ui_badge(Canvas* c,uint8_t x,uint8_t y,uint8_t w,const char* s,bool fill){
    (void)fill; if((int)x+w>128||(int)y+11>64)++c->faults;
    c->badge_x=x;c->badge_y=y;c->badge_w=w;
    canvas_set_font(c,FontSecondary);canvas_draw_str(c,x+4,y+8,s);
}
void ui_footer_pair(Canvas* c,const char* lk,const char* la,const char* rk,const char* ra){
    char a[32],b[32];
    int n=snprintf(a,sizeof(a),"(%s) %s",lk,la);
    if(n>10)n=snprintf(a,sizeof(a),"(%s)%s",lk,la);
    assert(n>0 && n<=10);
    n=snprintf(b,sizeof(b),"(%s) %s",rk,ra);
    if(n>10)n=snprintf(b,sizeof(b),"(%s)%s",rk,ra);
    assert(n>0 && n<=10);
    canvas_draw_line(c,0,52,127,52);
    canvas_set_font(c,FontSecondary);
    canvas_draw_str(c,2,61,a);
    canvas_draw_str(c,66,61,b);
}

typedef struct {bool present;uint8_t frequency_pin,generator_index;} LabMateProfile;
#define LABMATE_PROFILE_SLOT_COUNT 3U
typedef struct {LabMateProfile slots[LABMATE_PROFILE_SLOT_COUNT];} LabMateProfiles;
typedef enum {LabMateProfileIoOk,LabMateProfileIoEmpty,LabMateProfileIoCorrupt,LabMateProfileIoError} LabMateProfileIoResult;
typedef enum {LabMateCaptureNone=0,LabMateCaptureBusy=1} LabMateCaptureOwner;
#define LOGGER_HISTORY_LIMIT 32U
const uint32_t labmate_generator_frequencies[]={1,2,5,10,20,50,100,200,500,1000,2000,5000,10000,20000,50000};
typedef struct {
    uint8_t profile_action,profile_selected,profile_notice;
    bool generator_running,logger_recording,profile_busy,profile_confirm;
    LabMateCaptureOwner capture_owner;
    LabMateProfileIoResult profile_io;
    LabMateProfiles profiles;
    uint16_t history_ids[LOGGER_HISTORY_LIMIT];
    uint8_t history_count,history_selected,history_delete_notice,history_mode;
    bool history_busy,history_error,history_delete_confirm,history_delete_mode,history_loading;
    uint32_t history_rows,history_last_ms;
} LabMateApp;
