/* Source-linked geometry gate for the shared E11 pixel header and keys.
 * Tests the ACTUAL production inline functions, not a copied implementation.
 * The Canvas mock uses conservative 6px FontSecondary ASCII glyphs.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "labmate_pixel_ui.h"
#include "labmate_comm_ui.h"

struct Canvas {
    Font font;
    unsigned faults;
    unsigned text_count;
    unsigned key_count;
    int16_t title_right;
    int16_t status_left;
    int16_t status_right;
    int16_t last_chip_y;
    bool chip_drawn;
};

void canvas_set_font(Canvas* c, Font f) { c->font=f; }
uint16_t canvas_string_width(Canvas* c, const char* s) {
    return (uint16_t)(strlen(s) * (c->font==FontSecondary ? 6U : 8U));
}
void canvas_set_color(Canvas* c, Color color) { (void)c; (void)color; }
void canvas_draw_rbox(Canvas* c, int32_t x,int32_t y,int32_t w,int32_t h,int32_t r) {
    (void)h;(void)r;
    if(x<0 || x+w>128 || y!=0) c->faults++;
    c->status_left=(int16_t)x;
    c->status_right=(int16_t)(x+w-1);
    c->last_chip_y=(int16_t)y;
    c->chip_drawn=true;
}
void canvas_draw_rframe(Canvas* c, int32_t x,int32_t y,int32_t w,int32_t h,int32_t r) {
    canvas_draw_rbox(c,x,y,w,h,r);
}
void canvas_draw_str(Canvas* c, int32_t x,int32_t y,const char* s) {
    const int right=x+(int)canvas_string_width(c,s)-1;
    if(x<0||right>=128||y<7||y>=64) c->faults++;
    c->text_count++;
}
void ui_kit_back_title(Canvas* c, const char* title,
                       const char* short_title, const char* pin) {
    (void)short_title;(void)pin;
    c->title_right=(int16_t)(12U+canvas_string_width(c,title)-1U);
    canvas_draw_str(c,12,9,title);
}
uint8_t ui_kit_key_hint_compact(
    Canvas* c,uint8_t x,UiKitKey key,const char* text) {
    unsigned w= key==UiKitKeyLeftRight ? 18U :
                key==UiKitKeyOk ? 19U : 16U;
    const unsigned end=x+w+3U+strlen(text)*6U;
    if(x+w>128U||end>127U) c->faults++;
    c->key_count++;
    return (uint8_t)end;
}

static void test_header(const char* title,const char* status,bool filled) {
    Canvas c={0};
    labmate_pixel_header(&c,title,status,filled);
    assert(c.faults==0U);
    assert(c.chip_drawn);
    assert(c.text_count==2U);
    assert(c.title_right+3 < c.status_left);
    assert(c.status_right<128);
    assert(c.last_chip_y==0);
}
int main(void) {
    struct { const char* title; const char* status; } const cases[]={
        {"Alerts","ALRT"},{"Button","BUSY"},{"Logger","READY"},
        {"History","255/255"},{"Log view","WAIT"},
        {"Profiles","DELETED"},{"Profiles","PWM ON"},
        {"UART TX","DROP"},{"I2C","FW API"},
        {"1-Wire temp","ERROR"},{"Stats","2/2"},{"Evidence","2/2"}
    };
    for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);++i) {
        test_header(cases[i].title,cases[i].status,false);
        test_header(cases[i].title,cases[i].status,true);
    }
    Canvas c={0};
    labmate_pixel_keys(&c,UiKitKeyLeftRight,"Source",UiKitKeyOk,"Arm");
    assert(c.faults==0U && c.key_count==2U);
    c=(Canvas){0};
    labmate_pixel_keys(&c,UiKitKeyLeftRight,"Delete",UiKitKeyOk,"Select");
    assert(c.faults==0U && c.key_count==2U);
    c=(Canvas){0};
    labmate_comm_ui_keys(&c,UiKitKeyOk,"Stop",UiKitKeyBack,"Save");
    assert(c.faults==0U && c.key_count==2U);
    printf("E11 PIXEL HEADER HOST PASS: %lu chip cases, 3 dual-hint cases\n",
           (unsigned long)(2U*sizeof(cases)/sizeof(cases[0])));
    return 0;
}
