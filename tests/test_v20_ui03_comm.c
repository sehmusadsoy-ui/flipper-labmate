/* UI-03 host-only bounded Canvas + actual extracted 1-Wire/UART renderer bodies. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>

typedef enum { FontSecondary = 0, FontPrimary = 1 } Font;
typedef struct Canvas Canvas;
struct Canvas {
    Font font;
    unsigned errors, drawn;
    int badge_x, badge_y, badge_width;
    char strings[24][48];
};
void canvas_set_font(Canvas* c, Font f) { assert(c); c->font=f; }
void canvas_draw_str(Canvas* c, int x, int y, const char* s) {
    assert(c && s);
    int w=(int)strlen(s)*(c->font==FontPrimary?8:6);
    int h=c->font==FontPrimary?11:8;
    if(x<0 || y<0 || x+w>128 || y>=64 || y-h+1<0) {
        fprintf(stderr, "TEXT BOUNDS: '%s' x=%d y=%d w=%d\n",s,x,y,w);
        c->errors++;
    }
    if(c->badge_width && y==c->badge_y+8 && x==c->badge_x+4 &&
       x+w>c->badge_x+c->badge_width) {
        fprintf(stderr, "BADGE CLIP '%s'\n",s); c->errors++;
    }
    if(c->drawn<24) (void)snprintf(c->strings[c->drawn++],48,"%s",s);
}
void canvas_draw_line(Canvas* c, int x0, int y0, int x1, int y1) {
    if(!c || x0<0 || x1<0 || y0<0 || x0>=128 || x1>=128 || y0>=64 || y1>=64) {
        fprintf(stderr,"LINE BOUNDS\n"); if(c)c->errors++;
    }
}
void ui_draw_header(Canvas* c, const char* t) {
    canvas_set_font(c, FontPrimary); canvas_draw_str(c,2,10,t);
    canvas_draw_line(c,0,13,127,13);
}
void ui_badge(Canvas* c, uint8_t x, uint8_t y, uint8_t w, const char* s,bool filled) {
    (void)filled;
    if((unsigned)x+w>128U || (unsigned)y+11U>64U) c->errors++;
    c->badge_x=x;c->badge_y=y;c->badge_width=w;
    canvas_set_font(c,FontSecondary);canvas_draw_str(c,x+4,y+8,s);
}
void ui_footer_pair(Canvas* c, const char* a,const char* b,const char* d,const char* e) {
    char text[32];int n=snprintf(text,sizeof(text),"(%s) %s",a,b);
    if(n>10)n=snprintf(text,sizeof(text),"(%s)%s",a,b);
    assert(n>0 && n<=10);canvas_draw_line(c,0,52,127,52);
    canvas_set_font(c,FontSecondary);canvas_draw_str(c,2,61,text);
    n=snprintf(text,sizeof(text),"(%s) %s",d,e);
    if(n>10)n=snprintf(text,sizeof(text),"(%s)%s",d,e);
    assert(n>0 && n<=10);canvas_draw_str(c,66,61,text);
}
typedef enum {
    LabMateOneWireHwIdle = 0,
    LabMateOneWireHwConverting,
    LabMateOneWireHwMeasured,
    LabMateOneWireHwNoSensor,
    LabMateOneWireHwBusy,
    LabMateOneWireHwDataError,
    LabMateOneWireHwPowerCheck,
    LabMateOneWireHwStopped
} LabMateOneWireHwStatus;
typedef struct {
    LabMateOneWireHwStatus status;
    int16_t temperature_tenths;
    uint8_t resolution_bits;
    bool has_temperature;
} LabMateOneWireHw;
#define LABMATE_UART_TX_CAP 12U
#define LABMATE_UART_ROWS 3U
#define LABMATE_UART_COLS 19U
typedef struct {
    char rows[LABMATE_UART_ROWS][LABMATE_UART_COLS+1U];
    uint8_t cursor_row, cursor_col;
} LabMateUartText;
typedef struct {
    bool active, blocked, invalid_baud;
    uint32_t dropped, rx_errors, rx_total;
    bool tx_editing, tx_sent;
    char tx_text[LABMATE_UART_TX_CAP+1U];
    uint8_t tx_cursor, baud_index;
    LabMateUartText terminal;
} LabMateUart;
typedef struct {
    LabMateOneWireHw thermometer;
    LabMateUart uart;
} LabMateApp;
uint32_t labmate_uart_baud(const LabMateUart* u) {
    const uint32_t rates[]={9600U,57600U,115200U};
    return rates[u->baud_index<3U?u->baud_index:0U];
}
#include "labmate_onewire_ui_body.inc"
#include "labmate_uart_ui_body.inc"
static bool saw(const Canvas* c,const char* needle){
    for(unsigned i=0;i<c->drawn;i++) if(!strcmp(c->strings[i],needle)) return true;
    return false;
}
static void check_onewire(void) {
    LabMateApp app={0};
    for(int i=LabMateOneWireHwIdle;i<=LabMateOneWireHwStopped;i++) {
        Canvas c={0};app.thermometer=(LabMateOneWireHw){
            .status=(LabMateOneWireHwStatus)i,.has_temperature=true,
            .temperature_tenths=-550,.resolution_bits=12};
        draw_onewire(&c,&app);
        assert(c.errors==0);
        if(i==LabMateOneWireHwMeasured) assert(saw(&c,"-55.0 C / 12bit"));
    }
    struct {int16_t value;uint8_t bits;bool present;const char* expected;} cases[]={
        {-550,9,true,"-55.0 C / 9bit"},
        {1250,12,true,"125.0 C / 12bit"},
        {0,11,true,"0.0 C / 11bit"},
        {INT16_MIN,12,true,"INVALID TEMP DATA"},
        {INT16_MAX,12,true,"INVALID TEMP DATA"},
        {-551,12,true,"INVALID TEMP DATA"},
        {1251,12,true,"INVALID TEMP DATA"},
        {250,8,true,"INVALID TEMP DATA"},
        {250,13,true,"INVALID TEMP DATA"},
        {250,12,false,"NO VALID SAMPLE"},
    };
    for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);i++) {
        Canvas c={0};
        app.thermometer=(LabMateOneWireHw){
            .status=LabMateOneWireHwMeasured,.has_temperature=cases[i].present,
            .temperature_tenths=cases[i].value,.resolution_bits=cases[i].bits};
        draw_onewire(&c,&app);
        if(c.errors || !saw(&c,cases[i].expected)) {
            fprintf(stderr,"1W case %u wanted: %s\n",i,cases[i].expected);
            assert(!"invalid 1-Wire sample rendered as real value or clipped");
        }
    }
}
static void check_uart(void) {
    LabMateApp app={0};
    for(uint8_t baud=0;baud<3;baud++) for(unsigned state=0;state<10;state++){
        Canvas c={0};LabMateUart* u=&app.uart;
        *u=(LabMateUart){0}; u->baud_index=baud;
        u->active=(state&1U)!=0;
        u->blocked=(state==2);
        u->invalid_baud=(state==3);
        u->dropped=state==4?UINT32_MAX:0;
        u->rx_errors=state==5?UINT32_MAX:0;
        u->rx_total=state>=6?UINT32_MAX:0;
        u->terminal.cursor_row=(state%3U);
        for(unsigned k=0;k<3;k++) { memset(u->terminal.rows[k],'X',19);u->terminal.rows[k][19]=0;}
        u->tx_editing=(state==8 || state==9);
        u->tx_sent=(state==9);
        memcpy(u->tx_text,"ABCDEFGHIJKL",13);
        u->tx_cursor=11;
        draw_uart(&c,&app);
        assert(c.errors==0);
    }
}
int main(void) {
    check_onewire();
    check_uart();
    puts("UI-03 HOST PASS: 1-Wire sensor envelope and UART RX/TX boundaries");
    return 0;
}
