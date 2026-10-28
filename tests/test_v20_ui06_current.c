/* E11 UI06 - exact production pair and triple footer source, not old inverse UI.
 * All text must remain within 128x64 and stay in black ink; never partial paint.
 */
#include "gui/gui.h"
#include "labmate_ui_layout.h"
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
typedef struct {int32_t x,y;char text[32];} Caption;
struct Canvas {Font font;Color color;unsigned faults,paints,count;Caption captions[4];};
void canvas_set_font(Canvas* c,Font f){c->font=f;}
void canvas_set_color(Canvas* c,Color x){c->color=x;}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* s){
    assert(c&&s);
    if(x<0||y<7||y>=64||x+6*(int32_t)strlen(s)>128)c->faults++;
    if(c->count<4U){
        Caption* t=&c->captions[c->count++];
        t->x=x;t->y=y;
        snprintf(t->text,sizeof(t->text),"%s",s);
    }else c->faults++;
    c->paints++;
}
#include "ui_format_key.inc"
#include "ui_key.inc"
#include "ui_footer_action.inc"
#include "ui_footer_pair.inc"
#include "ui_footer_triple_label_valid.inc"
#include "ui_footer_triple.inc"
_Static_assert(LABMATE_UI_WIDTH==128 && LABMATE_UI_HEIGHT==64,"Flipper pixels");
_Static_assert(LABMATE_UI_FOOTER_BASELINE_Y==61,"current footer text baseline");
static unsigned valid_pair(void){
    const char* const cases[][4]={
      {"OK","SAVE","BACK","NO"},
      {"LR","SOURCE","OK","ARM"},
      {"DOWN","ACK","OK","OFF"},
      {"OK","DELETE","BACK","NO"},
      {"LR","MODE","OK","DELETE"},
      {"DOWN","MORE","OK","START"},
      {"OK","STOP","BACK","EXIT"},
      {"OK","RESUME","UP","RESET"},
      {"LR","FREQ","OK","RUN"},
      {"LR","SOURCE","OK","RECORD"},
      {"OK","START","BACK","EXIT"}
    };
    for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        struct Canvas c={0};char a[24],b[24];
        assert(ui_format_key(a,sizeof(a),cases[i][0],cases[i][1],10U));
        assert(ui_format_key(b,sizeof(b),cases[i][2],cases[i][3],10U));
        ui_footer_pair(&c,cases[i][0],cases[i][1],cases[i][2],cases[i][3]);
        assert(!c.faults&&c.count==2U&&c.paints==2U&&c.color==ColorBlack);
        assert(c.captions[0].x==2 && c.captions[1].x==66);
        assert(c.captions[0].y==61&&c.captions[1].y==61);
        assert(!strcmp(c.captions[0].text,a)&&!strcmp(c.captions[1].text,b));
        assert(strlen(a)<=10U&&strlen(b)<=10U);
    }
    return (unsigned)(sizeof(cases)/sizeof(cases[0]));
}
static unsigned valid_triple(void){
    const char* const cases[][3]={
        {"<> MODE","OK LIVE","^RST"},
        {"<> MODE","OK HOLD","^RST"},
        {"<>PIN","OK LIVE","^STAT"},
        {"<>PIN","OK HOLD","^STAT"},
        {"1234567","1234567","12345"}
    };
    for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        struct Canvas c={0};
        ui_footer_triple(&c,cases[i][0],cases[i][1],cases[i][2]);
        assert(!c.faults&&c.count==3U&&c.paints==3U);
        assert(c.font==FontSecondary&&c.color==ColorBlack);
        assert(c.captions[0].x==2&&c.captions[1].x==45&&c.captions[2].x==96);
        for(unsigned j=0;j<3;j++){
            assert(c.captions[j].y==61);
            assert(!strcmp(c.captions[j].text,cases[i][j]));
        }
    }
    return (unsigned)(sizeof(cases)/sizeof(cases[0]));
}
static unsigned malformed(void){
    const char* const cases[][3]={
        {NULL,"OK LIVE","^RST"},{"<> MODE",NULL,"^RST"},
        {"<> MODE","OK LIVE",NULL},{"","OK LIVE","^RST"},
        {"12345678","OK LIVE","^RST"},{"<> MODE","12345678","^RST"},
        {"<> MODE","OK LIVE","123456"},{"\xC3\xA9","OK LIVE","^RST"},
    };
    unsigned cases_done=0;
    for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        struct Canvas c={0};
        ui_footer_triple(&c,cases[i][0],cases[i][1],cases[i][2]);
        assert(!c.paints&&!c.count&&!c.faults);
        cases_done++;
    }
    {
        struct Canvas c={0};
        ui_footer_pair(&c,NULL,"TEST","OK","NEXT");
        assert(!c.paints&&!c.count);
        cases_done++;
    }
    {
        struct Canvas c={0};
        ui_footer_pair(&c,"OK","TOO_LONG_ACTION","BACK","EXIT");
        assert(!c.paints&&!c.count);
        cases_done++;
    }
    return cases_done;
}
int main(void){
    const unsigned a=valid_pair(),b=valid_triple(),c=malformed();
    assert(a==11U&&b==5U&&c==10U);
    printf("E11 UI06 EXACT QUIET FOOTER HOST PASS: pair=%u triple=%u rejects=%u\n",a,b,c);
    return 0;
}
