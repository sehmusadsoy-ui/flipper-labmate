#!/usr/bin/env python3
"""Actual pinned RFID field TIM1+TIM2+DMA2 C and firmware allocator fault gate."""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#define UNUSED(x) ((void)(x))
#define furi_check(x) assert(x)
#define FURI_CRITICAL_ENTER() ((void)0)
#define FURI_CRITICAL_EXIT() ((void)0)
typedef struct {uint32_t CNT;} SimTimer;
static SimTimer counter_timer,timeout_timer;
#define FURI_HAL_RFID_FIELD_COUNTER_TIMER (&counter_timer)
#define FURI_HAL_RFID_FIELD_TIMEOUT_TIMER (&timeout_timer)
#define FURI_HAL_RFID_FIELD_COUNTER_TIMER_BUS 2
#define FURI_HAL_RFID_FIELD_TIMEOUT_TIMER_BUS 1
#define FURI_HAL_RFID_FIELD_COUNTER_TIMER_CHANNEL 3
#define RFID_DMA 2
#define RFID_DMA_CH1_DEF 2,1
#define RFID_DMA_CH2_DEF 2,2
#define FURI_HAL_RFID_FIELD_DMAMUX_DMA 0
#define FURI_HAL_RFID_FIELD_FREQUENCY_MIN 100U
#define FURI_HAL_RFID_FIELD_FREQUENCY_MAX 200000U
#define FURI_HAL_LEASE_NATIVE_RFID_FIELD ((1U<<0)|(1U<<2)|(1U<<25)|(1U<<26))
#define LL_TIM_COUNTERMODE_UP 0
#define LL_TIM_CLOCKDIVISION_DIV1 0
#define LL_TIM_CLOCKSOURCE_EXT_MODE2 0
#define LL_TIM_CLOCKSOURCE_INTERNAL 0
#define LL_TIM_ETR_POLARITY_INVERTED 0
#define LL_TIM_ETR_PRESCALER_DIV1 0
#define LL_TIM_ETR_FILTER_FDIV1 0
#define LL_TIM_OCMODE_PWM1 0
#define LL_TIM_OCSTATE_ENABLE 0
#define LL_TIM_OCPOLARITY_HIGH 0
#define LL_DMA_DIRECTION_PERIPH_TO_MEMORY 0
#define LL_DMA_DIRECTION_MEMORY_TO_PERIPH 0
#define LL_DMA_MODE_CIRCULAR 0
#define LL_DMA_PERIPH_NOINCREMENT 0
#define LL_DMA_MEMORY_NOINCREMENT 0
#define LL_DMA_PDATAALIGN_WORD 0
#define LL_DMA_MDATAALIGN_WORD 0
#define LL_DMA_PRIORITY_MEDIUM 0
#define LL_DMA_PRIORITY_LOW 0
typedef struct {uint32_t OCMode,OCState,CompareValue;} LL_TIM_OC_InitTypeDef;
typedef struct {struct {uint32_t counter,set_tim_counter_cnt;} field;} RfidState;
static RfidState instance;
static RfidState* furi_hal_rfid=&instance;
static int writes,claims,releases,pin_writes;
static bool allow_claim,allow_release=true,tim1,tim2,dma1,dma2;
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
 assert(mask==FURI_HAL_LEASE_NATIVE_RFID_FIELD);claims++;
 return allow_claim?88U:0U;
}
bool furi_hal_resource_lease_release(uint32_t owner,uint32_t mask) {
 assert(owner==88U && mask==FURI_HAL_LEASE_NATIVE_RFID_FIELD);releases++;
 return allow_release;
}
bool furi_hal_bus_is_enabled(int b) {assert(b==1||b==2);return b==1?tim1:tim2;}
void furi_hal_bus_enable(int b) {
 assert(b==1||b==2);assert(!(b==1?tim1:tim2));
 if(b==1)tim1=true;else tim2=true;writes++;
}
void furi_hal_bus_disable(int b) {
 assert(b==1||b==2);assert(b==1?tim1:tim2);
 if(b==1)tim1=false;else tim2=false;writes++;
}
static bool is_dma(int ctrl,int ch) {
 assert(ctrl==2 && (ch==1||ch==2));
 return ch==1?dma1:dma2;
}
static void dma_enable(int ctrl,int ch) {
 assert(ctrl==2 && (ch==1||ch==2));
 if(ch==1)dma1=true;else dma2=true;writes++;
}
static void dma_deinit(int ctrl,int ch) {
 assert(ctrl==2 && (ch==1||ch==2));
 if(ch==1)dma1=false;else dma2=false;writes++;
}
#define LL_DMA_IsEnabledChannel is_dma
#define LL_DMA_EnableChannel dma_enable
#define LL_DMA_DeInit dma_deinit
static void furi_hal_rfid_pins_field(void) {pin_writes++;writes++;}
static void furi_hal_rfid_pins_reset(void) {pin_writes++;writes++;}
#define LL_TIM_SetPrescaler(...) (++writes)
#define LL_TIM_SetCounterMode(...) (++writes)
#define LL_TIM_SetAutoReload(...) (++writes)
#define LL_TIM_DisableARRPreload(...) (++writes)
#define LL_TIM_SetRepetitionCounter(...) (++writes)
#define LL_TIM_SetClockDivision(...) (++writes)
#define LL_TIM_SetClockSource(...) (++writes)
#define LL_TIM_ConfigETR(...) (++writes)
#define LL_TIM_OC_Init(...) ((void)(&TIM_OC_InitStruct),++writes)
#define LL_TIM_GenerateEvent_UPDATE(...) (++writes)
#define LL_TIM_OC_SetPolarity(...) (++writes)
#define LL_TIM_EnableDMAReq_UPDATE(...) (++writes)
#define LL_TIM_EnableAllOutputs(...) (++writes)
#define LL_TIM_DisableAllOutputs(...) (++writes)
#define LL_TIM_EnableCounter(...) (++writes)
#define LL_TIM_DisableCounter(...) (++writes)
#define LL_TIM_SetCounter(...) (++writes)
#define LL_TIM_EnableIT_UPDATE(...) (++writes)
#define LL_TIM_DisableIT_UPDATE(...) (++writes)
#define LL_DMA_SetMemoryAddress(...) (++writes)
#define LL_DMA_SetPeriphAddress(...) (++writes)
#define LL_DMA_ConfigTransfer(...) (++writes)
#define LL_DMA_SetDataLength(...) (++writes)
#define LL_DMA_SetPeriphRequest(...) (++writes)
"""
RUN=r"""
static void reset_case(void) {
 writes=claims=releases=pin_writes=0;
 allow_claim=false;allow_release=true;
 tim1=tim2=dma1=dma2=false;
 instance.field.counter=14;
 e11_rfid_field_handle=0U;e11_rfid_field_fault=false;
}
int main(void) {
 /* Mocked register macros must still exercise the actual timer objects. */
 (void)&counter_timer;
 (void)&timeout_timer;
 uint32_t freq=999U;
 reset_case();
 assert(!furi_hal_rfid_field_detect_try_start());
 furi_hal_rfid_field_detect_start();
 furi_hal_rfid_field_detect_stop();
 assert(!furi_hal_rfid_field_is_present(&freq) && freq==0U);
 assert(writes==0 && pin_writes==0 && claims==2 && releases==0);
 for(int i=0;i<4;i++) {
  reset_case();allow_claim=true;
  if(i==0)tim1=true;
  if(i==1)tim2=true;
  if(i==2)dma1=true;
  if(i==3)dma2=true;
  assert(!furi_hal_rfid_field_detect_try_start());
  assert(!writes && !pin_writes && releases==1 && !e11_rfid_field_handle);
  furi_hal_rfid_field_detect_stop();
  assert(!writes);
 }
 reset_case();allow_claim=true;allow_release=false;tim2=true;
 assert(!furi_hal_rfid_field_detect_try_start());
 assert(e11_rfid_field_fault && e11_rfid_field_handle==88U);
 tim2=false;
 assert(!furi_hal_rfid_field_detect_try_start());
 assert(!writes && claims==1);
 reset_case();allow_claim=true;
 assert(furi_hal_rfid_field_detect_try_start());
 assert(tim1 && tim2 && dma1 && dma2 && pin_writes==1);
 assert(furi_hal_rfid_field_is_present(&freq) && freq==140U);
 int before=claims;
 assert(!furi_hal_rfid_field_detect_try_start() && claims==before);
 furi_hal_rfid_field_detect_stop();
 assert(!tim1&&!tim2&&!dma1&&!dma2 &&
        !e11_rfid_field_handle && !e11_rfid_field_fault &&
        pin_writes==2 && releases==1);
 before=writes;
 furi_hal_rfid_field_detect_stop();
 assert(writes==before && releases==1);
 assert(!furi_hal_rfid_field_is_present(&freq) && freq==0U);
 assert(furi_hal_rfid_field_detect_try_start());furi_hal_rfid_field_detect_stop();
#ifdef TEST_FAILED_RELEASE
 reset_case();allow_claim=true;allow_release=false;
 assert(furi_hal_rfid_field_detect_try_start());
 furi_hal_rfid_field_detect_stop();
 assert(!tim1 && !tim2 && e11_rfid_field_handle==88U && e11_rfid_field_fault);
 before=writes;
 assert(!furi_hal_rfid_field_detect_try_start());
 furi_hal_rfid_field_detect_stop();
 assert(writes==before && claims==1);
#else
 reset_case();allow_claim=true;
 assert(furi_hal_rfid_field_detect_try_start());
 tim1=false;
 before=writes;
 assert(!furi_hal_rfid_field_is_present(&freq) && freq==0U);
 furi_hal_rfid_field_detect_stop();
 assert(writes==before && e11_rfid_field_fault && e11_rfid_field_handle==88U);
 assert(releases==0);
#endif
 puts("E11 original RFID FIELD C: zero-write BUSY, atomic TIM1/TIM2/DMA, STOP/fault PASS");
 return 0;
}
"""
MASK=r"""
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"RFID field allocator FAIL line %d\n",__LINE__);exit(1);}}while(0)
int main(void) {
 uint32_t x=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_FIELD);
 REQUIRE(x);
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_TIMERS));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_RX_TIM2));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3));
 REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_MONITOR_PC0));
 REQUIRE(!furi_hal_resource_lease_release(x,FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1));
 REQUIRE(furi_hal_resource_lease_release(x,FURI_HAL_LEASE_NATIVE_RFID_FIELD));
 REQUIRE(!furi_hal_resource_lease_release(x,FURI_HAL_LEASE_NATIVE_RFID_FIELD));
 puts("E11 real firmware RFID field atomic allocator overlaps TIM1/TIM2/DMA PASS");
 return 0;
}
"""

def main()->None:
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    s=(root/"targets/f7/furi_hal/furi_hal_rfid.c").read_text()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    res=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    api=(root/"targets/f7/api_symbols.csv").read_text()
    pub=(root/"targets/f7/furi_hal/furi_hal_rfid.h").read_text()
    marker="/* E11 native RFID field atomic TIM1/TIM2/DMA2 owner. */"
    assert marker in s and "bool furi_hal_rfid_field_detect_try_start(void)" in pub
    assert "mask == FURI_HAL_LEASE_NATIVE_RFID_FIELD" in res
    assert "Function,+,furi_hal_rfid_field_detect_try_start,_Bool," in api
    helper=s[s.index("static void furi_hal_rfid_field_tim_setup(void) {"):s.index(marker)]
    field=s[s.index(marker):]
    assert field.index("furi_hal_resource_lease_try_acquire(") < field.index(
        "furi_hal_rfid_pins_field();")
    assert field.index("furi_hal_resource_lease_try_acquire(") < field.index(
        "furi_hal_rfid_field_tim_setup();")
    assert "if(!e11_rfid_field_ready()) return;" in field
    assert "*frequency=0U;" in field
    with tempfile.TemporaryDirectory(prefix="e11_native_rfid_field_") as tmpdir:
        d=Path(tmpdir);exe=d/"test"
        (d/"native.c").write_text(STUB+"\n"+helper+"\n"+field+"\n"+RUN)
        for failed in (False,True):
            flags=["-DTEST_FAILED_RELEASE=1"] if failed else []
            subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                            "-Wno-pointer-to-int-cast","-pedantic","-O0",*flags,
                            str(d/"native.c"),"-o",str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
        pre=r"""
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
static pthread_mutex_t critical=PTHREAD_MUTEX_INITIALIZER;
#define FURI_CRITICAL_ENTER() do{if(pthread_mutex_lock(&critical))abort();}while(0)
#define FURI_CRITICAL_EXIT() do{if(pthread_mutex_unlock(&critical))abort();}while(0)
"""
        masks=h[h.index("enum {\n    FuriHalLeaseTim1"):
                h.index("/* Returns unique nonzero")]
        allocator=res[res.index("/* Firmware-owned E11 lease primitive"):
                      res.index("const GpioPinRecord* furi_hal_resources_pin_by_number")]
        (d/"lease.c").write_text(pre+masks+allocator+MASK)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(d/"lease.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("RFID native field actual production C and E11 allocator HOST PASS")
    print("Native internal GPIO/EXTI and physical field recovery still OPEN")

if __name__=="__main__":
    main()
