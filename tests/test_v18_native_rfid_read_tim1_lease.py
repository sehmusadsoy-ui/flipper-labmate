#!/usr/bin/env python3
"""E11 real pinned native RFID read TIM1 C and firmware allocator fault tests.

No radio hardware or device writes. Field/emulation/capture are NOT covered.
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
#define FURI_HAL_RFID_READ_TIMER 1
#define FURI_HAL_RFID_READ_TIMER_BUS 1
#define FURI_HAL_RFID_READ_TIMER_CHANNEL 1
#define LL_TIM_CHANNEL_CH1N 1
#define FURI_HAL_RFID_READ_TIMER_CHANNEL_CONFIG 2
#define LL_TIM_OCMODE_PWM1 1
#define LL_TIM_OCSTATE_ENABLE 1
#define SystemCoreClock 64000000UL
#define FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1 (1U<<0)
typedef struct {uint32_t Autoreload;} LL_TIM_InitTypeDef;
typedef struct {
 uint32_t OCMode,OCNState,CompareValue;
} LL_TIM_OC_InitTypeDef;
static int writes,claims,releases;
static bool allow_claim,allow_release=true,tim1_clock;
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
 assert(mask==FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1);claims++;
 return allow_claim?41U:0U;
}
bool furi_hal_resource_lease_release(uint32_t h,uint32_t mask) {
 assert(h==41U && mask==FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1);
 releases++;return allow_release;
}
bool furi_hal_bus_is_enabled(int b){assert(b==1);return tim1_clock;}
void furi_hal_bus_enable(int b) {
 assert(b==1&&!tim1_clock);tim1_clock=true;writes++;
}
void furi_hal_bus_disable(int b) {
 assert(b==1&&tim1_clock);tim1_clock=false;writes++;
}
void furi_hal_rfid_pins_read(void){writes++;}
void furi_hal_rfid_tim_read_continue(void);
#define LL_TIM_Init(timer,cfg) ((void)(timer),(void)(cfg),++writes)
#define LL_TIM_DisableARRPreload(timer) ((void)(timer),++writes)
#define LL_TIM_OC_Init(timer,channel,cfg) ((void)(timer),(void)(channel),(void)(cfg),++writes)
#define LL_TIM_EnableCounter(timer) ((void)(timer),++writes)
#define LL_TIM_EnableAllOutputs(timer) ((void)(timer),++writes)
#define LL_TIM_DisableAllOutputs(timer) ((void)(timer),++writes)
#define LL_TIM_SetAutoReload(timer,period) ((void)(timer),(void)(period),++writes)
#define LL_TIM_OC_SetCompareCH1(timer,pulse) ((void)(timer),(void)(pulse),++writes)
"""
RUN=r"""
static void reset_case(void) {
 writes=claims=releases=0;
 tim1_clock=false;
 allow_claim=false;allow_release=true;
 e11_rfid_read_handle=0U;e11_rfid_read_fault=false;
}
int main(void) {
 reset_case();
 assert(!furi_hal_rfid_tim_read_try_start(125000.f,0.5f));
 furi_hal_rfid_tim_read_stop();
 furi_hal_rfid_tim_read_continue();
 furi_hal_rfid_tim_read_pause();
 furi_hal_rfid_set_read_period(100);
 furi_hal_rfid_set_read_pulse(50);
 assert(!writes && claims==1 && !releases);
 /* Old void API denial does not alter GPIO, TIM1 or later STOP. */
 furi_hal_rfid_tim_read_start(125000.f,0.5f);
 furi_hal_rfid_tim_read_stop();
 assert(!writes && claims==2);
 /* Legacy uncoordinated active TIM1 refused after claim. */
 reset_case();allow_claim=true;tim1_clock=true;
 assert(!furi_hal_rfid_tim_read_try_start(125000.f,0.5f));
 assert(!writes && releases==1 && !e11_rfid_read_handle);
 furi_hal_rfid_tim_read_stop();assert(!writes);
 /* Failed preflight release becomes sticky and blocks retries. */
 reset_case();allow_claim=true;tim1_clock=true;allow_release=false;
 assert(!furi_hal_rfid_tim_read_try_start(125000.f,0.5f));
 assert(e11_rfid_read_fault && e11_rfid_read_handle==41U);
 tim1_clock=false;
 int c=claims;
 furi_hal_rfid_tim_read_start(125000.f,0.5f);
 furi_hal_rfid_tim_read_stop();
 assert(claims==c && writes==0);
 /* Acquired carrier, safe pause/continue/retune, owned STOP. */
 reset_case();allow_claim=true;
 assert(furi_hal_rfid_tim_read_try_start(125000.f,0.5f));
 assert(tim1_clock && e11_rfid_read_handle==41U && writes>0);
 c=claims;
 assert(!furi_hal_rfid_tim_read_try_start(125000.f,0.5f));
 assert(claims==c);
 int before=writes;
 furi_hal_rfid_tim_read_pause();
 furi_hal_rfid_tim_read_continue();
 furi_hal_rfid_set_read_period(20);
 furi_hal_rfid_set_read_pulse(8);
 assert(writes==before+4);
 furi_hal_rfid_tim_read_stop();
 assert(!tim1_clock && !e11_rfid_read_handle && releases==1);
 before=writes;
 furi_hal_rfid_tim_read_stop();
 furi_hal_rfid_tim_read_pause();
 furi_hal_rfid_tim_read_continue();
 furi_hal_rfid_set_read_period(20);
 furi_hal_rfid_set_read_pulse(8);
 assert(writes==before && releases==1);
#ifdef TEST_RELEASE_FAILURE
 reset_case();allow_claim=true;allow_release=false;
 assert(furi_hal_rfid_tim_read_try_start(125000.f,0.5f));
 furi_hal_rfid_tim_read_stop();
 assert(!tim1_clock && e11_rfid_read_fault && e11_rfid_read_handle==41U);
 before=writes;c=claims;
 assert(!furi_hal_rfid_tim_read_try_start(125000.f,0.5f));
 furi_hal_rfid_tim_read_stop();
 assert(writes==before && claims==c);
#else
 reset_case();allow_claim=true;
 assert(furi_hal_rfid_tim_read_try_start(125000.f,0.5f));
 tim1_clock=false;
 before=writes;
 furi_hal_rfid_tim_read_pause();
 furi_hal_rfid_tim_read_continue();
 furi_hal_rfid_set_read_period(20);
 furi_hal_rfid_set_read_pulse(8);
 furi_hal_rfid_tim_read_stop();
 assert(writes==before && e11_rfid_read_fault && e11_rfid_read_handle==41U);
 assert(releases==0);
#endif
 puts("E11 RFID REAL READ TIM1 C PASS: denied zero writes, STOP, sticky failed release, clock loss");
 return 0;
}
"""
MASK_TEST=r"""
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"RFID read mask failure at %d\n",__LINE__);exit(1);}}while(0)
int main(void) {
 uint32_t r=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1);
 REQUIRE(r);
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_TIMERS));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7));
 REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_RX_TIM2));
 REQUIRE(!furi_hal_resource_lease_release(r,FURI_HAL_LEASE_NATIVE_NFC_TIMERS));
 REQUIRE(furi_hal_resource_lease_release(r,FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1));
 REQUIRE(!furi_hal_resource_lease_release(r,FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1));
 puts("E11 RFID actual firmware C: READ TIM1 overlaps PWM/NFC/iButton/IR TX");
 return 0;
}
"""

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("root",type=Path)
    root=ap.parse_args().root.resolve()
    s=(root/"targets/f7/furi_hal/furi_hal_rfid.c").read_text()
    h=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    resources=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    hdr=(root/"targets/f7/furi_hal/furi_hal_rfid.h").read_text()
    api=(root/"targets/f7/api_symbols.csv").read_text()
    assert "/* E11 native RFID read TIM1 owner. */" in s
    assert "mask == FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1" in resources
    assert "bool furi_hal_rfid_tim_read_try_start(" in hdr
    assert "Function,+,furi_hal_rfid_tim_read_try_start,_Bool," in api
    source=s[s.index("/* E11 native RFID read TIM1 owner. */"):
             s.index("static void furi_hal_rfid_tim_emulate(void) {")]
    tuning=s[s.index("void furi_hal_rfid_set_read_period(uint32_t period) {"):
             s.index("void furi_hal_rfid_comp_start(void) {")]
    source += "\n" + tuning
    assert source.index("furi_hal_resource_lease_try_acquire(")<source.index(
        "furi_hal_rfid_pins_read();")
    assert source.count("if(!e11_rfid_read_ready()) return;")>=5
    with tempfile.TemporaryDirectory(prefix="labmate_e11_rfid_read_") as td:
        tmp=Path(td);exe=tmp/"test"
        (tmp/"host.c").write_text(STUB+"\n"+source+"\n"+RUN)
        for fail in (False,True):
            flags=["-DTEST_RELEASE_FAILURE=1"] if fail else []
            subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                            "-O0",*flags,str(tmp/"host.c"),"-o",str(exe)],check=True)
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
        allocator=resources[resources.index("/* Firmware-owned E11 lease primitive"):
                             resources.index("const GpioPinRecord* furi_hal_resources_pin_by_number")]
        (tmp/"lease.c").write_text(pre+masks+allocator+MASK_TEST)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(tmp/"lease.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 NATIVE RFID READ TIM1 ACTUAL C HOST 2/2 + FIRMWARE ALLOCATOR PASS; FIELD/EMULATE/CAPTURE OPEN")

if __name__=="__main__":
    main()
