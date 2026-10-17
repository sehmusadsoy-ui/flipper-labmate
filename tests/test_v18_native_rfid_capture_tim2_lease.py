#!/usr/bin/env python3
"""Compile actual patched native RFID capture TIM2 C + genuine firmware lease allocator.

This is host-only fault injection, never a physical RFID/device PASS.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB = r"""
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define UNUSED(x) ((void)(x))
#define furi_check(x) assert(x)
#define RFID_CAPTURE_TIM 2
#define RFID_CAPTURE_TIM_BUS 2
#define FURI_HAL_RFID_EMULATE_TIMER_IRQ 7
#define FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2 (1U<<2)
#define LL_TIM_COUNTERMODE_UP 0
#define LL_TIM_CLOCKDIVISION_DIV1 0
#define LL_TIM_CLOCKSOURCE_INTERNAL 0
#define LL_TIM_TS_TI2FP2 0
#define LL_TIM_SLAVEMODE_DISABLED 0
#define LL_TIM_TRGO_RESET 0
#define LL_TIM_TIM2_TI4_RMP_COMP1 0
#define LL_TIM_ACTIVEINPUT_INDIRECTTI 0
#define LL_TIM_ICPSC_DIV1 0
#define LL_TIM_IC_POLARITY_FALLING 0
#define LL_TIM_IC_FILTER_FDIV1 0
#define LL_TIM_ACTIVEINPUT_DIRECTTI 0
#define LL_TIM_IC_POLARITY_RISING 0
#define RFID_CAPTURE_IND_CH 3
#define RFID_CAPTURE_DIR_CH 4
typedef void (*FuriHalRfidReadCaptureCallback)(bool,uint32_t,void*);
typedef struct {
 FuriHalRfidReadCaptureCallback read_capture_callback;
 void* context;
} RfidState;
static RfidState sample;
static RfidState* furi_hal_rfid=&sample;
typedef struct {
 uint32_t Prescaler,CounterMode,Autoreload,ClockDivision;
} LL_TIM_InitTypeDef;
static int writes, claims, releases, callbacks;
static bool allow_claim, allow_release=true, tim2_clock, flag3, flag4;
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
 assert(mask==FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2);
 claims++;
 return allow_claim?51U:0U;
}
bool furi_hal_resource_lease_release(uint32_t h,uint32_t mask) {
 assert(h==51U && mask==FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2);
 releases++;
 return allow_release;
}
bool furi_hal_bus_is_enabled(int bus) {assert(bus==2);return tim2_clock;}
void furi_hal_bus_enable(int bus) {
 assert(bus==2&&!tim2_clock);tim2_clock=true;writes++;
}
void furi_hal_bus_disable(int bus) {
 assert(bus==2&&tim2_clock);tim2_clock=false;writes++;
}
static void furi_hal_interrupt_set_isr(int irq,void(*fn)(void*),void* ctx) {
 assert(irq==7);(void)fn;(void)ctx;writes++;
}
static void furi_hal_rfid_comp_start(void) {writes++;}
static void furi_hal_rfid_comp_stop(void) {writes++;}
#define LL_TIM_Init(t,c) ((void)(t),(void)(c),++writes)
#define LL_TIM_SetClockSource(...) (++writes)
#define LL_TIM_DisableARRPreload(...) (++writes)
#define LL_TIM_SetTriggerInput(...) (++writes)
#define LL_TIM_SetSlaveMode(...) (++writes)
#define LL_TIM_SetTriggerOutput(...) (++writes)
#define LL_TIM_EnableMasterSlaveMode(...) (++writes)
#define LL_TIM_DisableDMAReq_TRIG(...) (++writes)
#define LL_TIM_DisableIT_TRIG(...) (++writes)
#define LL_TIM_SetRemap(...) (++writes)
#define LL_TIM_IC_SetActiveInput(...) (++writes)
#define LL_TIM_IC_SetPrescaler(...) (++writes)
#define LL_TIM_IC_SetPolarity(...) (++writes)
#define LL_TIM_IC_SetFilter(...) (++writes)
#define LL_TIM_EnableIT_CC3(...) (++writes)
#define LL_TIM_EnableIT_CC4(...) (++writes)
#define LL_TIM_CC_EnableChannel(...) (++writes)
#define LL_TIM_SetCounter(...) (++writes)
#define LL_TIM_EnableCounter(...) (++writes)
#define LL_TIM_IsActiveFlag_CC3(...) (flag3)
#define LL_TIM_IsActiveFlag_CC4(...) (flag4)
#define LL_TIM_ClearFlag_CC3(...) (flag3=false,++writes)
#define LL_TIM_ClearFlag_CC4(...) (flag4=false,++writes)
#define LL_TIM_IC_GetCaptureCH3(...) 14U
#define LL_TIM_IC_GetCaptureCH4(...) 20U
"""
RUN = r"""
static void capture_cb(bool level,uint32_t value,void* ctx) {
 assert(ctx==(void*)&sample);
 assert(value==(level?14U:20U));
 callbacks++;
}
static void reset_case(void) {
 writes=claims=releases=callbacks=0;
 allow_claim=false;allow_release=true;
 tim2_clock=false;flag3=flag4=false;
 sample.read_capture_callback=NULL;sample.context=NULL;
 e11_rfid_capture_handle=0U;e11_rfid_capture_fault=false;
}
int main(void) {
 reset_case();
 assert(!furi_hal_rfid_tim_read_capture_try_start(capture_cb,&sample));
 furi_hal_rfid_tim_read_capture_stop();
 flag3=flag4=true;
 furi_hal_capture_dma_isr(NULL);
 assert(!writes && claims==1 && !releases && !callbacks);
 assert(sample.read_capture_callback==NULL);
 furi_hal_rfid_tim_read_capture_start(capture_cb,&sample);
 furi_hal_rfid_tim_read_capture_stop();
 assert(!writes && claims==2);
 reset_case();
 assert(!furi_hal_rfid_tim_read_capture_try_start(NULL,&sample));
 assert(!claims && !writes);
 /* Legacy pre-enabled TIM2: acquire/release without peripheral access. */
 reset_case();allow_claim=true;tim2_clock=true;
 assert(!furi_hal_rfid_tim_read_capture_try_start(capture_cb,&sample));
 assert(!writes && releases==1 && !e11_rfid_capture_handle);
 furi_hal_rfid_tim_read_capture_stop();assert(!writes);
 /* Failed preflight release retains opaque claim permanently. */
 reset_case();allow_claim=true;tim2_clock=true;allow_release=false;
 assert(!furi_hal_rfid_tim_read_capture_try_start(capture_cb,&sample));
 assert(e11_rfid_capture_fault && e11_rfid_capture_handle==51U && !writes);
 tim2_clock=false;
 assert(!furi_hal_rfid_tim_read_capture_try_start(capture_cb,&sample));
 assert(claims==1 && !writes);
 /* Normal START, captured IRQ channels, exact owner STOP/re-entry. */
 reset_case();allow_claim=true;
 assert(furi_hal_rfid_tim_read_capture_try_start(capture_cb,&sample));
 assert(writes>0 && tim2_clock && e11_rfid_capture_handle==51U);
 assert(!furi_hal_rfid_tim_read_capture_try_start(capture_cb,&sample));
 int prior=writes;
 flag3=flag4=true;
 furi_hal_capture_dma_isr(NULL);
 assert(callbacks==2 && writes==prior+3 && !flag3 && !flag4);
 furi_hal_rfid_tim_read_capture_stop();
 assert(!tim2_clock && !e11_rfid_capture_handle && releases==1);
 prior=writes;
 furi_hal_rfid_tim_read_capture_stop();
 furi_hal_capture_dma_isr(NULL);
 assert(writes==prior && callbacks==2);
 assert(furi_hal_rfid_tim_read_capture_try_start(capture_cb,&sample));
 furi_hal_rfid_tim_read_capture_stop();
#ifdef TEST_RELEASE_FAILURE
 reset_case();allow_claim=true;allow_release=false;
 assert(furi_hal_rfid_tim_read_capture_try_start(capture_cb,&sample));
 furi_hal_rfid_tim_read_capture_stop();
 assert(!tim2_clock && e11_rfid_capture_fault && e11_rfid_capture_handle==51U);
 prior=writes;
 assert(!furi_hal_rfid_tim_read_capture_try_start(capture_cb,&sample));
 furi_hal_rfid_tim_read_capture_stop();
 assert(writes==prior && claims==1);
#else
 reset_case();allow_claim=true;
 assert(furi_hal_rfid_tim_read_capture_try_start(capture_cb,&sample));
 tim2_clock=false;flag3=flag4=true;
 prior=writes;
 furi_hal_capture_dma_isr(NULL);
 furi_hal_rfid_tim_read_capture_stop();
 assert(writes==prior && callbacks==0 && releases==0);
 assert(e11_rfid_capture_fault && e11_rfid_capture_handle==51U);
 assert(!furi_hal_rfid_tim_read_capture_try_start(capture_cb,&sample));
#endif
 puts("E11 RFID capture real C: denied zero writes, IRQ/STOP, sticky faults PASS");
 return 0;
}
"""
MASK = r"""
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"RFID capture mask failure at %d\n",__LINE__);exit(1);}}while(0)
int main(void) {
 uint32_t c=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2);
 REQUIRE(c);
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_RX_TIM2));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_COUNTER_PB3));
 REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1));
 REQUIRE(!furi_hal_resource_lease_release(c,FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1));
 REQUIRE(furi_hal_resource_lease_release(c,FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2));
 REQUIRE(!furi_hal_resource_lease_release(c,FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2));
 puts("E11 RFID capture real firmware allocator TIM2 overlap PASS");
 return 0;
}
"""

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    s=(root/"targets/f7/furi_hal/furi_hal_rfid.c").read_text()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    r=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    header=(root/"targets/f7/furi_hal/furi_hal_rfid.h").read_text()
    api=(root/"targets/f7/api_symbols.csv").read_text()
    assert "/* E11 native RFID capture TIM2 owner. */" in s
    assert "bool furi_hal_rfid_tim_read_capture_try_start(" in header
    assert "Function,+,furi_hal_rfid_tim_read_capture_try_start,_Bool," in api
    assert "mask == FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2" in r
    capture_end=("/* E11 native RFID emulate TIM2/DMA2 composite owner. */"
                 if "/* E11 native RFID emulate TIM2/DMA2 composite owner. */" in s
                 else "static void furi_hal_rfid_dma_isr(void* context)")
    source=s[s.index("/* E11 native RFID capture TIM2 owner. */"):
             s.index(capture_end)]
    assert source.index("furi_hal_resource_lease_try_acquire(") < source.index(
        "furi_hal_rfid->read_capture_callback = callback;")
    assert source.index("furi_hal_resource_lease_try_acquire(") < source.index(
        "furi_hal_bus_enable(RFID_CAPTURE_TIM_BUS);")
    with tempfile.TemporaryDirectory(prefix="e11_native_rfid_capture_") as t:
        tmp=Path(t);exe=tmp/"test"
        (tmp/"host.c").write_text(STUB+"\n"+source+"\n"+RUN)
        for failure in (False,True):
            flags=["-DTEST_RELEASE_FAILURE=1"] if failure else []
            subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                            "-pedantic","-O0",*flags,str(tmp/"host.c"),"-o",str(exe)],check=True)
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
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                        "-pedantic","-pthread",str(tmp/"lease.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("RFID CAPTURE TIM2 ACTUAL NATIVE C HOST + GENUINE FIRMWARE ALLOCATOR PASS")
    print("Sub-GHz, RFID DMA/field and upstream BUSY still OPEN; NO DEVICE/FLASH")

if __name__=="__main__":
    main()
