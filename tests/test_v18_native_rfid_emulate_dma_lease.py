#!/usr/bin/env python3
"""Real pinned RFID TIM2 DMA2 emulation C + genuine firmware allocator host tests.

No device, RF transmitter or microSD interaction. Native caller BUSY still OPEN.
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
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#define UNUSED(x) ((void)(x))
#define furi_check(x) assert(x)
#define FURI_CRITICAL_ENTER() ((void)0)
#define FURI_CRITICAL_EXIT() ((void)0)
#define FURI_HAL_RFID_EMULATE_TIMER 2
#define FURI_HAL_RFID_EMULATE_TIMER_BUS 2
#define FURI_HAL_RFID_EMULATE_TIMER_CHANNEL 3
#define RFID_DMA 2
#define LL_DMA_CHANNEL_1 1
#define RFID_DMA_CH1_CHANNEL 1
#define RFID_DMA_CH1_DEF 2,1
#define RFID_DMA_CH2_DEF 2,2
#define RFID_DMA_CH1_IRQ 6
#define LL_TIM_CHANNEL_CH3 3
#define LL_TIM_CLOCKDIVISION_DIV1 0
#define LL_TIM_CLOCKSOURCE_EXT_MODE2 0
#define LL_TIM_COUNTERMODE_UP 0
#define LL_TIM_ETR_POLARITY_INVERTED 0
#define LL_TIM_ETR_PRESCALER_DIV1 0
#define LL_TIM_ETR_FILTER_FDIV1 0
#define LL_TIM_OCMODE_PWM1 0
#define LL_TIM_OCSTATE_ENABLE 0
#define LL_TIM_OCPOLARITY_HIGH 0
#define LL_DMA_DIRECTION_MEMORY_TO_PERIPH 0
#define LL_DMA_MODE_CIRCULAR 0
#define LL_DMA_PERIPH_NOINCREMENT 0
#define LL_DMA_MEMORY_INCREMENT 0
#define LL_DMA_PDATAALIGN_WORD 0
#define LL_DMA_MDATAALIGN_WORD 0
#define LL_DMAMUX_REQ_TIM2_UP 0
#define LL_DMA_MODE_NORMAL 0
#define FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA ((1U<<2)|(1U<<25)|(1U<<26))
typedef void(*FuriHalRfidDMACallback)(bool,void*);
typedef struct {
 FuriHalRfidDMACallback dma_callback;
 void* context;
} RfidState;
static RfidState sample;
static RfidState* furi_hal_rfid=&sample;
typedef struct {uint32_t OCMode,OCState,CompareValue;} LL_TIM_OC_InitTypeDef;
typedef struct {
 uint32_t PeriphOrM2MSrcAddress,MemoryOrM2MDstAddress,Direction,Mode;
 uint32_t PeriphOrM2MSrcIncMode,MemoryOrM2MDstIncMode;
 uint32_t PeriphOrM2MSrcDataSize,MemoryOrM2MDstDataSize;
 uint32_t NbData,PeriphRequest,Priority;
} LL_DMA_InitTypeDef;
static int writes,claims,releases,irq_calls,pin_writes;
static bool allow_claim,allow_release=true,clock_live,dma1,dma2,ht,tc;
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
 assert(mask==FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA);
 claims++;return allow_claim?68U:0U;
}
bool furi_hal_resource_lease_release(uint32_t h,uint32_t mask) {
 assert(h==68U && mask==FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA);
 releases++;return allow_release;
}
bool furi_hal_bus_is_enabled(int bus) {assert(bus==2);return clock_live;}
void furi_hal_bus_enable(int bus) {
 assert(bus==2&&!clock_live);clock_live=true;writes++;
}
void furi_hal_bus_disable(int bus) {
 assert(bus==2&&clock_live);clock_live=false;writes++;
}
uint32_t ll_dma_enabled(int controller,int channel) {
 assert(controller==2 && (channel==1||channel==2));
 return (channel==1?dma1:dma2);
}
#define LL_DMA_IsEnabledChannel ll_dma_enabled
void dma_enable(int controller,int channel) {
 assert(controller==2);(channel==1? (dma1=true):(dma2=true));writes++;
}
void dma_deinit(int controller,int channel) {
 assert(controller==2);(channel==1? (dma1=false):(dma2=false));writes++;
}
static void furi_hal_rfid_pins_emulate(void) {pin_writes++;writes++;}
static void furi_hal_interrupt_set_isr(int irq,void(*isr)(void*),void* ctx) {
 assert(irq==6);(void)isr;(void)ctx;writes++;
}
#define LL_TIM_SetPrescaler(...) (++writes)
#define LL_TIM_SetCounterMode(...) (++writes)
#define LL_TIM_SetAutoReload(...) (++writes)
#define LL_TIM_DisableARRPreload(...) (++writes)
#define LL_TIM_SetRepetitionCounter(...) (++writes)
#define LL_TIM_SetClockDivision(...) (++writes)
#define LL_TIM_SetClockSource(...) (++writes)
#define LL_TIM_ConfigETR(...) (++writes)
#define LL_TIM_OC_Init(...) (++writes)
#define LL_TIM_GenerateEvent_UPDATE(...) (++writes)
#define LL_TIM_OC_SetPolarity(...) (++writes)
#define LL_TIM_EnableDMAReq_UPDATE(...) (++writes)
#define LL_TIM_EnableAllOutputs(...) (++writes)
#define LL_TIM_DisableAllOutputs(...) (++writes)
#define LL_TIM_SetCounter(...) (++writes)
#define LL_TIM_EnableCounter(...) (++writes)
#define LL_TIM_DisableCounter(...) (++writes)
#define LL_DMA_Init(...) (++writes)
#define LL_DMA_EnableChannel dma_enable
#define LL_DMA_DeInit dma_deinit
#define LL_DMA_EnableIT_TC(...) (++writes)
#define LL_DMA_EnableIT_HT(...) (++writes)
#define LL_DMA_DisableIT_TC(...) (++writes)
#define LL_DMA_DisableIT_HT(...) (++writes)
#define LL_DMA_IsActiveFlag_HT1(...) (ht)
#define LL_DMA_IsActiveFlag_TC1(...) (tc)
#define LL_DMA_ClearFlag_HT1(...) (ht=false,++writes)
#define LL_DMA_ClearFlag_TC1(...) (tc=false,++writes)
"""
RUN=r"""
static void dma_callback(bool half,void* context) {
 assert(context==&sample);
 assert(half==((irq_calls % 2)==0));
 irq_calls++;
}
static uint32_t durations[8],pulses[8];
static void reset(void) {
 writes=claims=releases=irq_calls=pin_writes=0;
 allow_claim=false;allow_release=true;
 clock_live=dma1=dma2=ht=tc=false;
 sample.dma_callback=NULL;sample.context=NULL;
 e11_rfid_emulate_handle=0U;e11_rfid_emulate_fault=false;
}
static bool start(void) {
 return furi_hal_rfid_tim_emulate_dma_try_start(
    durations,pulses,8,dma_callback,&sample);
}
int main(void) {
 reset();
 assert(!start());furi_hal_rfid_tim_emulate_dma_stop();
 furi_hal_rfid_dma_isr(NULL);
 assert(!writes && claims==1 && !irq_calls);
 furi_hal_rfid_tim_emulate_dma_start(durations,pulses,8,dma_callback,&sample);
 furi_hal_rfid_tim_emulate_dma_stop();
 assert(!writes && claims==2);
 reset();allow_claim=true;
 assert(!furi_hal_rfid_tim_emulate_dma_try_start(NULL,pulses,8,dma_callback,&sample));
 assert(!furi_hal_rfid_tim_emulate_dma_try_start(durations,pulses,0,dma_callback,&sample));
 assert(!furi_hal_rfid_tim_emulate_dma_try_start(durations,pulses,8,NULL,&sample));
 assert(!claims && !writes);
 /* All three distinct legacy preflights deny with NO hardware changes. */
 for(int i=0;i<3;i++) {
  reset();allow_claim=true;
  if(i==0)clock_live=true;
  if(i==1)dma1=true;
  if(i==2)dma2=true;
  assert(!start());
  assert(!writes && !pin_writes && releases==1);
  furi_hal_rfid_tim_emulate_dma_stop();assert(!writes);
 }
 reset();allow_claim=true;allow_release=false;dma1=true;
 assert(!start());
 assert(e11_rfid_emulate_handle==68U && e11_rfid_emulate_fault);
 dma1=false;
 assert(!start());assert(claims==1 && !writes);
 /* Atomic normal START/ISR/STOP, no double-release. */
 reset();allow_claim=true;
 assert(start());assert(dma1 && dma2 && clock_live && pin_writes==1);
 int count=claims;
 assert(!start() && claims==count);
 ht=tc=true;int before=writes;
 furi_hal_rfid_dma_isr(NULL);
 assert(irq_calls==2 && !ht && !tc && writes==before+2);
 furi_hal_rfid_tim_emulate_dma_stop();
 assert(!dma1&&!dma2&&!clock_live && releases==1 &&
        !e11_rfid_emulate_handle && sample.dma_callback==NULL);
 before=writes;
 furi_hal_rfid_tim_emulate_dma_stop();furi_hal_rfid_dma_isr(NULL);
 assert(writes==before && releases==1);
 assert(start());furi_hal_rfid_tim_emulate_dma_stop();
#ifdef TEST_RELEASE_FAILURE
 reset();allow_claim=true;allow_release=false;
 assert(start());furi_hal_rfid_tim_emulate_dma_stop();
 assert(!clock_live && e11_rfid_emulate_fault && e11_rfid_emulate_handle==68U);
 before=writes;
 assert(!start());furi_hal_rfid_tim_emulate_dma_stop();
 assert(writes==before && claims==1);
#else
 reset();allow_claim=true;
 assert(start());clock_live=false;ht=tc=true;
 before=writes;
 furi_hal_rfid_dma_isr(NULL);
 furi_hal_rfid_tim_emulate_dma_stop();
 assert(writes==before && irq_calls==0 && releases==0);
 assert(e11_rfid_emulate_fault && e11_rfid_emulate_handle==68U);
#endif
 puts("E11 RFID original DMA C: denied zero writes, ISR/STOP, sticky faults PASS");
 return 0;
}
"""
MASK=r"""
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"RFID emulate lease failure at %d\n",__LINE__);exit(1);}}while(0)
int main(void) {
 uint32_t r=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA);
 REQUIRE(r);
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_RX_TIM2));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3));
 REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1));
 REQUIRE(!furi_hal_resource_lease_release(r,FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL));
 REQUIRE(furi_hal_resource_lease_release(r,FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA));
 REQUIRE(!furi_hal_resource_lease_release(r,FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA));
 puts("E11 REAL firmware allocator: RFID TIM2/DMA vs IR TX/RX/Counter PASS");
 return 0;
}
"""

def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    s=(root/"targets/f7/furi_hal/furi_hal_rfid.c").read_text()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    r=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    pub=(root/"targets/f7/furi_hal/furi_hal_rfid.h").read_text()
    api=(root/"targets/f7/api_symbols.csv").read_text()
    assert "/* E11 native RFID emulate TIM2/DMA2 composite owner. */" in s
    assert "FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA" in h
    assert "mask == FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA" in r
    assert "bool furi_hal_rfid_tim_emulate_dma_try_start(" in pub
    assert "Function,+,furi_hal_rfid_tim_emulate_dma_try_start,_Bool," in api
    # Original pinned helper, not a rewritten imitation.
    helper=s[s.index("static void furi_hal_rfid_tim_emulate(void) {"):
             s.index("/* E11 native RFID capture TIM2 owner. */")]
    source=s[s.index("/* E11 native RFID emulate TIM2/DMA2 composite owner. */"):
             s.index("void furi_hal_rfid_set_read_period(uint32_t period) {")]
    assert source.index("furi_hal_resource_lease_try_acquire(") < source.index(
        "furi_hal_rfid_pins_emulate();")
    assert source.index("furi_hal_resource_lease_try_acquire(") < source.index(
        "furi_hal_rfid->dma_callback = callback;")
    assert "if(!e11_rfid_emulate_ready()) return;" in source
    with tempfile.TemporaryDirectory(prefix="e11_rfid_dma_") as folder:
        tmp=Path(folder);exe=tmp/"host"
        (tmp/"driver.c").write_text(STUB+"\n"+helper+"\n"+source+"\n"+RUN)
        for fail in (False,True):
            flags=["-DTEST_RELEASE_FAILURE=1"] if fail else []
            subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                            "-Wno-pointer-to-int-cast","-pedantic","-O0",*flags,
                            str(tmp/"driver.c"),"-o",str(exe)],check=True)
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
        allocator=r[r.index("/* Firmware-owned E11 lease primitive"):
                    r.index("const GpioPinRecord* furi_hal_resources_pin_by_number")]
        (tmp/"lease.c").write_text(pre+masks+allocator+MASK)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(tmp/"lease.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("RFID DMA native production C + genuine E11 allocator host PASS")
    print("Native emulation callers, RFID field, SubGHz, real-device still OPEN")

if __name__=="__main__":
    main()
