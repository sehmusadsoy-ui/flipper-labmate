#!/usr/bin/env python3
"""Real pinned native infrared RX C host fault tests plus firmware allocator.

Production RX source (not a model) is extracted and compiled with
instrumented minimal STM32 HAL; native infrared TX is NOT migrated.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
typedef struct { uint32_t CCMR1; } TIM_TypeDef;
static TIM_TypeDef tim2;
#define INFRARED_RX_TIMER (&tim2)
#define INFRARED_RX_TIMER_BUS 2
#define INFRARED_RX_IRQ 202
#define FuriHalBusTIM2 2
#define FURI_HAL_LEASE_NATIVE_IR_RX_TIM2 (1U << 2)
#define GpioModeAltFunctionPushPull 1
#define GpioPullNo 0
#define GpioSpeedLow 1
#define INFRARED_RX_GPIO_ALT 1
#define LL_TIM_COUNTERMODE_UP 1
#define LL_TIM_CLOCKDIVISION_DIV1 1
#define LL_TIM_CLOCKSOURCE_INTERNAL 1
#define LL_TIM_TS_TI1FP1 1
#define LL_TIM_SLAVEMODE_RESET 1
#define LL_TIM_CHANNEL_CH2 2
#define LL_TIM_CHANNEL_CH1 1
#define LL_TIM_IC_FILTER_FDIV1 1
#define LL_TIM_IC_POLARITY_FALLING 0
#define LL_TIM_IC_POLARITY_RISING 1
#define LL_TIM_TRGO_RESET 1
#define LL_TIM_ACTIVEINPUT_DIRECTTI 1
#define LL_TIM_ACTIVEINPUT_INDIRECTTI 2
#define LL_TIM_ICPSC_DIV1 1
#define LL_TIM_OCMODE_ACTIVE 1
#define TIM_CCMR1_CC1S 1
#define UNUSED(x) (void)(x)
#define furi_check(x) assert(x)
#define FURI_CRITICAL_ENTER() ((void)0)
#define FURI_CRITICAL_EXIT() ((void)0)
#define READ_BIT(x,mask) ((x)&(mask))
typedef struct { uint32_t Prescaler,CounterMode,Autoreload,ClockDivision; } LL_TIM_InitTypeDef;
typedef struct {uint32_t x;uint32_t pin;} GpioPin;
static const GpioPin gpio_infrared_rx={0,1};
typedef void (*FuriHalInfraredRxCaptureCallback)(void*,bool,uint32_t);
typedef void (*FuriHalInfraredRxTimeoutCallback)(void*);
typedef struct {
    FuriHalInfraredRxCaptureCallback capture_callback;
    void* capture_context;
    FuriHalInfraredRxTimeoutCallback timeout_callback;
    void* timeout_context;
} InfraredTimRx;
typedef enum {
    InfraredStateIdle,InfraredStateAsyncRx,InfraredStateAsyncTx,
    InfraredStateAsyncTxStopReq,InfraredStateAsyncTxStopInProgress,
    InfraredStateAsyncTxStopped,InfraredStateMAX
} InfraredState;
static volatile InfraredState furi_hal_infrared_state=InfraredStateIdle;
static InfraredTimRx infrared_tim_rx;
static int writes,acquires,releases;
static bool allow_acquire,allow_release=true,clock_enabled;
static void (*native_isr)(void*);
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
    assert(mask==FURI_HAL_LEASE_NATIVE_IR_RX_TIM2);
    acquires++;
    return allow_acquire?77U:0U;
}
bool furi_hal_resource_lease_release(uint32_t h,uint32_t mask) {
    assert(h==77U && mask==FURI_HAL_LEASE_NATIVE_IR_RX_TIM2);
    releases++;
    return allow_release;
}
bool furi_hal_bus_is_enabled(int b) {assert(b==2);return clock_enabled;}
void furi_hal_bus_enable(int b) {assert(b==2);assert(!clock_enabled);clock_enabled=true;writes++;}
void furi_hal_bus_disable(int b) {assert(b==2);assert(clock_enabled);clock_enabled=false;writes++;}
void furi_hal_gpio_init_ex(const GpioPin* p,int a,int b,int c,int d) {
    assert(p==&gpio_infrared_rx);(void)a;(void)b;(void)c;(void)d;writes++;
}
void furi_hal_interrupt_set_isr(int id,void(*cb)(void*),void* arg) {
    assert(id==INFRARED_RX_IRQ && arg==NULL);
    native_isr=cb;writes++;
}
void furi_crash(void) {abort();}
#define LL_TIM_Init(t,config) ((void)(t),(void)(config),++writes)
#define LL_TIM_SetClockSource(...) (++writes)
#define LL_TIM_DisableARRPreload(...) (++writes)
#define LL_TIM_SetTriggerInput(...) (++writes)
#define LL_TIM_SetSlaveMode(...) (++writes)
#define LL_TIM_CC_DisableChannel(...) (++writes)
#define LL_TIM_IC_SetFilter(...) (++writes)
#define LL_TIM_IC_SetPolarity(...) (++writes)
#define LL_TIM_DisableIT_TRIG(...) (++writes)
#define LL_TIM_DisableDMAReq_TRIG(...) (++writes)
#define LL_TIM_SetTriggerOutput(...) (++writes)
#define LL_TIM_EnableMasterSlaveMode(...) (++writes)
#define LL_TIM_IC_SetActiveInput(...) (++writes)
#define LL_TIM_IC_SetPrescaler(...) (++writes)
#define LL_TIM_EnableIT_CC1(...) (++writes)
#define LL_TIM_EnableIT_CC2(...) (++writes)
#define LL_TIM_CC_EnableChannel(...) (++writes)
#define LL_TIM_SetCounter(...) (++writes)
#define LL_TIM_EnableCounter(...) (++writes)
#define LL_TIM_OC_SetCompareCH3(...) (++writes)
#define LL_TIM_OC_SetMode(...) (++writes)
#define LL_TIM_EnableIT_CC3(...) (++writes)
#define LL_TIM_IsActiveFlag_CC1(...) 0
#define LL_TIM_IsActiveFlag_CC2(...) 0
#define LL_TIM_IsActiveFlag_CC3(...) 0
#define LL_TIM_ClearFlag_CC1(...) (++writes)
#define LL_TIM_ClearFlag_CC2(...) (++writes)
#define LL_TIM_ClearFlag_CC3(...) (++writes)
#define LL_GPIO_IsInputPinSet(...) 0
#define LL_TIM_IC_GetCaptureCH1(...) 0U
#define LL_TIM_IC_GetCaptureCH2(...) 0U
"""
RUN=r"""
int main(void) {
    /* Denied claim: NO native GPIO alt, TIM2 bus or ISR writes. */
    furi_hal_infrared_async_rx_start();
    furi_hal_infrared_async_rx_set_timeout(120U);
    furi_hal_infrared_async_rx_stop();
    assert(acquires==1 && writes==0 && releases==0 && !native_isr);
    assert(furi_hal_infrared_state==InfraredStateIdle);
    allow_acquire=true;
    clock_enabled=true;
    /* Legacy native user enabled TIM2 without lease: no native mutation. */
    furi_hal_infrared_async_rx_start();
    assert(acquires==2 && releases==1 && writes==0 && !native_isr);
    furi_hal_infrared_async_rx_stop();
    assert(writes==0);
#ifdef TEST_PREFLIGHT_RELEASE_FAILURE
    allow_release=false;
    furi_hal_infrared_async_rx_start();
    assert(acquires==3 && releases==2 && infrared_e11_rx_fault);
    assert(infrared_e11_rx_handle==77U);
    clock_enabled=false;
    int before=acquires;
    furi_hal_infrared_async_rx_start();
    furi_hal_infrared_async_rx_stop();
    furi_hal_infrared_async_rx_set_timeout(120U);
    assert(acquires==before && writes==0);
    puts("E11 INFRARED RX REAL C PREFLIGHT FAILED RELEASE PASS");
    return 0;
#endif
    clock_enabled=false;
    furi_hal_infrared_async_rx_start();
    assert(furi_hal_infrared_state==InfraredStateAsyncRx);
    assert(infrared_e11_rx_handle==77U && clock_enabled && native_isr);
    int w=writes;
    furi_hal_infrared_async_rx_set_timeout(300U);
    assert(writes==w+4);
    native_isr(NULL);
    furi_hal_infrared_async_rx_stop();
    assert(furi_hal_infrared_state==InfraredStateIdle);
    assert(infrared_e11_rx_handle==0 && !clock_enabled && !native_isr);
    assert(releases==2);
    w=writes;
    furi_hal_infrared_async_rx_stop();
    furi_hal_infrared_async_rx_set_timeout(222U);
    assert(writes==w && releases==2);
#ifdef TEST_STOP_RELEASE_FAILURE
    furi_hal_infrared_async_rx_start();
    assert(infrared_e11_rx_handle==77U);
    allow_release=false;
    furi_hal_infrared_async_rx_stop();
    assert(infrared_e11_rx_fault && infrared_e11_rx_handle==77U && releases==3);
    w=writes;
    int c=acquires;
    furi_hal_infrared_async_rx_start();
    furi_hal_infrared_async_rx_stop();
    furi_hal_infrared_async_rx_set_timeout(100U);
    assert(writes==w && acquires==c);
#else
    /* Clock stolen/killed by noncooperating service: do not disable bus,
     * reset native ISR, or release our original handle.
     */
    furi_hal_infrared_async_rx_start();
    assert(infrared_e11_rx_handle==77U && clock_enabled);
    clock_enabled=false;
    w=writes;
    native_isr(NULL);
    furi_hal_infrared_async_rx_set_timeout(100U);
    furi_hal_infrared_async_rx_stop();
    assert(infrared_e11_rx_fault && infrared_e11_rx_handle==77U);
    assert(writes==w && releases==2);
    assert(native_isr);
#endif
    puts("E11 INFRARED RX NATIVE C HOST PASS: TIM2 ownership, ISR/timeout/STOP, sticky errors");
    return 0;
}
"""

LEASE=r"""
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"IR RX resource FAIL at line %d\n",__LINE__);exit(1);}}while(0)
int main(void) {
    uint32_t h=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_RX_TIM2);
    REQUIRE(h);
    REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3));
    REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PULSE_PC1));
    REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_DIGITAL_NONCONNECTOR));
    REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1));
    REQUIRE(!furi_hal_resource_lease_release(h,FURI_HAL_LEASE_COUNTER_PB3));
    REQUIRE(furi_hal_resource_lease_release(h,FURI_HAL_LEASE_NATIVE_IR_RX_TIM2));
    REQUIRE(!furi_hal_resource_lease_release(h,FURI_HAL_LEASE_NATIVE_IR_RX_TIM2));
    REQUIRE(furi_hal_resource_lease_try_acquire(
        FURI_HAL_LEASE_NATIVE_IR_RX_TIM2|FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1)==0U);
    puts("E11 INFRARED RX REAL firmware allocator TIM2 mask collision PASS");
    return 0;
}
"""

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("firmware_root",type=Path)
    args=parser.parse_args()
    root=args.firmware_root.resolve()
    src=(root/"targets/f7/furi_hal/furi_hal_infrared.c").read_text()
    head=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    resource=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    assert "/* LabMate E11 native infrared TIM2 RX owner. */" in src
    assert "mask == FURI_HAL_LEASE_NATIVE_IR_RX_TIM2" in resource
    assert "FURI_HAL_LEASE_NATIVE_IR_RX_TIM2" in head
    rx=src[src.index("static void furi_hal_infrared_tim_rx_isr("):
           src.index("void furi_hal_infrared_async_rx_set_capture_isr_callback(")]
    e11=src[src.index("/* LabMate E11 native infrared TIM2 RX owner. */"):
            src.index("static const GpioPin* infrared_tx_pins")]
    assert rx.index("furi_hal_resource_lease_try_acquire(") < rx.index(
        "furi_hal_gpio_init_ex(")
    assert "if(!infrared_e11_rx_ready()) return;" in rx
    assert "infrared_e11_rx_fault=true;" in rx
    assert "void furi_hal_infrared_async_tx_start(" in src
    assert "furi_hal_bus_enable(INFRARED_DMA_TIMER_BUS);" in src
    with tempfile.TemporaryDirectory(prefix="labmate_e11_ir_rx_") as td:
        tmp=Path(td)
        exe=tmp/"run"
        native=STUB+"\n"+e11+"\n"+rx+"\n"+RUN
        (tmp/"rx.c").write_text(native)
        for fault in (None,"TEST_STOP_RELEASE_FAILURE","TEST_PREFLIGHT_RELEASE_FAILURE"):
            args=["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic","-O0"]
            if fault: args.append("-D"+fault)
            subprocess.run(args+[str(tmp/"rx.c"),"-o",str(exe)],check=True)
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
        masks=head[head.index("enum {\n    FuriHalLeaseTim1"):
                   head.index("/* Returns unique nonzero")]
        rs=resource[resource.index("/* Firmware-owned E11 lease primitive"):
                    resource.index("const GpioPinRecord* furi_hal_resources_pin_by_number")]
        (tmp/"lease.c").write_text(pre+masks+rs+LEASE)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(tmp/"lease.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 NATIVE INFRARED RX ACTUAL C 3/3 + REAL allocator PASS. TX NOT MIGRATED.")

if __name__=="__main__":
    main()
