#!/usr/bin/env python3
"""Genuine patched SignalReader ISR/START/STOP C and parser BUSY fault test.

No actual Flipper NFC, DMA sampling or external radio test. Uses native
function bodies and strict mocked peripheral side effects.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#define UNUSED(x) ((void)(x))
#define furi_check(x) assert(x)
#define furi_assert(x) assert(x)
enum { FuriHalBusTIM16=16, FuriHalInterruptIdDma2Ch2=2,
 FuriHalInterruptPriorityHighest=1, GpioModeInterruptRiseFall=1,
 GpioModeAnalog=2,GpioPullNo=0,GpioPullDown=1,GpioSpeedLow=0,
 GpioSpeedVeryHigh=4,LL_TIM_COUNTERMODE_UP=0,LL_TIM_CLOCKDIVISION_DIV1=0,
 LL_TIM_CLOCKSOURCE_INTERNAL=0,LL_TIM_OCMODE_FROZEN=0,
 LL_TIM_OCSTATE_DISABLE=0,LL_TIM_OCPOLARITY_HIGH=0,
 LL_TIM_TRGO_RESET=0,LL_TIM_CHANNEL_CH1=1,LL_DMA_CHANNEL_2=2,
 LL_DMA_CHANNEL_3=3,LL_DMA_CHANNEL_5=5,LL_DMAMUX_REQ_GEN_0=0,
 LL_DMAMUX_REQ_GEN_POL_RISING=0,LL_DMAMUX_REQ_GENERATOR0=0,
 LL_DMAMUX_REQ_TIM16_CH1=0,LL_DMA_DIRECTION_MEMORY_TO_PERIPH=0,
 LL_DMA_DIRECTION_PERIPH_TO_MEMORY=0,LL_DMA_MODE_CIRCULAR=0,
 LL_DMA_PERIPH_NOINCREMENT=0,LL_DMA_MEMORY_NOINCREMENT=0,
 LL_DMA_MEMORY_INCREMENT=0,LL_DMA_PDATAALIGN_HALFWORD=0,
 LL_DMA_MDATAALIGN_HALFWORD=0,LL_DMA_PRIORITY_VERYHIGH=0,
 LL_DMA_PRIORITY_HIGH=0};
#define TIM_CR1_CEN 1U
#define SIGNAL_READER_DMA 2
#define SIGNAL_READER_DMA_GPIO_DEF 2,2
#define SIGNAL_READER_DMA_TRIGGER_DEF 2,3
#define SIGNAL_READER_DMA_CNT_SYNC_DEF 2,5
#define SIGNAL_READER_DMA_GPIO_IRQ 2
#define SIGNAL_READER_CAPTURE_TIM_CHANNEL 1
typedef struct {uint32_t CR1,CNT;} SimTimer;
static SimTimer timer;
#define SIGNAL_READER_CAPTURE_TIM (&timer)
#define DMAMUX1 1
#define GET_DMAMUX_EXTI_LINE(pin) (2U)
typedef struct {uint32_t IDR;} GpioPort;
typedef struct {GpioPort* port;uint32_t pin;} GpioPin;
static GpioPort port;
static const GpioPin gpio_nfc_irq_rfid_pull={&port,4U},other={&port,8U};
typedef enum { GpioPullDummy=6 } GpioPullExtra;
typedef enum {SignalReaderPolarityNormal,SignalReaderPolarityInverted} SignalReaderPolarity;
typedef enum {SignalReaderTriggerNone,SignalReaderTriggerRisingFallingEdge} SignalReaderTrigger;
typedef enum {SignalReaderEventTypeHalfBufferFilled,
 SignalReaderEventTypeFullBufferFilled} SignalReaderEventType;
typedef struct {uint8_t* data;size_t len;} SignalReaderEventData;
typedef struct {SignalReaderEventType type;SignalReaderEventData* data;} SignalReaderEvent;
typedef void(*SignalReaderCallback)(SignalReaderEvent,void*);
typedef struct SignalReader SignalReader;
typedef struct {uint32_t OCMode,OCState,OCNState,CompareValue,OCPolarity;} LL_TIM_OC_InitTypeDef;
#define FURI_HAL_LEASE_NATIVE_SIGNAL_READER_NFC ((uint64_t)0x1FFF00000000ULL)
static bool claim_ok,release_ok=true,clock_on,rg_on,dma2,dma3,dma5,slot_ok=true,remove_ok=true,flag_half,flag_full;
static uint32_t owner_counter=77U,expected_owner;
static int claims,releases,writes,callbacks,irq_sets,callback_changes;
static void(*active_cb)(void*);
static void* active_ctx;
static uint32_t furi_hal_resource_lease_v2_try_acquire(uint64_t mask) {
 assert(mask==FURI_HAL_LEASE_NATIVE_SIGNAL_READER_NFC);
 claims++;return claim_ok?owner_counter:0U;
}
static bool furi_hal_resource_lease_v2_release(uint32_t handle,uint64_t mask) {
 assert(mask==FURI_HAL_LEASE_NATIVE_SIGNAL_READER_NFC && handle==owner_counter);
 releases++;return release_ok;
}
static bool furi_hal_bus_is_enabled(int bus) {assert(bus==16);return clock_on;}
static void furi_hal_bus_enable(int bus) {assert(bus==16 && !clock_on);clock_on=true;writes++;}
static void furi_hal_bus_disable(int bus) {assert(bus==16 && clock_on);clock_on=false;writes++;}
static bool enabled(int ctrl,int ch) {
 assert(ctrl==2);return ch==2?dma2:ch==3?dma3:dma5;
}
static void enable(int ctrl,int ch) {
 assert(ctrl==2);
 if(ch==2)dma2=true;else if(ch==3)dma3=true;else dma5=true;
 writes++;
}
static void deinit(int ctrl,int ch) {
 assert(ctrl==2);
 if(ch==2)dma2=false;else if(ch==3)dma3=false;else dma5=false;
 writes++;
}
#define LL_DMA_IsEnabledChannel enabled
#define LL_DMA_EnableChannel enable
#define LL_DMA_DeInit deinit
static bool dmamux_is_enabled(int ctrl,int gen) {
 assert(ctrl==DMAMUX1 && gen==0);return rg_on;
}
static void dmamux_enable(int ctrl,int gen) {
 assert(ctrl==DMAMUX1&&gen==0);rg_on=true;writes++;
}
static void dmamux_disable(int ctrl,int gen) {
 assert(ctrl==DMAMUX1&&gen==0);rg_on=false;writes++;
}
#define LL_DMAMUX_IsEnabledRequestGen dmamux_is_enabled
#define LL_DMAMUX_EnableRequestGen dmamux_enable
#define LL_DMAMUX_DisableRequestGen dmamux_disable
static bool furi_hal_gpio_try_add_int_callback(
 const GpioPin* p,void(*cb)(void*),void* ctx) {
 assert(p==&gpio_nfc_irq_rfid_pull && cb && ctx);
 if(!slot_ok || active_cb)return false;
 active_cb=cb;active_ctx=ctx;writes++;return true;
}
static bool furi_hal_gpio_try_remove_int_callback(
 const GpioPin* p,void(*cb)(void*),void* ctx) {
 assert(p==&gpio_nfc_irq_rfid_pull && cb && ctx);
 if(!remove_ok || active_cb!=cb || active_ctx!=ctx)return false;
 active_cb=NULL;active_ctx=NULL;writes++;return true;
}
static void furi_hal_gpio_init(const GpioPin* p,int mode,int pull,int speed) {
 assert(p==&gpio_nfc_irq_rfid_pull && (mode==GpioModeInterruptRiseFall ||
 mode==GpioModeAnalog));(void)pull;(void)speed;writes++;
}
static bool dma_half(int unused) {(void)unused;return flag_half;}
static bool dma_full(int unused) {(void)unused;return flag_full;}
#define LL_DMA_IsActiveFlag_HT2 dma_half
#define LL_DMA_IsActiveFlag_TC2 dma_full
#define LL_DMA_ClearFlag_HT2(unused) (flag_half=false,++writes)
#define LL_DMA_ClearFlag_TC2(unused) (flag_full=false,++writes)
#define LL_TIM_SetPrescaler(...) (++writes)
#define LL_TIM_SetCounterMode(...) (++writes)
#define LL_TIM_SetAutoReload(...) (++writes)
#define LL_TIM_SetClockDivision(...) (++writes)
#define LL_TIM_DisableARRPreload(...) (++writes)
#define LL_TIM_SetClockSource(...) (++writes)
#define LL_TIM_OC_Init(...) ((void)(&TIM_OC_InitStruct),++writes)
#define LL_TIM_OC_DisableFast(...) (++writes)
#define LL_TIM_SetTriggerOutput(...) (++writes)
#define LL_TIM_DisableMasterSlaveMode(...) (++writes)
#define LL_TIM_GenerateEvent_UPDATE(...) (++writes)
#define LL_DMA_SetMemoryAddress(...) (++writes)
#define LL_DMA_SetPeriphAddress(...) (++writes)
#define LL_DMA_ConfigTransfer(...) (++writes)
#define LL_DMA_SetDataLength(...) (++writes)
#define LL_DMA_SetPeriphRequest(...) (++writes)
#define LL_TIM_EnableDMAReq_CC1(...) (++writes)
#define LL_TIM_CC_EnableChannel(...) (++writes)
#define LL_TIM_SetCounter(...) (++writes)
#define LL_TIM_EnableCounter(...) (++writes)
#define LL_DMAMUX_SetRequestSignalID(...) (++writes)
#define LL_DMAMUX_SetRequestGenPolarity(...) (++writes)
#define LL_DMAMUX_SetGenRequestNb(...) (++writes)
#define LL_DMA_EnableIT_TC(...) (++writes)
#define LL_DMA_EnableIT_HT(...) (++writes)
static void furi_hal_gpio_enable_int_callback(const GpioPin* p){
 assert(p==&gpio_nfc_irq_rfid_pull);writes++;
}
static void furi_hal_interrupt_set_isr_ex(int id,int prio,void(*fn)(void*),void*ctx){
 assert(id==2 && prio==1 && fn && ctx);irq_sets++;writes++;
}
static void furi_hal_interrupt_set_isr(int id,void(*fn)(void*),void*ctx){
 assert(id==2 && !fn && !ctx);irq_sets++;writes++;
}
"""
RUN=r"""
static void cb(SignalReaderEvent event,void*ctx){
 assert(ctx==&timer);
 assert(event.data && event.data->len==1);
 callbacks++;
}
static void foreign(void* ptr) {(void)ptr;}
static void reset_case(SignalReader* r) {
 writes=callbacks=claims=releases=irq_sets=callback_changes=0;
 claim_ok=false;release_ok=slot_ok=remove_ok=true;
 clock_on=rg_on=dma2=dma3=dma5=flag_half=flag_full=false;
 active_cb=NULL;active_ctx=NULL;
 r->e11_owner=0U;r->e11_fault=false;r->callback=NULL;
 r->pin=&gpio_nfc_irq_rfid_pull;r->buffer_size=2;r->trigger=SignalReaderTriggerRisingFallingEdge;
 r->polarity=SignalReaderPolarityNormal;r->pull=GpioPullNo;r->tim_arr=603U;
 r->event.data=&r->event_data;
}
int main(void) {
 uint16_t gpio_buf[16]={0};uint8_t bit_buf[2]={0};
 SignalReader r={0};r.gpio_buffer=gpio_buf;r.bitstream_buffer=bit_buf;
 reset_case(&r);
 assert(!signal_reader_try_start(&r,cb,&timer));
 signal_reader_stop(&r);
 flag_half=true;furi_hal_sw_digital_pin_dma_rx_isr(&r);
 assert(writes==0 && !irq_sets && claims==1 && !callbacks);
 reset_case(&r);claim_ok=true;r.pin=&other;
 assert(!signal_reader_try_start(&r,cb,&timer));
 assert(!claims && !writes);
 for(int k=0;k<5;k++){
  reset_case(&r);claim_ok=true;
  if(k==0)clock_on=true;
  if(k==1)dma2=true;
  if(k==2)dma3=true;
  if(k==3)dma5=true;
  if(k==4)rg_on=true;
  assert(!signal_reader_try_start(&r,cb,&timer));
  assert(writes==0 && releases==1 && !r.e11_owner);
 }
 reset_case(&r);claim_ok=true;slot_ok=false;
 assert(!signal_reader_try_start(&r,cb,&timer));
 assert(!writes && !r.e11_owner && releases==1);
 reset_case(&r);claim_ok=true;
 active_cb=foreign;active_ctx=(void*)7;
 assert(!signal_reader_try_start(&r,cb,&timer));
 assert(active_cb==foreign && active_ctx==(void*)7 && !writes);
 reset_case(&r);claim_ok=true;
 assert(signal_reader_try_start(&r,cb,&timer));
 assert(clock_on && dma2 && dma3 && dma5 && rg_on);
 assert(active_cb==signal_reader_e11_exti_callback && r.e11_owner==owner_counter);
 assert(!signal_reader_try_start(&r,cb,&timer));
 flag_half=true;furi_hal_sw_digital_pin_dma_rx_isr(&r);
 assert(callbacks==1 && !flag_half);
 signal_reader_stop(&r);
 assert(!clock_on && !dma2 && !dma3 && !dma5 && !rg_on);
 assert(!active_cb && !r.e11_owner && releases==1);
 int before=writes;
 signal_reader_stop(&r);furi_hal_sw_digital_pin_dma_rx_isr(&r);
 assert(writes==before && !r.e11_owner);
 assert(signal_reader_try_start(&r,cb,&timer));signal_reader_stop(&r);
 reset_case(&r);claim_ok=true;
 assert(signal_reader_try_start(&r,cb,&timer));
 active_cb=foreign;before=writes;
 signal_reader_stop(&r);
 assert(r.e11_fault && r.e11_owner && writes==before && active_cb==foreign);
 reset_case(&r);claim_ok=true;release_ok=false;clock_on=true;
 assert(!signal_reader_try_start(&r,cb,&timer));
 assert(r.e11_owner && r.e11_fault && !writes);
 reset_case(&r);claim_ok=true;release_ok=false;
 assert(signal_reader_try_start(&r,cb,&timer));
 signal_reader_stop(&r);
 assert(r.e11_fault && r.e11_owner && !clock_on && !rg_on);
 before=writes;signal_reader_stop(&r);assert(writes==before);
 reset_case(&r);claim_ok=true;
 assert(signal_reader_try_start(&r,cb,&timer));
 clock_on=false;before=writes;
 furi_hal_sw_digital_pin_dma_rx_isr(&r);
 signal_reader_stop(&r);
 assert(r.e11_fault && r.e11_owner && writes==before);
 puts("E11 original SignalReader TIM16 DMA2 RG0 C start/ISR/STOP BUSY PASS");
 return 0;
}
"""
PARSER_STUB=r"""
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <assert.h>
#define furi_assert(x) assert(x)
typedef struct SignalReader{int dummy;} SignalReader;
typedef void(*SignalReaderCallback)(int,void*);
typedef void(*Iso15693ParserCallback)(int,void*);
typedef struct Iso15693Parser {
 SignalReader* signal_reader;
 Iso15693ParserCallback callback;
 void* context;
} Iso15693Parser;
static bool accept_reader;
static int starts,stops,reset_calls;
static bool signal_reader_try_start(SignalReader*r,SignalReaderCallback cb,void*ctx){
 assert(r && cb && ctx);starts++;return accept_reader;
}
static void signal_reader_stop(SignalReader*r){assert(r);stops++;}
static void iso15693_parser_reset(Iso15693Parser*p){assert(p);reset_calls++;}
static void signal_reader_callback(int event,void*context){(void)event;(void)context;}
"""
PARSER_RUN=r"""
static void cb(int event,void*context){(void)event;(void)context;}
int main(void){
 SignalReader reader={0};Iso15693Parser parser={.signal_reader=&reader};
 accept_reader=false;
 assert(!iso15693_parser_try_start(&parser,cb,&reader));
 assert(!parser.callback && !parser.context && starts==1 && reset_calls==1 && !stops);
 accept_reader=true;
 assert(iso15693_parser_try_start(&parser,cb,&reader));
 assert(parser.callback==cb && parser.context==&reader && starts==2);
 iso15693_parser_stop(&parser);assert(stops==1);
 puts("E11 genuine ISO15693 parser bool START denied/success C PASS");
 return 0;
}
"""

def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    s=(root/"lib/signal_reader/signal_reader.c").read_text()
    header=(root/"lib/signal_reader/signal_reader.h").read_text()
    parser=(root/"lib/signal_reader/parsers/iso15693/iso15693_parser.c").read_text()
    ph=(root/"lib/signal_reader/parsers/iso15693/iso15693_parser.h").read_text()
    nfc=(root/"targets/f7/furi_hal/furi_hal_nfc_iso15693.c").read_text()
    assert "/* E11 native NFC SignalReader TIM16/DMA2/DMAMUX V2 owner. */" in s
    assert "bool signal_reader_try_start(" in header and "bool iso15693_parser_try_start(" in ph
    assert "LL_DMAMUX_DisableRequestGen(DMAMUX1,LL_DMAMUX_REQ_GEN_0);" in s
    assert nfc.count("iso15693_parser_try_start(")==1
    assert "return FuriHalNfcEventAbortRequest;" in nfc[
        nfc.index("static FuriHalNfcEvent furi_hal_nfc_iso15693_wait_event("):
        nfc.index("static FuriHalNfcError furi_hal_nfc_iso15693_listener_tx(")]
    start=s[s.index("bool signal_reader_try_start("):]
    assert start.index("furi_hal_resource_lease_v2_try_acquire(") < start.index(
        "furi_hal_bus_enable(FuriHalBusTIM16);")
    assert start.index("furi_hal_gpio_try_add_int_callback(") < start.index(
        "furi_hal_bus_enable(FuriHalBusTIM16);")
    assert start.index("furi_hal_resource_lease_v2_try_acquire(") < start.index(
        "instance->callback = callback;")
    assert "if(!signal_reader_e11_ready(instance)) return;" in start
    mark=s.index("static void signal_reader_e11_exti_callback(")
    reader_src=s[s.index("struct SignalReader {"):s.index("#define GPIO_PIN_MAP(")]
    funcs=s[mark:]
    psrc=parser[parser.index("static bool iso15693_parser_start_signal_reader("):
                parser.index("static Iso15693ParserCommand iso15693_parser_parse_1_out_of_4(")]
    with tempfile.TemporaryDirectory(prefix="e11_signal_reader_") as tmp:
        d=Path(tmp);exe=d/"test"
        (d/"reader.c").write_text(STUB+"\n"+reader_src+"\n"+funcs+"\n"+RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                        "-Wno-pointer-to-int-cast","-pedantic",
                        str(d/"reader.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
        (d/"parser.c").write_text(PARSER_STUB+"\n"+psrc+"\n"+PARSER_RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        str(d/"parser.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 REAL SignalReader ISR/START/STOP + ISO parser BUSY C HOST PASS")
    print("Physical NFC and external CC1101 TX V2 owner still OPEN")

if __name__=="__main__":
    main()
