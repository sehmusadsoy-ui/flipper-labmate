/* LabMate v2.0 UI-02: real COMM renderer function bodies, host Canvas model.
 * Production includes are replaced ONLY by these narrow host types; the
 * functions themselves are extracted unmodified at host test execution.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>

typedef enum { FontSecondary, FontPrimary } Font;
typedef struct Canvas Canvas;
struct Canvas {
    Font font;
    struct { int x0, y0, x1, y1; } rects[32];
    unsigned count;
    unsigned faults;
    int badge_x, badge_y, badge_w;
};
void canvas_set_font(Canvas* c, Font font) { c->font = font; }
static int overlaps(int x0,int y0,int x1,int y1,int a0,int b0,int a1,int b1) {
    return !(x1<a0 || a1<x0 || y1<b0 || b1<y0);
}
void canvas_draw_str(Canvas* c, int x, int y, const char* text) {
    const int w=(int)strlen(text)*(c->font==FontPrimary?8:6);
    const int h=c->font==FontPrimary?11:8;
    if(x<0 || y<0 || x+w>128 || y>63 || y-h+1<0 || w<=0) {
        fprintf(stderr,"TEXT OUT OF LCD: %s x=%d width=%d baseline=%d\n",text,x,w,y);
        c->faults++;
    }
    if(c->count<32) {
        const int y0=y-h+1;
        for(unsigned i=0;i<c->count;i++) {
            const int x0=c->rects[i].x0, x1=c->rects[i].x1;
            const int b0=c->rects[i].y0, b1=c->rects[i].y1;
            if(overlaps(x,y0,x+w-1,y,x0,b0,x1,b1)) {
                fprintf(stderr,"TEXT OVERLAP: %s at (%d,%d)\n",text,x,y);
                c->faults++;
            }
        }
        c->rects[c->count].x0=x;
        c->rects[c->count].x1=x+w-1;
        c->rects[c->count].y0=y-h+1;
        c->rects[c->count].y1=y;
        c->count++;
    }
    /* Secondary badge labels must be inside their painted badge frame. */
    if(c->badge_w>0 && y==c->badge_y+8 && c->font==FontSecondary &&
       (x<c->badge_x || x+w>c->badge_x+c->badge_w)) {
        fprintf(stderr,"BADGE LABEL OUTSIDE FRAME: %s x=%d width=%d frame=[%d,%d)\n",text,x,w,c->badge_x,c->badge_x+c->badge_w);
        c->faults++;
    }
}
void canvas_draw_line(Canvas* c, int x0, int y0, int x1, int y1) {
    if(x0<0 || y0<0 || x1<0 || y1<0 || x0>=128 || x1>=128 || y0>=64 || y1>=64) {
        fprintf(stderr,"LINE OUT OF LCD (%d,%d) (%d,%d)\n",x0,y0,x1,y1);
        c->faults++;
    }
}
void ui_draw_header(Canvas* c, const char* title) {
    canvas_set_font(c,FontPrimary);
    canvas_draw_str(c,2,10,title);
    canvas_draw_line(c,0,13,127,13);
}
void ui_badge(Canvas* c, uint8_t x, uint8_t y, uint8_t w, const char* text, bool filled) {
    (void)filled;
    if((int)x+(int)w>128 || (int)y+11>64) c->faults++;
    c->badge_x=x;c->badge_y=y;c->badge_w=w;
    canvas_set_font(c,FontSecondary);
    canvas_draw_str(c,x+4,y+8,text);
}
void ui_footer_pair(Canvas* c, const char* lk, const char* la, const char* rk, const char* ra) {
    char label[32];
    canvas_draw_line(c,0,52,127,52);
    int n=snprintf(label,sizeof(label),"(%s) %s",lk,la);
    if(n>10) n=snprintf(label,sizeof(label),"(%s)%s",lk,la);
    assert(n>=0 && n<=10);
    canvas_set_font(c,FontSecondary);
    canvas_draw_str(c,2,61,label);
    n=snprintf(label,sizeof(label),"(%s) %s",rk,ra);
    if(n>10) n=snprintf(label,sizeof(label),"(%s)%s",rk,ra);
    assert(n>=0 && n<=10);
    canvas_draw_str(c,66,61,label);
}

typedef enum {
    LabMateI2cRuntimeApiMissing, LabMateI2cRuntimeBusy,
    LabMateI2cRuntimeScanning, LabMateI2cRuntimeResults,
    LabMateI2cRuntimeNoDevices, LabMateI2cRuntimeCancelled,
    LabMateI2cRuntimeFailed, LabMateI2cRuntimeReady
} LabMateI2cRuntimeStatus;
typedef struct {
    uint8_t found_total,page,page_count,row_count,row_address[4];
} LabMateI2cView;
typedef enum {
    LabMateOneWireHwConverting, LabMateOneWireHwMeasured,
    LabMateOneWireHwNoSensor, LabMateOneWireHwBusy,
    LabMateOneWireHwDataError, LabMateOneWireHwPowerCheck,
    LabMateOneWireHwStopped, LabMateOneWireHwReady
} LabMateOneWireHwStatus;
typedef struct {
    LabMateOneWireHwStatus status;
    bool has_temperature;
    int32_t temperature_tenths;
    uint8_t resolution_bits;
} LabMateOneWireHw;
typedef struct {
    void* i2c;
    uint8_t i2c_page;
    LabMateOneWireHw thermometer;
} LabMateApp;
static LabMateI2cRuntimeStatus current_status;
static LabMateI2cRuntimeStatus labmate_i2c_runtime_snapshot(
    void* runtime, uint8_t page, LabMateI2cView* out) {
    (void)runtime;(void)page;
    *out=(LabMateI2cView){.found_total=4,.page=0,.page_count=1,
                          .row_count=4,.row_address={0x18,0x28,0x48,0x76}};
    return current_status;
}

#include "labmate_i2c_ui_body.inc"
#include "labmate_onewire_ui_body.inc"

int main(void) {
    unsigned failures=0;
    for(int i=LabMateI2cRuntimeApiMissing;i<=LabMateI2cRuntimeReady;i++) {
        Canvas c={0}; LabMateApp app={0};current_status=(LabMateI2cRuntimeStatus)i;
        fprintf(stdout,"I2C case %d: ",i);fflush(stdout);
        draw_i2c(&c,&app);
        failures+=c.faults;
        fprintf(stdout,"%s\n",c.faults?"FAIL":"PASS");
    }
    for(int i=LabMateOneWireHwConverting;i<=LabMateOneWireHwReady;i++) {
        Canvas c={0};LabMateApp app={0};
        app.thermometer.status=(LabMateOneWireHwStatus)i;
        app.thermometer.has_temperature=true;
        app.thermometer.temperature_tenths=-250;
        app.thermometer.resolution_bits=12;
        fprintf(stdout,"1W case %d: ",i);fflush(stdout);
        draw_onewire(&c,&app);
        failures+=c.faults;
        fprintf(stdout,"%s\n",c.faults?"FAIL":"PASS");
    }
    if(failures){fprintf(stderr,"UI-02 COMM GEOMETRY FAIL: %u conditions\n",failures);return 1;}
    puts("UI-02 COMM GEOMETRY PASS: 8 I2C + 8 1-Wire renderer states");
    return 0;
}
