#include "labmate_ui_primitives.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* Compile real shared Canvas primitives under strict host GCC warnings. */
struct Canvas {
    Font font;
    unsigned labels, lines;
    char text[4][32];
};
void canvas_set_font(Canvas* c, Font f) { assert(c); c->font=f; }
void canvas_set_color(Canvas* c, Color x) { (void)x; assert(c); }
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* s) {
    assert(c && s && x>=0 && y>=0 && y<64);
    assert((size_t)x + strlen(s) * 6U <= 128U);
    assert(c->labels < 4U);
    (void)snprintf(c->text[c->labels++],32,"%s",s);
}
void canvas_draw_line(Canvas* c,int32_t a,int32_t b,int32_t d,int32_t e) {
    assert(c && a>=0 && a<128 && d>=0 && d<128 && b>=0 && e<64);
    ++c->lines;
}
void canvas_draw_box(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h) {
    (void)x; (void)y; (void)w; (void)h; assert(c);
}
void canvas_draw_frame(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h) {
    (void)x; (void)y; (void)w; (void)h; assert(c);
}
void canvas_draw_dot(Canvas* c,int32_t x,int32_t y) {
    (void)x; (void)y; assert(c);
}
static void check(const char* a,const char* action,const char* b,const char* other) {
    struct Canvas canvas={0};
    ui_footer_pair(&canvas,a,action,b,other);
    assert(canvas.lines==1U && canvas.labels==2U);
    assert(canvas.text[0][0]=='(' && canvas.text[1][0]=='(');
    assert(strchr(canvas.text[0],')') && strchr(canvas.text[1],')'));
    assert(strlen(canvas.text[0])<=10U && strlen(canvas.text[1])<=10U);
}
int main(void) {
    check("OK","SAVE","BACK","NO");
    check("LR","SOURCE","OK","ARM");
    check("DOWN","ACK","OK","OFF");
    check("OK","DELETE","BACK","NO");
    check("LR","MODE","OK","DELETE");
    check("DOWN","MORE","OK","START");
    check("OK","STOP","BACK","EXIT");
    check("OK","RESUME","UP","RESET");
    check("LR","FREQ","OK","RUN");
    check("LR","SOURCE","OK","RECORD");
    check("OK","START","BACK","EXIT");
    struct Canvas c={0};
    ui_key(&c,70,"OK","OPEN");
    assert(c.labels==1U && !strcmp(c.text[0],"(OK) OPEN"));
    c=(struct Canvas){0};
    ui_key(&c,2,"<>","PIN");
    assert(c.labels==1U && !strcmp(c.text[0],"(<>) PIN"));
    puts("v1.9 shared LabMate key parentheses, glyph bounds, stable meaning PASS");
    return 0;
}
