#!/usr/bin/env python3
"""Exercise actual pinned SubGHz TX ISR/START/STOP C and firmware allocator.

Strict host fault injection, not a radio/device/transmit PASS.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#define UNUSED(x) ((void)(x))
#define FURI_CRITICAL_ENTER() ((void)0)
#define FURI_CRITICAL_EXIT() ((void)0)
#define TAG "SubGHz"
#define FURI_LOG_D(tag,fmt,...) ((void)printf(fmt, __VA_ARGS__))
#define FURI_LOG_W(...) ((void)0)
enum { FuriHalBusTIM2=2, SubGhzStateIdle=1, SubGhzStateAsyncTx=2,
 SubGhzRegulationTxRx=1,SubGhzRegulationOnlyRx=0 };
enum { GpioModeAltFunctionPushPull=1,GpioModeAnalog=2,
 GpioPullNo=0,GpioSpeedLow=0,GpioAltFn1TIM2=1 };
enum { LL_DMA_CHANNEL_1=1,LL_DMA_CHANNEL_2=2 };
enum { LL_DMA_DIRECTION_MEMORY_TO_PERIPH=0,LL_DMA_MODE_CIRCULAR=0,
 LL_DMA_PERIPH_NOINCREMENT=0,LL_DMA_MEMORY_INCREMENT=0,
 LL_DMA_PDATAALIGN_WORD=0,LL_DMA_MDATAALIGN_WORD=0,
 LL_DMAMUX_REQ_TIM2_UP=0,LL_DMA_PRIORITY_VERYHIGH=0,
 LL_DMA_PRIORITY_HIGH=0,LL_TIM_COUNTERMODE_UP=0,
 LL_TIM_CLOCKDIVISION_DIV1=0,LL_TIM_CLOCKSOURCE_INTERNAL=0,
 LL_TIM_OCMODE_TOGGLE=0,LL_TIM_OCSTATE_DISABLE=0,
 LL_TIM_OCPOLARITY_HIGH=0,LL_TIM_CHANNEL_CH2=2,GPIO_NUMBER=16 };
typedef struct {uint32_t BSRR;} SimPort;
typedef struct {SimPort* port;uint32_t pin;} GpioPin;
static SimPort pa,pb;
static const GpioPin gpio_cc1101_g0={&pa,2};
static const GpioPin gpio_ext_pa7={&pa,128};
static const GpioPin gpio_ext_pb3={&pb,8};
typedef int LevelDuration;
typedef LevelDuration (*FuriHalSubGhzAsyncTxCallback)(void*);
typedef struct {uint32_t ARR;} SimTimer;
static SimTimer timer2;
#define TIM2 (&timer2)
#define DMA2 2
#define SUBGHZ_DMA 2
#define LL_DMA_CHANNEL_1 1
#define SUBGHZ_DMA_CH1_CHANNEL 1
#define SUBGHZ_DMA_CH1_DEF 2,1
#define SUBGHZ_DMA_CH2_DEF 2,2
#define SUBGHZ_DMA_CH1_IRQ 8
#define FURI_HAL_SUBGHZ_ASYNC_TX_BUFFER_FULL 256
#define FURI_HAL_SUBGHZ_ASYNC_TX_BUFFER_HALF 128
#define FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_BASE ((1U<<2)|(1U<<25))
#define FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PA7 ((1U<<2)|(1U<<25)|(1U<<26)|(1U<<1))
#define FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PB3 ((1U<<2)|(1U<<25)|(1U<<26)|(1U<<3))
typedef struct {uint32_t PeriphOrM2MSrcAddress,MemoryOrM2MDstAddress;
 uint32_t Direction,Mode,PeriphOrM2MSrcIncMode,MemoryOrM2MDstIncMode;
 uint32_t PeriphOrM2MSrcDataSize,MemoryOrM2MDstDataSize,NbData,PeriphRequest,Priority;
} LL_DMA_InitTypeDef;
typedef struct {uint32_t OCMode,OCState,OCNState,CompareValue,OCPolarity;} LL_TIM_OC_InitTypeDef;
typedef struct {int state;} SimMiddleware;
typedef struct {uint32_t* buffer;FuriHalSubGhzAsyncTxCallback callback;
 void* callback_context;uint64_t duty_low,duty_high;SimMiddleware middleware;
} FuriHalSubGhzAsyncTx;
static FuriHalSubGhzAsyncTx furi_hal_subghz_async_tx;
typedef struct {int state,regulation;const GpioPin* async_mirror_pin;} SimSubGhz;
static SimSubGhz furi_hal_subghz={SubGhzStateIdle,SubGhzRegulationTxRx,NULL};
static uint32_t e11_subghz_tx_handle,e11_subghz_tx_mask;
static bool e11_subghz_tx_fault;
static uint32_t furi_hal_subghz_debug_gpio_buff[2];
static int claims,releases,writes,pin_writes,radio_stops,debug_stops;
static bool claim_ok,release_ok=true,bus_live,chan1,chan2,fail_malloc,flag_ht,flag_tc;
static uint32_t expected_mask;
static void* tx_malloc(size_t n) {return fail_malloc?NULL:calloc(1,n);}
#define malloc tx_malloc
static bool furi_hal_bus_is_enabled(int bus) {assert(bus==2);return bus_live;}
static void furi_hal_bus_enable(int bus) {assert(bus==2&&!bus_live);bus_live=true;writes++;}
static void furi_hal_bus_disable(int bus) {assert(bus==2&&bus_live);bus_live=false;writes++;}
static uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
 assert(mask==expected_mask);claims++;return claim_ok?79U:0U;
}
static bool furi_hal_resource_lease_release(uint32_t handle,uint32_t mask) {
 assert(handle==79U && mask==expected_mask);releases++;return release_ok;
}
static bool dma_enabled(int controller,int channel) {
 assert(controller==2);return channel==1?chan1:chan2;
}
static void dma_enable(int controller,int channel) {
 assert(controller==2);if(channel==1)chan1=true;else chan2=true;writes++;
}
static void dma_deinit(int controller,int channel) {
 assert(controller==2);if(channel==1)chan1=false;else chan2=false;writes++;
}
#define LL_DMA_IsEnabledChannel dma_enabled
#define LL_DMA_EnableChannel dma_enable
#define LL_DMA_DeInit dma_deinit
#define LL_DMA_DisableChannel dma_deinit
#define LL_DMA_Init(...) ((void)(&dma_config),++writes)
#define LL_DMA_SetDataLength(...) (++writes)
#define LL_DMA_EnableIT_TC(...) (++writes)
#define LL_DMA_EnableIT_HT(...) (++writes)
#define LL_DMA_DisableIT_TC(...) (++writes)
#define LL_DMA_DisableIT_HT(...) (++writes)
#define LL_DMA_IsActiveFlag_HT1(...) (flag_ht)
#define LL_DMA_IsActiveFlag_TC1(...) (flag_tc)
#define LL_DMA_ClearFlag_HT1(...) (flag_ht=false,++writes)
#define LL_DMA_ClearFlag_TC1(...) (flag_tc=false,++writes)
#define furi_hal_gpio_init_ex(...) (pin_writes++,writes++)
#define furi_hal_gpio_init(...) (pin_writes++,writes++)
#define furi_hal_gpio_write(...) (pin_writes++,writes++)
#define furi_hal_interrupt_set_isr(...) (++writes)
#define LL_TIM_SetCounterMode(...) (++writes)
#define LL_TIM_SetClockDivision(...) (++writes)
#define LL_TIM_SetPrescaler(...) (++writes)
#define LL_TIM_SetAutoReload(...) (++writes)
#define LL_TIM_SetClockSource(...) (++writes)
#define LL_TIM_DisableARRPreload(...) (++writes)
#define LL_TIM_OC_Init(...) ((void)(&TIM_OC_InitStruct),++writes)
#define LL_TIM_OC_DisableFast(...) (++writes)
#define LL_TIM_DisableMasterSlaveMode(...) (++writes)
#define LL_TIM_EnableDMAReq_UPDATE(...) (++writes)
#define LL_TIM_CC_EnableChannel(...) (++writes)
#define LL_TIM_SetCounter(...) (++writes)
#define LL_TIM_EnableCounter(...) (++writes)
#define LL_TIM_GetAutoReload(...) (timer2.ARR)
static bool furi_hal_subghz_start_debug(void) {
 if(furi_hal_subghz.async_mirror_pin){writes++;return true;}
 return false;
}
static bool furi_hal_subghz_stop_debug(void) {
 if(furi_hal_subghz.async_mirror_pin){debug_stops++;writes++;return true;}
 return false;
}
static void furi_hal_subghz_async_tx_middleware_idle(SimMiddleware* middleware) {
 middleware->state=0;
}
static void furi_hal_subghz_async_tx_refill(uint32_t* buffer,size_t count) {
 assert(buffer && count); /* Real refill is not compiled into this focused gate. */
}
static void furi_hal_subghz_tx(void) {writes++;}
static void furi_hal_subghz_idle(void) {radio_stops++;writes++;}
"""
RUN=r"""
static LevelDuration cb(void* ctx) {(void)ctx;return 1;}
static void reset(void) {
 claims=releases=writes=pin_writes=radio_stops=debug_stops=0;
 claim_ok=false;release_ok=true;
 bus_live=chan1=chan2=fail_malloc=flag_ht=flag_tc=false;
 expected_mask=FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_BASE;
 furi_hal_subghz.state=SubGhzStateIdle;
 furi_hal_subghz.regulation=SubGhzRegulationTxRx;
 furi_hal_subghz.async_mirror_pin=NULL;
 e11_subghz_tx_handle=e11_subghz_tx_mask=0U;e11_subghz_tx_fault=false;
 furi_hal_subghz_async_tx.buffer=NULL;
 furi_hal_subghz_async_tx.callback=NULL;
}
static bool start(void) {return furi_hal_subghz_start_async_tx(cb,&furi_hal_subghz);}
int main(void) {
 reset();
 assert(!start());furi_hal_subghz_stop_async_tx();
 furi_hal_subghz_async_tx_dma_isr(NULL);
 assert(!writes && !pin_writes && claims==1 && !radio_stops);
 reset();claim_ok=true;furi_hal_subghz.regulation=SubGhzRegulationOnlyRx;
 assert(!start() && !claims && !writes);
 for(int n=0;n<2;n++){
  reset();claim_ok=true;
  if(n==0)bus_live=true;else chan1=true;
  assert(!start());
  assert(!writes&&!pin_writes && releases==1 && !e11_subghz_tx_handle);
 }
 reset();claim_ok=true;fail_malloc=true;
 assert(!start());
 assert(releases==1 && !writes && !pin_writes &&
        furi_hal_subghz.state==SubGhzStateIdle);
 reset();claim_ok=true;
 assert(start());
 assert(bus_live && chan1 && !chan2 && pin_writes>0);
 int count=claims;
 assert(!start() && claims==count);
 assert(!furi_hal_subghz_is_async_tx_complete());
 furi_hal_subghz_stop_async_tx();
 assert(!bus_live&&!chan1&&!e11_subghz_tx_handle && releases==1 &&
        radio_stops==1);
 int before=writes;
 furi_hal_subghz_stop_async_tx();
 furi_hal_subghz_async_tx_dma_isr(NULL);
 assert(writes==before && releases==1);
 assert(start());furi_hal_subghz_stop_async_tx();
 reset();claim_ok=true;furi_hal_subghz.async_mirror_pin=&gpio_ext_pa7;
 expected_mask=FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PA7;
 assert(start() && chan1 && chan2);
 furi_hal_subghz_stop_async_tx();
 assert(!chan1&&!chan2 && debug_stops==1);
 reset();claim_ok=true;furi_hal_subghz.async_mirror_pin=&gpio_ext_pb3;
 expected_mask=FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PB3;
 assert(start() && chan1 && chan2);
 furi_hal_subghz_stop_async_tx();
 reset();claim_ok=true;furi_hal_subghz.async_mirror_pin=&gpio_cc1101_g0;
 assert(!start() && !claims && !pin_writes);
 reset();claim_ok=true;release_ok=false;bus_live=true;
 assert(!start() && e11_subghz_tx_handle && e11_subghz_tx_fault);
 bus_live=false;assert(!start() && claims==1 && !writes);
#ifdef FAIL_FINAL_RELEASE
 reset();claim_ok=true;release_ok=false;
 assert(start());furi_hal_subghz_stop_async_tx();
 assert(e11_subghz_tx_fault && e11_subghz_tx_handle && !bus_live);
 before=writes;assert(!start());
 furi_hal_subghz_stop_async_tx();assert(writes==before);
#else
 reset();claim_ok=true;
 assert(start());bus_live=false;before=writes;
 furi_hal_subghz_async_tx_dma_isr(NULL);
 furi_hal_subghz_stop_async_tx();
 assert(writes==before && e11_subghz_tx_fault && e11_subghz_tx_handle &&
        !radio_stops && releases==0);
#endif
 puts("E11 original SubGHz TX C DMA2+TIM2 BUSY/ISR/STOP mirror/fault PASS");
 return 0;
}
"""
MASK=r"""
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"SubGHz TX lease FAIL %d\n",__LINE__);exit(1);}}while(0)
int main(void) {
 uint32_t t=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_BASE);
 REQUIRE(t);
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_FIELD));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL));
 REQUIRE(furi_hal_resource_lease_release(t,FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_BASE));
 uint32_t e=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PA7);
 REQUIRE(e);
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7));
 REQUIRE(furi_hal_resource_lease_release(e,FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PA7));
 uint32_t p=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PB3);
 REQUIRE(p);
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3));
 REQUIRE(furi_hal_resource_lease_release(p,FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PB3));
 puts("E11 real firmware SubGHz TX TIM2/DMA2/PA7/PB3 allocator PASS");
 return 0;
}
"""

def main()->None:
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    s=(root/"targets/f7/furi_hal/furi_hal_subghz.c").read_text()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    r=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    assert "/* E11 native SubGHz TX TIM2/DMA2 lease owner. */" in s
    assert "mask == FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_BASE" in r
    assert "if(!e11_subghz_tx_ready()) return;" in s
    seg=s[s.index("/* E11 native SubGHz TX TIM2/DMA2 lease owner. */"):
          s.index("void furi_hal_subghz_stop_async_tx(void) {")]
    stop=s[s.index("void furi_hal_subghz_stop_async_tx(void) {"):]
    # Source contains actual DMA ISR and TX START; no separate void substitute.
    assert seg.index("furi_hal_resource_lease_try_acquire(") < seg.index(
        "furi_hal_subghz_async_tx.callback = callback;")
    assert seg.index("furi_hal_resource_lease_try_acquire(") < seg.index(
        "furi_hal_gpio_init_ex(")
    assert "if(!e11_subghz_tx_ready()) return;" in stop
    assert "furi_hal_resource_lease_release(" in seg
    with tempfile.TemporaryDirectory(prefix="e11_subghz_tx_") as folder:
        d=Path(folder);exe=d/"test"
        source=seg+stop[:stop.index("\n}",stop.index("void furi_hal_subghz_stop_async_tx(void) {"))+2]
        (d/"tx.c").write_text(STUB+"\n"+source+"\n"+RUN)
        for failure in (False,True):
            flags=["-DFAIL_FINAL_RELEASE=1"] if failure else []
            subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                            "-Wno-pointer-to-int-cast","-O0",*flags,str(d/"tx.c"),"-o",str(exe)],
                           check=True)
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
        (d/"allocator.c").write_text(pre+masks+allocator+MASK)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(d/"allocator.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 actual native SubGHz TX DMA C+firmware lease allocator HOST PASS")
    print("Not device RF/GUI/physical co-existence PASS.")

if __name__=="__main__":
    main()
