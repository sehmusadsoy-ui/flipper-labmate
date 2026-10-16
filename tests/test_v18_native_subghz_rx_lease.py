#!/usr/bin/env python3
"""E11 pinned original SubGHz RX TIM2 ISR/START/STOP C + real allocator host.

No radio device, firmware install, external plugin or physical RF inference.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <assert.h>
#define UNUSED(x) ((void)(x))
#define FURI_CRITICAL_ENTER() ((void)0)
#define FURI_CRITICAL_EXIT() ((void)0)
#define TAG "SubGHz"
#define FURI_LOG_W(...) ((void)0)
enum { FuriHalBusTIM2=2, SubGhzStateIdle=1, SubGhzStateAsyncRx=2 };
enum { GpioModeAltFunctionPushPull=1,GpioModeAnalog=2,GpioPullNo=0,
 GpioSpeedLow=0,GpioAltFn1TIM2=1 };
enum { FuriHalInterruptIdTIM2=7 };
enum { LL_TIM_COUNTERMODE_UP=0,LL_TIM_CLOCKDIVISION_DIV4=0,
 LL_TIM_CLOCKSOURCE_INTERNAL=0, LL_TIM_TS_TI2FP2=0,
 LL_TIM_SLAVEMODE_RESET=0, LL_TIM_TRGO_RESET=0,
 LL_TIM_CHANNEL_CH1=1, LL_TIM_CHANNEL_CH2=2,
 LL_TIM_ACTIVEINPUT_INDIRECTTI=0,LL_TIM_ICPSC_DIV1=0,
 LL_TIM_IC_POLARITY_FALLING=0,LL_TIM_ACTIVEINPUT_DIRECTTI=0,
 LL_TIM_IC_POLARITY_RISING=0,LL_TIM_IC_FILTER_FDIV32_N8=0 };
typedef struct {int port;int pin;} GpioPin;
static const GpioPin gpio_ext_pa7={1,7},gpio_ext_pb3={2,3};
static const GpioPin gpio_cc1101_g0={1,1};
typedef void (*FuriHalSubGhzCaptureCallback)(bool,uint32_t,void*);
typedef struct {uint32_t Prescaler,CounterMode,Autoreload,ClockDivision;} LL_TIM_InitTypeDef;
typedef struct {volatile int state;const GpioPin* async_mirror_pin;} SimSubGhz;
static SimSubGhz furi_hal_subghz={.state=SubGhzStateIdle,.async_mirror_pin=NULL};
static int claims,releases,writes,callbacks,debug_stop,radio_idle;
static bool claim_allowed,release_allowed=true,clock_on,flag1,flag2;
static uint32_t expected_mask,real_handle=101U;
static uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
 assert(mask==expected_mask);claims++;return claim_allowed?real_handle:0U;
}
static bool furi_hal_resource_lease_release(uint32_t owner,uint32_t mask) {
 assert(owner==real_handle && mask==expected_mask);releases++;return release_allowed;
}
static bool furi_hal_bus_is_enabled(int bus) {assert(bus==2);return clock_on;}
static void furi_hal_bus_enable(int bus) {assert(bus==2&&!clock_on);clock_on=true;writes++;}
static void furi_hal_bus_disable(int bus) {assert(bus==2&&clock_on);clock_on=false;writes++;}
static bool furi_hal_subghz_start_debug(void) {writes++;return true;}
static bool furi_hal_subghz_stop_debug(void) {debug_stop++;writes++;return true;}
static void furi_hal_subghz_rx(void) {writes++;}
static void furi_hal_subghz_idle(void) {radio_idle++;writes++;}
#define furi_hal_gpio_init_ex(...) (++writes)
#define furi_hal_gpio_init(...) (++writes)
#define furi_hal_gpio_write(...) (++writes)
#define furi_hal_interrupt_set_isr(...) (++writes)
#define LL_TIM_Init(t,c) ((void)(c),++writes)
#define LL_TIM_SetClockSource(...) (++writes)
#define LL_TIM_DisableARRPreload(...) (++writes)
#define LL_TIM_SetTriggerInput(...) (++writes)
#define LL_TIM_SetSlaveMode(...) (++writes)
#define LL_TIM_SetTriggerOutput(...) (++writes)
#define LL_TIM_EnableMasterSlaveMode(...) (++writes)
#define LL_TIM_DisableDMAReq_TRIG(...) (++writes)
#define LL_TIM_DisableIT_TRIG(...) (++writes)
#define LL_TIM_IC_SetActiveInput(...) (++writes)
#define LL_TIM_IC_SetPrescaler(...) (++writes)
#define LL_TIM_IC_SetPolarity(...) (++writes)
#define LL_TIM_IC_SetFilter(...) (++writes)
#define LL_TIM_EnableIT_CC1(...) (++writes)
#define LL_TIM_EnableIT_CC2(...) (++writes)
#define LL_TIM_CC_EnableChannel(...) (++writes)
#define LL_TIM_SetCounter(...) (++writes)
#define LL_TIM_EnableCounter(...) (++writes)
#define LL_TIM_IsActiveFlag_CC1(...) (flag1)
#define LL_TIM_IsActiveFlag_CC2(...) (flag2)
#define LL_TIM_ClearFlag_CC1(...) (flag1=false,++writes)
#define LL_TIM_ClearFlag_CC2(...) (flag2=false,++writes)
#define LL_TIM_IC_GetCaptureCH1(...) (13U)
#define LL_TIM_IC_GetCaptureCH2(...) (18U)
#define FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_TIM2 (1U<<2)
#define FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PA7 ((1U<<2)|(1U<<1))
#define FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PB3 ((1U<<2)|(1U<<3))
#define TIM2 2
"""
RUN=r"""
static void cb(bool level,uint32_t duration,void* ctx) {
 assert(ctx==&furi_hal_subghz);
 assert(duration==(level?13U:5U));callbacks++;
}
static void reset(void) {
 claims=releases=writes=callbacks=debug_stop=radio_idle=0;
 claim_allowed=false;release_allowed=true;
 clock_on=flag1=flag2=false;
 furi_hal_subghz.state=SubGhzStateIdle;
 furi_hal_subghz.async_mirror_pin=NULL;
 furi_hal_subghz_capture_callback=NULL;
 furi_hal_subghz_capture_callback_context=NULL;
 e11_subghz_rx_handle=e11_subghz_rx_mask=0U;
 e11_subghz_rx_fault=false;
 expected_mask=FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_TIM2;
}
int main(void) {
 reset();
 assert(!furi_hal_subghz_async_rx_try_start(cb,&furi_hal_subghz));
 furi_hal_subghz_stop_async_rx();
 flag1=flag2=true;furi_hal_subghz_capture_ISR(NULL);
 assert(!writes && !callbacks && claims==1 && !radio_idle);
 furi_hal_subghz_start_async_rx(cb,&furi_hal_subghz);
 furi_hal_subghz_stop_async_rx();
 assert(!writes && claims==2);
 reset();
 assert(!furi_hal_subghz_async_rx_try_start(NULL,&furi_hal_subghz));
 assert(!claims && !writes);
 reset();claim_allowed=true;clock_on=true;
 assert(!furi_hal_subghz_async_rx_try_start(cb,&furi_hal_subghz));
 assert(!writes && releases==1);
 furi_hal_subghz_stop_async_rx();assert(!writes);
 reset();claim_allowed=true;release_allowed=false;clock_on=true;
 assert(!furi_hal_subghz_async_rx_try_start(cb,&furi_hal_subghz));
 assert(e11_subghz_rx_fault && e11_subghz_rx_handle==real_handle);
 clock_on=false;
 assert(!furi_hal_subghz_async_rx_try_start(cb,&furi_hal_subghz));
 assert(claims==1 && !writes);
 reset();claim_allowed=true;
 assert(furi_hal_subghz_async_rx_try_start(cb,&furi_hal_subghz));
 assert(clock_on && e11_subghz_rx_handle==real_handle);
 assert(!furi_hal_subghz_async_rx_try_start(cb,&furi_hal_subghz));
 flag1=flag2=true;int before=writes;
 furi_hal_subghz_capture_ISR(NULL);
 assert(callbacks==2 && !flag1&&!flag2 && writes==before+2);
 furi_hal_subghz_stop_async_rx();
 assert(!clock_on && !e11_subghz_rx_handle && releases==1);
 before=writes;
 furi_hal_subghz_stop_async_rx();
 assert(writes==before && releases==1);
 assert(furi_hal_subghz_async_rx_try_start(cb,&furi_hal_subghz));
 furi_hal_subghz_stop_async_rx();
 reset();claim_allowed=true;
 furi_hal_subghz.async_mirror_pin=&gpio_ext_pa7;
 expected_mask=FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PA7;
 assert(furi_hal_subghz_async_rx_try_start(cb,&furi_hal_subghz));
 furi_hal_subghz_stop_async_rx();
 reset();claim_allowed=true;
 furi_hal_subghz.async_mirror_pin=&gpio_ext_pb3;
 expected_mask=FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PB3;
 assert(furi_hal_subghz_async_rx_try_start(cb,&furi_hal_subghz));
 furi_hal_subghz_stop_async_rx();
 reset();claim_allowed=true;
 furi_hal_subghz.async_mirror_pin=&gpio_cc1101_g0;
 assert(!furi_hal_subghz_async_rx_try_start(cb,&furi_hal_subghz));
 assert(!claims&&!writes);
#ifdef FAIL_FINAL_RELEASE
 reset();claim_allowed=true;release_allowed=false;
 assert(furi_hal_subghz_async_rx_try_start(cb,&furi_hal_subghz));
 furi_hal_subghz_stop_async_rx();
 assert(!clock_on && e11_subghz_rx_fault && e11_subghz_rx_handle);
 before=writes;
 assert(!furi_hal_subghz_async_rx_try_start(cb,&furi_hal_subghz));
 furi_hal_subghz_stop_async_rx();
 assert(writes==before && claims==1);
#else
 reset();claim_allowed=true;
 assert(furi_hal_subghz_async_rx_try_start(cb,&furi_hal_subghz));
 clock_on=false;flag1=flag2=true;before=writes;
 furi_hal_subghz_capture_ISR(NULL);
 furi_hal_subghz_stop_async_rx();
 assert(writes==before && !callbacks && releases==0 &&
        e11_subghz_rx_fault && e11_subghz_rx_handle);
#endif
 puts("E11 actual SubGHz RX C denied-zero-writes/ISR/STOP/mirror/fault PASS");
 return 0;
}
"""
MASK=r"""
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"SubGHz lease FAIL %d\n",__LINE__);exit(1);}}while(0)
int main(void) {
 uint32_t a=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_TIM2);
 REQUIRE(a);
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_RX_TIM2));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_FIELD));
 REQUIRE(furi_hal_resource_lease_release(a,FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_TIM2));
 uint32_t b=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PA7);
 REQUIRE(b);
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7));
 REQUIRE(furi_hal_resource_lease_release(b,FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PA7));
 uint32_t c=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PB3);
 REQUIRE(c);
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_MONITOR_PB3));
 REQUIRE(furi_hal_resource_lease_release(c,FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PB3));
 puts("E11 actual firmware allocator SubGHz TIM2/PA7/PB3 conflict PASS");
 return 0;
}
"""

def main()->None:
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    s=(root/"targets/f7/furi_hal/furi_hal_subghz.c").read_text()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    r=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    pub=(root/"targets/f7/furi_hal/furi_hal_subghz.h").read_text()
    api=(root/"targets/f7/api_symbols.csv").read_text()
    assert "/* E11 native SubGHz RX TIM2 cooperative owner. */" in s
    assert "bool furi_hal_subghz_async_rx_try_start(" in pub
    assert "Function,+,furi_hal_subghz_async_rx_try_start,_Bool," in api
    assert "mask == FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_TIM2" in r
    helpers=s[s.index("/* E11 native SubGHz RX TIM2 cooperative owner. */"):
              s.index("int32_t furi_hal_subghz_get_rolling_counter_mult(void) {")]
    # A subsequent separately-tested TX stage places its globals next to RX
    # globals. The isolated genuine RX-C fixture must not compile unreferenced
    # TX state, while the integrated firmware still compiles both unchanged.
    tx_globals=("static uint32_t e11_subghz_tx_handle;\n"
                "static uint32_t e11_subghz_tx_mask;\n"
                "static bool e11_subghz_tx_fault;\n")
    if "/* E11 native SubGHz TX TIM2/DMA2 lease owner. */" in s:
        assert tx_globals in helpers
        helpers=helpers.replace(tx_globals,"")
    native=s[s.index("volatile uint32_t furi_hal_subghz_capture_delta_duration = 0;"):
             s.index("typedef enum {\n    FuriHalSubGhzAsyncTxMiddlewareStateIdle")]
    assert native.index("furi_hal_resource_lease_try_acquire(") < native.index(
        "furi_hal_subghz_capture_callback = callback;")
    assert native.index("furi_hal_resource_lease_try_acquire(") < native.index(
        "furi_hal_gpio_init_ex(")
    assert "if(!e11_subghz_rx_ready()) return;" in native
    with tempfile.TemporaryDirectory(prefix="e11_subghz_rx_") as dir:
        d=Path(dir);exe=d/"test"
        (d/"rx.c").write_text(STUB+"\n"+helpers+"\n"+native+"\n"+RUN)
        for failed in (False,True):
            flags=["-DFAIL_FINAL_RELEASE=1"] if failed else []
            subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                            "-pedantic","-O0",*flags,str(d/"rx.c"),"-o",str(exe)],
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
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                        "-pedantic","-pthread",str(d/"allocator.c"),"-o",str(exe)],
                        check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 original SubGHz RX TIM2 ISR/START/STOP and allocator C HOST PASS")
    print("TX, unhandled mirror pins, app/device BUSY and physical radio OPEN")

if __name__=="__main__":
    main()
