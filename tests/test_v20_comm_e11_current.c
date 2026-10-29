/* E11 UI02/UI03 migration: exact current I2C, OneWire and UART renderers,
 * driven by bounded test-only snapshot/port states. No GPIO or transport.
 */
#include "labmate_comm_ui.h"
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
typedef enum {AlignRight,AlignBottom} Align;
typedef enum {
 LabMateI2cRuntimeReady,LabMateI2cRuntimeApiMissing,
 LabMateI2cRuntimeBusy,LabMateI2cRuntimeScanning,
 LabMateI2cRuntimeResults,LabMateI2cRuntimeNoDevices,
 LabMateI2cRuntimeCancelled,LabMateI2cRuntimeFailed
} LabMateI2cRuntimeStatus;
typedef struct {
 uint8_t found_total,page,page_count,row_count,row_address[4];
} LabMateI2cView;
typedef struct {
 LabMateI2cRuntimeStatus status;
 LabMateI2cView view;
} LabMateI2cRuntime;
typedef enum {
 LabMateOneWireHwIdle,LabMateOneWireHwConverting,
 LabMateOneWireHwMeasured,LabMateOneWireHwNoSensor,
 LabMateOneWireHwBusy,LabMateOneWireHwDataError,
 LabMateOneWireHwPowerCheck,LabMateOneWireHwStopped
} LabMateOneWireHwStatus;
typedef struct {
 LabMateOneWireHwStatus status;
 int16_t temperature_tenths;
 uint8_t resolution_bits;
 bool has_temperature;
} LabMateOneWireHw;
typedef struct {char rows[3][20];uint8_t cursor_row,cursor_col;} LabMateUartText;
typedef struct {
 bool active,blocked,invalid_baud;
 uint32_t dropped,rx_errors,rx_total;
 bool tx_editing,tx_sent;
 char tx_text[13];
 uint8_t tx_cursor,baud_index;
 LabMateUartText terminal;
} LabMateUart;
typedef struct {
 LabMateOneWireHw thermometer;
 LabMateUart uart;
 LabMateI2cRuntime* i2c;
 uint8_t i2c_page,ui_frame;
} LabMateApp;
struct Canvas {
 Font font; Color color;
 unsigned faults,paints,text_count,keys,heads,panels,chip_count,big_numbers_count,degree_dots;
 unsigned primary_punctuation_count;
 bool missing_big_dot,missing_big_minus;
 UiKitInstrumentState chip_state;
 char strings[32][48];
 struct {uint8_t x;UiKitKey k;char label[16];} actions[2];
};
static Canvas fresh(void){Canvas c={0};c.color=ColorBlack;return c;}
void canvas_set_font(Canvas* c,Font f){c->font=f;}
size_t canvas_glyph_width(Canvas* c,uint16_t symbol){
 if(c->font==FontBigNumbers&&symbol=='.'&&c->missing_big_dot)return 0U;
 if(c->font==FontBigNumbers&&symbol=='-'&&c->missing_big_minus)return 0U;
 return c->font==FontPrimary?8U:c->font==FontBigNumbers?10U:6U;
}
uint16_t canvas_string_width(Canvas* c,const char* s){
 unsigned advance=c->font==FontPrimary?8U:c->font==FontBigNumbers?10U:6U;
 return (uint16_t)(strlen(s)*advance);
}
void canvas_set_color(Canvas* c,Color ink){c->color=ink;}
void canvas_draw_str(Canvas* c,int32_t x,int32_t y,const char* s){
 if(c->font==FontBigNumbers)c->big_numbers_count++;
 if(c->font==FontPrimary&&s[0]&&s[1]=='\0'&&
    (s[0]=='.'||s[0]=='-'))c->primary_punctuation_count++;
 int w=canvas_string_width(c,s);
 int h=c->font==FontBigNumbers?15:c->font==FontPrimary?10:8;
 if(!w||x<0||x+w>128||y<0||y>=64||y-h+1<0)c->faults++;
 if(c->text_count<32U)snprintf(c->strings[c->text_count],48,"%s",s);
 else c->faults++;
 c->text_count++;c->paints++;
}
void canvas_draw_dot(Canvas* c,int32_t x,int32_t y){
 if(x<0||x>=128||y<0||y>=64)c->faults++;
 c->degree_dots++;c->paints++;
}
void canvas_draw_line(Canvas* c,int32_t x,int32_t y,int32_t xx,int32_t yy){
 if(x<0||x>=128||xx<0||xx>=128||y<0||y>=64||yy<0||yy>=64)c->faults++;
 c->paints++;
}
void canvas_draw_rbox(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t r){
 (void)r;
 if(x<0||y<0||x+w>128||y+h>64||w<=0||h<=0)c->faults++;
 c->panels++;c->paints++;
}
void canvas_draw_rframe(Canvas* c,int32_t x,int32_t y,int32_t w,int32_t h,int32_t r){
 canvas_draw_rbox(c,x,y,w,h,r);
}
void ui_kit_back_title(Canvas* c,const char* title,const char* alt,const char* pin){
 (void)alt;(void)pin;
 c->heads++;canvas_set_color(c,ColorBlack);
 canvas_set_font(c,FontSecondary);
 canvas_draw_line(c,7,2,4,5);canvas_draw_line(c,4,5,7,8);
 canvas_draw_str(c,12,9,title);
}
bool ui_kit_text(Canvas* c,int16_t x,int16_t y,uint8_t w,
                 const char* label,const char* alt){
 if(!c||!label)return false;
 const char* chosen=label;
 if(canvas_string_width(c,chosen)>w)chosen=alt;
 if(!chosen||canvas_string_width(c,chosen)>w)return false;
 canvas_draw_str(c,x,y,chosen);return true;
}
uint8_t ui_kit_key_hint_compact(Canvas* c,uint8_t x,UiKitKey k,const char* s){
 unsigned w=k==UiKitKeyOk?19U:16U;
 unsigned end=x+w+3U+6U*strlen(s);
 if(!s||end>127U||c->keys>=2U){c->faults++;return 0U;}
 unsigned j=c->keys++;
 c->actions[j].x=x;c->actions[j].k=k;
 snprintf(c->actions[j].label,16,"%s",s);
 c->paints++;return (uint8_t)end;
}
#undef ui_kit_stat_row
bool ui_kit_stat_row(Canvas* c,uint8_t y,const char* a,const char* b){
 canvas_set_font(c,FontSecondary);
 unsigned aw=canvas_string_width(c,a),bw=canvas_string_width(c,b);
 if(aw+bw+8U>120U)return false;
 canvas_draw_str(c,4,y,a);
 canvas_draw_str(c,124-bw,y,b);
 return true;
}
/* Header and status mocks emulate the production pixel preflight and
 * string widths; exact ui_kit primitive bodies are independently source-
 * linked by scripts/test-v20-button-scope-uikit-step1-host.sh. */
uint8_t ui_kit_state_chip_width(Canvas* c,UiKitInstrumentState state){
 const char* name = state==UiKitInstrumentReady?"Ready":
  state==UiKitInstrumentLive?"Live":
  state==UiKitInstrumentStopped?"Stopped":
  state==UiKitInstrumentBusy?"Busy":
  state==UiKitInstrumentError?"Error":
  state==UiKitInstrumentNoReply?"No reply":
  state==UiKitInstrumentDone?"Done":NULL;
 if(!name)return 0U;
 canvas_set_font(c,FontSecondary);
 return (uint8_t)(canvas_string_width(c,name)+17U);
}
bool ui_kit_state_chip_compact(Canvas* c,UiKitInstrumentState state,bool pulse){
 (void)pulse;
 uint8_t w=ui_kit_state_chip_width(c,state);
 if(!w)return false;
 uint8_t x=(uint8_t)(127U-w);
 canvas_set_color(c,ColorBlack);
 canvas_draw_rframe(c,x,0U,w,11U,3U);
 canvas_set_font(c,FontSecondary);
 const char* name=state==UiKitInstrumentReady?"Ready":
  state==UiKitInstrumentLive?"Live":
  state==UiKitInstrumentStopped?"Stopped":
  state==UiKitInstrumentBusy?"Busy":
  state==UiKitInstrumentNoReply?"No reply":
  state==UiKitInstrumentDone?"Done":"Error";
 canvas_draw_str(c,x+12U,9U,name);
 c->chip_count++;c->chip_state=state;
 return true;
}
bool ui_kit_pixel_header(Canvas* c,const char* title,bool show_chip,
                         UiKitInstrumentState state,bool pulse){
 if(!c||!title||!title[0])return false;
 canvas_set_font(c,FontPrimary);
 unsigned tw=canvas_string_width(c,title);
 if(!tw||9U+tw>127U)return false;
 if(show_chip){
  uint8_t w=ui_kit_state_chip_width(c,state);
  if(!w||9U+tw+2U>127U-w)return false;
 }
 canvas_set_color(c,ColorBlack);
 canvas_draw_line(c,5U,2U,2U,5U);
 canvas_draw_line(c,2U,5U,5U,8U);
 canvas_set_font(c,FontPrimary);
 canvas_draw_str(c,9U,9U,title);
 if(show_chip&&!ui_kit_state_chip_compact(c,state,pulse))return false;
 c->heads++;
 return true;
}
bool ui_kit_tag(Canvas* c,uint8_t x_right,uint8_t y,const char* s){
 if(!c||!s||!s[0]||x_right>=128U||y>55U)return false;
 canvas_set_font(c,FontSecondary);
 uint32_t w=(uint32_t)canvas_string_width(c,s)+8U;
 if(w>x_right+1U)return false;
 uint8_t x=(uint8_t)(x_right+1U-w);
 canvas_set_color(c,ColorBlack);
 canvas_draw_rframe(c,x,y,(int32_t)w,9U,3U);
 canvas_draw_str(c,x+4U,y+7U,s);
 return true;
}
uint32_t labmate_uart_baud(const LabMateUart* u) {
 static const uint32_t rates[]={9600U,38400U,115200U};
 return rates[u->baud_index<3U?u->baud_index:0U];
}
LabMateI2cRuntimeStatus labmate_i2c_runtime_snapshot(
 LabMateI2cRuntime* r,uint8_t page,LabMateI2cView* v){
 (void)page;
 assert(r&&v);
 *v=r->view;return r->status;
}
/* The 3 extracted bodies are byte-identical to production draw functions. */
#include "comm_uart_e11.inc"
#include "comm_i2c_e11.inc"
#include "comm_onewire_e11.inc"

static bool has(const Canvas* c,const char* s){
 for(unsigned i=0;i<c->text_count&&i<32U;i++)
     if(!strcmp(c->strings[i],s))return true;
 return false;
}
static bool key(const Canvas* c,unsigned i,UiKitKey k,const char* s){
 return i<c->keys&&c->actions[i].k==k&&!strcmp(c->actions[i].label,s);
}
static void good(const Canvas* c){
 assert(c->faults==0U&&c->color==ColorBlack&&c->keys>=1U&&c->keys<=2U&&c->heads<=1U);
}
static void test_i2c(void) {
 unsigned count=0;
 for(unsigned st=0;st<8U;st++)for(unsigned page=0;page<3U;page++){
  LabMateI2cRuntime rt={0};
  rt.status=(LabMateI2cRuntimeStatus)st;
  rt.view=(LabMateI2cView){.found_total=4U,.page=(uint8_t)page,
    .page_count=3U,.row_count=4U,.row_address={0x20U,0x38U,0x40U,0x48U}};
  LabMateApp a={.i2c=&rt,.i2c_page=(uint8_t)page,
                 .ui_frame=(uint8_t)(7U+page)};
  const LabMateApp before=a;const LabMateI2cRuntime snapshot=rt;
  Canvas c=fresh();draw_i2c(&c,&a);good(&c);
  assert(!memcmp(&before,&a,sizeof(a))&&!memcmp(&snapshot,&rt,sizeof(rt)));
  assert(c.chip_count==1U);
  const UiKitInstrumentState expected=st==3U?UiKitInstrumentLive:
   st==5U?UiKitInstrumentNoReply:
   st==2U?UiKitInstrumentBusy:
   (st==1U||st==7U)?UiKitInstrumentError:
   st==6U?UiKitInstrumentStopped:UiKitInstrumentReady;
  assert(c.chip_state==expected);
  assert(has(&c,(st==5U||st==6U)?"I2C":"I2C explorer"));
  assert(has(&c,"3.3 V")&&has(&c,"SCL0 / SDA1"));
  assert(key(&c,0U,UiKitKeyOk,st==3U?"Stop":
       (st==4U||st==5U)?"Scan again":"Scan"));
  if(st==4U){
   assert(c.keys==2U&&key(&c,1U,UiKitKeyUpDown,"Page"));
   assert(has(&c,"0x20")&&has(&c,"0x48"));
   assert(has(&c,"4")&&has(&c,"found"));
   assert(has(&c,page==0U?"Page 1 of 3":
          page==1U?"Page 2 of 3":"Page 3 of 3"));
  }else{
   assert(c.keys==1U);
   if(st==0U||st==3U){
    assert(has(&c,st==3U?"Scanning bus...":"Press OK to scan"));
    assert(has(&c,"SCL")&&has(&c,"SDA"));
   }else if(st==1U) {
    assert(has(&c,"Firmware error")&&has(&c,"Timed API required"));
   }else if(st==2U){
    assert(has(&c,"Bus busy")&&has(&c,"Tool owns the bus"));
   }else if(st==5U){
    assert(has(&c,"No devices found")&&has(&c,"Wiring / pull-ups"));
   }else if(st==6U){
    assert(has(&c,"Scan cancelled")&&has(&c,"Press OK to scan"));
   }else if(st==7U){
    assert(has(&c,"Scan error")&&has(&c,"Check bus / retry"));
   }
  }
  assert(!has(&c,"Exit")&&!has(&c,"NO ACKS / CHECK BUS"));
  ++count;
 }
 assert(count==24U);
 /* No false ACK or page chip when a scan returned only one address. */
 LabMateI2cRuntime rt={.status=LabMateI2cRuntimeResults,
  .view={.found_total=1U,.page_count=1U,.row_count=1U,
         .row_address={0x3CU}}};
 LabMateApp a={.i2c=&rt};
 const LabMateI2cRuntime before=rt;
 Canvas c=fresh();draw_i2c(&c,&a);good(&c);
 assert(c.keys==1U);
 assert(has(&c,"0x3C")&&has(&c,"device found"));
 assert(!has(&c,"Page 1 of 1"));
 assert(!memcmp(&rt,&before,sizeof(rt)));
}
static void test_onewire(void){
 unsigned n=0;
 for(unsigned st=0;st<8U;st++)for(unsigned variant=0;variant<7U;variant++){
  LabMateApp a={0};
  a.thermometer.status=(LabMateOneWireHwStatus)st;
  a.thermometer.has_temperature=(variant!=2U);
  a.thermometer.temperature_tenths=(variant==1U?-550:
      variant==3U?1250:variant==4U?-551:variant==5U?1251:235);
  a.thermometer.resolution_bits=variant==6U?8U:12U;
  a.ui_frame=(uint8_t)variant;
  const bool valid=variant==0U||variant==1U||variant==3U;
  const bool done=st==2U&&valid;
  const LabMateApp copy=a;
  Canvas c=fresh();draw_onewire(&c,&a);good(&c);
  assert(!memcmp(&copy,&a,sizeof(a)));
  assert(c.chip_count==1U);
  const UiKitInstrumentState expected=st==1U?UiKitInstrumentLive:
   done?UiKitInstrumentDone:st==3U?UiKitInstrumentNoReply:
   st==4U?UiKitInstrumentBusy:
   (st==5U||st==6U||(st==2U&&!valid))?UiKitInstrumentError:
   st==7U?UiKitInstrumentStopped:UiKitInstrumentReady;
  assert(c.chip_state==expected);
  assert(has(&c,(st==3U||st==7U)?"1-Wire":"1-Wire temp"));
  assert(has(&c,"DQ pin PA4")&&has(&c,"3.3 V"));
  assert(c.keys==1U);
  assert(key(&c,0U,UiKitKeyOk,st==1U?"Stop":done?"Read again":"Read"));
  assert(!has(&c,"EXTERNAL VDD ONLY")&&!has(&c,"EXT. VDD REQUIRED"));
  assert(!has(&c,"Menu"));
  const char* expected_message=st==0U?"External VDD needed":
    st==1U?"Reading sensor...":
    st==2U?(valid?"Temperature":"Invalid data"):
    st==3U?"Check DQ and power":
    st==4U?"PA4 is busy":
    st==5U?"Invalid data":
    st==6U?"Check VDD power":"Measurement stopped";
  assert(has(&c,expected_message));
  assert(c.big_numbers_count==1U&&c.degree_dots==4U);
  assert(has(&c,"C"));
  if(done){
   assert(has(&c,variant==1U?"-55.0":variant==3U?"125.0":"23.5"));
   assert(has(&c,"12-bit"));
   assert(!has(&c,"--.-"));
  }else{
   assert(has(&c,"--.-"));
   assert(!has(&c,"12-bit"));
   assert(!has(&c,"23.5")&&!has(&c,"-55.0")&&!has(&c,"125.0"));
  }
  ++n;
 }
 assert(n==56U);

 /* Additional signed decimal, 9/10/11-bit boundary and invalid samples.
  * The display is read-only; negative and missing data must never fabricate
  * a valid CRC, a temperature or a resolution. */
 struct Case {int16_t temp;uint8_t bits;bool has;const char* value;bool ok;};
 static const struct Case cases[]={
  {-125,9U,true,"-12.5",true},
  {-1,10U,true,"-0.1",true},
  {0,11U,true,"0.0",true},
  {234,12U,true,"23.4",true},
  {1250,12U,true,"125.0",true},
  {-550,12U,true,"-55.0",true},
  {235,12U,false,"--.-",false},
  {235,8U,true,"--.-",false},
  {-551,12U,true,"--.-",false},
  {1251,12U,true,"--.-",false},
  {INT16_MIN,12U,true,"--.-",false},
 };
 for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  LabMateApp a={0};
  a.thermometer.status=LabMateOneWireHwMeasured;
  a.thermometer.temperature_tenths=cases[i].temp;
  a.thermometer.resolution_bits=cases[i].bits;
  a.thermometer.has_temperature=cases[i].has;
  const LabMateApp before=a;
  Canvas c=fresh();draw_onewire(&c,&a);good(&c);
  assert(!memcmp(&before,&a,sizeof(a)));
  assert(has(&c,cases[i].value));
  assert(c.chip_count==1U&&c.chip_state==
         (cases[i].ok?UiKitInstrumentDone:UiKitInstrumentError));
  assert(c.keys==1U&&key(&c,0U,UiKitKeyOk,
                          cases[i].ok?"Read again":"Read"));
  if(cases[i].ok){
   char expected_bits[16];
   snprintf(expected_bits,sizeof(expected_bits),"%u-bit",cases[i].bits);
   assert(has(&c,expected_bits));
  }else{
   assert(!has(&c,"12-bit")&&!has(&c,"9-bit"));
  }
 }
}
static void test_onewire_missing_glyph_fallback(void) {
 /* Exercise the ACTUAL runtime font-subset fallback, not a mocked copy. */
 LabMateApp a={0};
 a.thermometer.status=LabMateOneWireHwMeasured;
 a.thermometer.temperature_tenths=-125;
 a.thermometer.resolution_bits=12U;
 a.thermometer.has_temperature=true;
 const LabMateApp original=a;
 Canvas c=fresh();
 c.missing_big_dot=true;c.missing_big_minus=true;
 draw_onewire(&c,&a);good(&c);
 assert(!memcmp(&a,&original,sizeof(a)));
 assert(c.chip_state==UiKitInstrumentDone);
 assert(has(&c,"-")&&has(&c,".")&&has(&c,"1")&&has(&c,"2")&&has(&c,"5"));
 assert(c.primary_punctuation_count==2U&&c.big_numbers_count==3U);
 assert(c.degree_dots==4U&&has(&c,"C")&&has(&c,"12-bit"));
 assert(key(&c,0U,UiKitKeyOk,"Read again"));

 a.thermometer.status=LabMateOneWireHwNoSensor;
 c=fresh();c.missing_big_dot=true;c.missing_big_minus=true;
 draw_onewire(&c,&a);good(&c);
 assert(c.chip_state==UiKitInstrumentNoReply);
 assert(c.primary_punctuation_count==4U);
 assert(c.big_numbers_count==0U && c.degree_dots==4U);
 assert(!has(&c,"12-bit"));
}
static void test_uart(void) {
 unsigned n=0;
 for(unsigned state=0U;state<32U;state++){
  LabMateApp a={0};
  a.uart.active=(state&1U)!=0U;
  a.uart.blocked=(state&2U)!=0U;
  a.uart.invalid_baud=(state&4U)!=0U;
  a.uart.dropped=(state&8U)?5U:0U;
  a.uart.rx_errors=(state&16U)?2U:0U;
  a.uart.baud_index=(uint8_t)(state%3U);
  a.uart.rx_total=(state%4U)?0U:52U;
  a.uart.tx_editing=(state%5U)==0U;
  a.uart.tx_sent=(state%7U)==0U;
  a.uart.tx_cursor=2U;
  a.ui_frame=(uint8_t)state;
  snprintf(a.uart.tx_text,sizeof(a.uart.tx_text),"HI");
  snprintf(a.uart.terminal.rows[0],20,"HELLO");
  snprintf(a.uart.terminal.rows[1],20,"WORLD");
  const LabMateApp before=a;
  Canvas c=fresh();draw_uart(&c,&a);good(&c);
  assert(!memcmp(&before,&a,sizeof(a))); /* draw must never mutate UART */
  if(a.uart.tx_editing){
   assert(has(&c,"UART TX"));
   assert(c.chip_count==0U);
   assert(has(&c,"HI")&&key(&c,0U,UiKitKeyOk,"Send"));
   assert(key(&c,1U,UiKitKeyBack,"RX")); /* TX remains old UI */
  }else{
   const UiKitInstrumentState expected=a.uart.blocked ?
    UiKitInstrumentBusy : a.uart.invalid_baud ?
    UiKitInstrumentError : a.uart.active ?
    UiKitInstrumentLive :
    a.uart.rx_total||a.uart.dropped||a.uart.rx_errors ?
    UiKitInstrumentStopped : UiKitInstrumentReady;
   assert(c.chip_count==1U && c.chip_state==expected);
   assert(has(&c,expected==UiKitInstrumentStopped?"UART":"UART receive"));
   assert(has(&c,"TX pin 13")&&has(&c,"RX pin 14"));
   assert(has(&c,"Baud rate"));
   assert(has(&c,"Recv")&&has(&c,"Drop")&&has(&c,"Errors"));
   assert(key(&c,0U,UiKitKeyOk,a.uart.active?"Stop":"Start"));
   assert(key(&c,1U,UiKitKeyLeftRight,"Baud"));
   assert(!has(&c,"WAITING RX...")&&!has(&c,"OK START / LR BAUD"));
   assert(!has(&c,"HELLO")&&!has(&c,"WORLD"));
  }
  ++n;
 }
 assert(n==32U);

 struct Case {uint32_t received,dropped,errors; const char* r,*d,*e;};
 static const struct Case cases[]={
  {0U,0U,0U,"0","0","0"},
  {1234U,5U,2U,"1234","5","2"},
  {12345U,10000U,100000U,"12.3k","10.0k","100k"},
  {1234567U,1000000U,4200000000U,"1.2M","1.0M","4.2G"},
  {UINT32_MAX,UINT32_MAX,UINT32_MAX,"4.2G","4.2G","4.2G"},
 };
 for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
  LabMateApp a={0};
  a.uart.active=true;a.uart.baud_index=2U;
  a.uart.rx_total=cases[i].received;
  a.uart.dropped=cases[i].dropped;
  a.uart.rx_errors=cases[i].errors;
  const LabMateApp before=a;
  Canvas c=fresh();draw_uart(&c,&a);good(&c);
  assert(!memcmp(&a,&before,sizeof(a)));
  assert(has(&c,cases[i].r)&&has(&c,cases[i].d)&&has(&c,cases[i].e));
  assert(has(&c,"115200")); /* existing 3 baud presets unchanged */
  assert(c.chip_state==UiKitInstrumentLive&&c.chip_count==1U);
 }
}

int main(void) {
 test_i2c();test_onewire();test_onewire_missing_glyph_fallback();test_uart();
 puts("E11 UI02/03 CURRENT COMM EXACT RENDER PASS: 24 I2C + 56 1W + 32 UART");
 return 0;
}
