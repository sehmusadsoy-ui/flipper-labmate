/* Exact draw_menu function is extracted unchanged into menu.inc by runner.
 * Fake Canvas validates 128x64 glyph bounds for EVERY selectable root and
 * tool row. It cannot replace visual physical screen acceptance.
 */
#include "labmate_navigation.h"
#include "labmate_menu_grid.h"
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef enum {FontSecondary=0,FontPrimary=1} Font;
typedef enum {ColorBlack=0,ColorWhite=1} Color;
typedef struct {
    Font font;
    Color color;
    unsigned text_count;
    struct {int x,y,w,h;} text[20];
} Canvas;
typedef struct {
    bool menu_in_group;
    uint8_t menu_group;
    uint8_t selected;
} LabMateApp;
#define LABMATE_VERSION_TEXT "v2.0DEV"

static void canvas_set_font(Canvas* c, Font f) {assert(c);c->font=f;}
static void canvas_set_color(Canvas* c,Color v) {assert(c);c->color=v;}
static void canvas_draw_box(Canvas* c,int x,int y,int w,int h) {
    assert(c && x>=0 && y>=0 && w>0 && h>0 && x+w<=128 && y+h<=64);
}
static void canvas_draw_frame(Canvas* c,int x,int y,int w,int h) {
    canvas_draw_box(c,x,y,w,h);
}
static void canvas_draw_line(Canvas* c,int x,int y,int x2,int y2) {
    assert(c && x>=0 && y>=0 && x2>=0 && y2>=0 &&
           x<128 && x2<128 && y<64 && y2<64);
}
static void canvas_draw_str(Canvas* c,int x,int y,const char* str) {
    assert(c && str && *str && c->text_count<20);
    const int w=(int)strlen(str)*(c->font==FontPrimary?8:6);
    const int h=c->font==FontPrimary?11:8;
    assert(x>=0 && y>=h-1 && x+w<=128 && y<64);
    for(const unsigned char* p=(const unsigned char*)str;*p;p++)
        assert(*p>=32 && *p<=126);
    for(unsigned i=0;i<c->text_count;i++) {
        const int a=c->text[i].x,b=c->text[i].y;
        const int aw=c->text[i].w,ah=c->text[i].h;
        assert(x>=a+aw || a>=x+w || y-h+1>b ||
               b-ah+1>y);
    }
    c->text[c->text_count].x=x;
    c->text[c->text_count].y=y;
    c->text[c->text_count].w=w;
    c->text[c->text_count].h=h;
    c->text_count++;
}
static void ui_draw_header(Canvas* c,const char* title) {
    canvas_set_font(c,FontPrimary);
    canvas_draw_str(c,2,10,title);
    canvas_draw_line(c,0,13,127,13);
}
static void ui_badge(Canvas* c,uint8_t x,uint8_t y,uint8_t w,const char* t,bool filled) {
    (void)filled;
    canvas_draw_frame(c,x,y,w,11);
    canvas_set_font(c,FontSecondary);
    canvas_draw_str(c,x+4,y+8,t);
}
static void ui_draw_menu_icon(Canvas* c,uint8_t tool,uint8_t x,uint8_t y) {
    assert(tool<LabMateToolCount);
    canvas_draw_frame(c,x,y,13,12);
}
static void ui_footer_pair(Canvas* c,const char* lk,const char* la,
                           const char* rk,const char* ra) {
    char l[24],r[24];
    int n=snprintf(l,sizeof(l),"(%s) %s",lk,la);
    if(n>10) n=snprintf(l,sizeof(l),"(%s)%s",lk,la);
    assert(n>0 && n<=10);
    n=snprintf(r,sizeof(r),"(%s) %s",rk,ra);
    if(n>10) n=snprintf(r,sizeof(r),"(%s)%s",rk,ra);
    assert(n>0 && n<=10);
    canvas_draw_line(c,0,52,127,52);
    canvas_set_font(c,FontSecondary);
    canvas_draw_str(c,2,61,l);
    canvas_draw_str(c,66,61,r);
}
#include "menu.inc"

int main(void) {
    unsigned cases=0;
    for(unsigned g=0;g<LabMateGroupCount;g++) {
        Canvas c={0};
        LabMateApp a={.menu_in_group=false,.selected=g};
        draw_menu(&c,&a);
        assert(c.color==ColorBlack && c.text_count==9U);
        cases++;
    }
    for(unsigned g=0;g<LabMateGroupCount;g++) {
        for(unsigned selected=0;selected<labmate_nav_group_size(g);selected++) {
            Canvas c={0};
            LabMateApp a={.menu_in_group=true,.menu_group=g,.selected=selected};
            draw_menu(&c,&a);
            assert(c.color==ColorBlack);
            cases++;
        }
    }
    printf("ULTIMATE ROOT+SUBMENU RENDERER PASS: %u exhaustive selections, 128x64\n",cases);
    return 0;
}
