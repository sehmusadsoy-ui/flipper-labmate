/* Exact production menu/chrome bodies. Icons are bounded ABI mocks; real
 * device glyphs/bitmaps remain a physical raster gate. Old grid assertions
 * are mapped explicitly in V20_E11_CURRENT_ACCEPTANCE_COVERAGE.md. */
#include "ui_kit.h"
#include "labmate_navigation.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    bool menu_in_group, ui_carousel_motion, ui_list_motion;
    uint8_t menu_group, selected, ui_frame, ui_from, ui_pulse_phase, ui_list_previous;
    int8_t ui_direction;
} LabMateApp;
struct Canvas {
    Font font; Color color;
    unsigned texts, icons, pills;
    int pill_y;
    struct { int x,y,w,h; char text[40]; } text[12];
};
void canvas_set_font(Canvas* c,Font f) {c->font=f;}
void canvas_set_color(Canvas* c,Color color) {c->color=color;}
uint16_t canvas_string_width(Canvas* c,const char* s) {
    return (uint16_t)(strlen(s)*(c->font==FontPrimary?8U:6U));
}
static void rect(int x,int y,int w,int h) {
    assert(x>=0&&y>=0&&w>0&&h>0&&x+w<=128&&y+h<=64);
}
void canvas_draw_line(Canvas* c,int32_t x,int32_t y,int32_t xx,int32_t yy) {
    assert(c&&x>=0&&xx>=0&&y>=0&&yy>=0&&x<128&&xx<128&&y<64&&yy<64);
}
void canvas_draw_box(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h) {
    assert(c);rect(x,y,w,h);
}
void canvas_draw_rbox(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t r) {
    assert(r==3);rect(x,y,w,h);c->pills++;c->pill_y=y;
}
void canvas_draw_rframe(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t r) {
    assert(c&&r==3);rect(x,y,w,h);
}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* s) {
    assert(c&&s&&*s&&c->texts<12U);
    const int w=canvas_string_width(c,s), h=c->font==FontPrimary?11:8;
    rect(x,y-h+1,w,h);
    for(const unsigned char* p=(const unsigned char*)s;*p;p++) assert(*p>=32&&*p<=126);
    for(unsigned i=0;i<c->texts;i++) {
        const int a=c->text[i].x,b=c->text[i].y;
        assert(x>=a+c->text[i].w||a>=x+w||y-h+1>b||b-c->text[i].h+1>y);
    }
    const unsigned n=c->texts++;
    c->text[n].x=x;c->text[n].y=y;c->text[n].w=w;c->text[n].h=h;
    snprintf(c->text[n].text,sizeof(c->text[n].text),"%s",s);
}
void ui_kit_icon(Canvas* c,UiKitIcon icon,int16_t x,int16_t y,uint8_t size,
                 bool subdued,bool inverse,uint8_t phase) {
    (void)subdued;(void)inverse;(void)phase;
    assert(c&&icon<UiKitIconCount);rect(x,y,size,size);c->icons++;
}
#include "menu_chrome.inc"
#include "menu.inc"

static void run(LabMateApp a) {
    Canvas c={0};const LabMateApp before=a;
    draw_menu(&c,&a);
    assert(!memcmp(&a,&before,sizeof(a))); /* presenter stays passive */
    assert(c.color==ColorBlack);
    if(!a.menu_in_group) {
        assert(c.pills==0U&&c.texts==4U);
        assert(c.icons==(a.ui_carousel_motion&&a.ui_frame<UI_KIT_TWEEN_FRAMES?2U:3U));
        assert(c.text[0].y==8&&c.text[1].y==8);
        assert(!strcmp(c.text[0].text,"LabMate Ultimate")||!strcmp(c.text[0].text,"LabMate"));
        assert(!strcmp(c.text[1].text,"V2.0"));
        assert(c.text[2].y==46&&c.text[3].y==55);
        const char* const groups[]={"Measure","Output","Records","Comm","Settings"};
        assert(!strcmp(c.text[2].text,groups[a.selected<5U?a.selected:0U]));
    } else {
        const uint8_t count=labmate_nav_group_size(a.menu_group);
        const uint8_t selected=a.selected<count?a.selected:0U;
        const uint8_t first=labmate_nav_first_visible(selected,count,3U);
        const unsigned remaining=(unsigned)count-first;
        const unsigned visible=remaining<3U?remaining:3U;
        assert(c.pills==1U&&c.icons==visible);
        assert(c.texts==1U+visible+(first+3U<count?1U:0U));
        for(unsigned row=0;row<visible;row++) {
            const uint8_t tool=labmate_nav_tool_at(a.menu_group,(uint8_t)(first+row));
            assert(c.text[row+1U].x==22&&c.text[row+1U].y==22+(int)row*14);
            assert(!strcmp(c.text[row+1U].text,labmate_tool_name(tool))||
                   !strcmp(c.text[row+1U].text,labmate_tool_short_name(tool)));
        }
        if(!a.ui_list_motion||a.ui_frame>=UI_KIT_TWEEN_FRAMES)
            assert(c.pill_y==12+(selected-first)*14);
    }
}
int main(void) {
    unsigned scenarios=0;
    for(uint8_t group=0;group<LabMateGroupCount;group++) {
        run((LabMateApp){.selected=group});scenarios++;
        for(int direction=-1;direction<=1;direction+=2)
            for(uint8_t frame=0;frame<=UI_KIT_TWEEN_FRAMES;frame++) {
                run((LabMateApp){.selected=group,.ui_carousel_motion=true,
                    .ui_direction=(int8_t)direction,.ui_frame=frame,
                    .ui_from=labmate_nav_wrap(group,LabMateGroupCount,-direction)});
                scenarios++;
            }
        const uint8_t count=labmate_nav_group_size(group);
        for(uint8_t selected=0;selected<count;selected++) {
            run((LabMateApp){.menu_in_group=true,.menu_group=group,.selected=selected});scenarios++;
            for(uint8_t previous=0;previous<count;previous++)
                for(uint8_t frame=0;frame<=UI_KIT_TWEEN_FRAMES;frame++) {
                    run((LabMateApp){.menu_in_group=true,.menu_group=group,.selected=selected,
                        .ui_list_motion=true,.ui_list_previous=previous,.ui_frame=frame});
                    scenarios++;
                }
        }
        run((LabMateApp){.menu_in_group=true,.menu_group=group,.selected=255U});scenarios++;
    }
    run((LabMateApp){.selected=255U});scenarios++;
    printf("E11 CURRENT MENU PASS: %u selections/transitions, exact source/chrome, bounded icon ABI mock\n",scenarios);
    return 0;
}
