#!/usr/bin/env python3
"""Native infrared TX E11 pinned real-C failure-ownership tests (NO DEVICE).

Execute actual TX claim, allocation and START, cleanup, WAIT/STOP code
and exact firmware lease allocator under strict host stubs. Worker call
ordering verified against actual patched Momentum worker source.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <math.h>
#define furi_check(c) assert(c)
#define FURI_CRITICAL_ENTER() ((void)0)
#define FURI_CRITICAL_EXIT() ((void)0)
#define FuriWaitForever 0xFFFFFFFFU
#define FuriStatusOk 0
#define FuriStatusErrorTimeout (-2)
#define FuriStatusErrorResource (-3)
typedef int FuriStatus;
#define FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL ((1U<<0)|(1U<<25)|(1U<<26))
#define FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7 (FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL|(1U<<1))
#define INFRARED_MIN_FREQUENCY 10000U
#define INFRARED_MAX_FREQUENCY 1000000U
#define INFRARED_TIM_TX_DMA_BUFFER_SIZE 200
#define INFRARED_POLARITY_SHIFT 1
#define INFRARED_DMA_TIMER_BUS 1
#define INFRARED_DMA_TIMER 1
#define INFRARED_DMA_CH1_DEF 2,1
#define INFRARED_DMA_CH2_DEF 2,2
#define INFRARED_DMA_CH1_IRQ 31
#define INFRARED_DMA_CH2_IRQ 32
#define GpioModeAnalog 0
#define GpioPullDown 0
#define GpioSpeedLow 0
#define GpioModeAltFunctionPushPull 1
#define GpioPullNo 0
#define GpioSpeedHigh 1
#define GpioAltFn1TIM1 1
typedef struct {int port;int pin;} GpioPin;
static GpioPin gpio_infrared_tx={.port=1,.pin=1};
static GpioPin gpio_ext_pa7={.port=1,.pin=7};
typedef enum {
 FuriHalInfraredTxPinInternal,FuriHalInfraredTxPinExtPA7,FuriHalInfraredTxPinMax
} FuriHalInfraredTxPin;
typedef enum {
 InfraredStateIdle,InfraredStateAsyncRx,InfraredStateAsyncTx,
 InfraredStateAsyncTxStopReq,InfraredStateAsyncTxStopInProgress,
 InfraredStateAsyncTxStopped,InfraredStateMAX
} InfraredState;
typedef enum {
 FuriHalInfraredTxGetDataStateOk, FuriHalInfraredTxGetDataStateDone,
 FuriHalInfraredTxGetDataStateLastDone
} FuriHalInfraredTxGetDataState;
typedef FuriHalInfraredTxGetDataState (*FuriHalInfraredTxGetDataISRCallback)(
    void*,uint32_t*,bool*);
typedef void (*FuriHalInfraredTxSignalSentISRCallback)(void*);
typedef struct {
 uint8_t* polarity; uint16_t* data; size_t size; bool packet_end,last_packet_end;
} InfraredTxBuf;
typedef struct FuriSemaphore {int x;} FuriSemaphore;
typedef struct {
 float cycle_duration,cycle_remainder;
 FuriHalInfraredTxGetDataISRCallback data_callback;
 FuriHalInfraredTxSignalSentISRCallback signal_sent_callback;
 void* data_context;void* signal_sent_context;
 InfraredTxBuf buffer[2];
 FuriSemaphore* stop_semaphore;
 uint32_t tx_timing_rest_duration;
 bool tx_timing_rest_level;
 FuriHalInfraredTxGetDataState tx_timing_rest_status;
} InfraredTimTx;
static volatile InfraredState furi_hal_infrared_state=InfraredStateIdle;
static InfraredTimTx infrared_tim_tx;
static FuriHalInfraredTxPin infrared_tx_output=FuriHalInfraredTxPinInternal;
static const GpioPin* infrared_tx_pins[FuriHalInfraredTxPinMax]={
 &gpio_infrared_tx,&gpio_ext_pa7};
static int writes,claims,releases,allocs,allocated_ok,freed,waits;
static bool claim_allowed,release_ok=true,tim1_clock,dma1,dma2,lose_clock;
static int fail_malloc_on=0;
static uint32_t last_claim_mask;
static int stop_signaled;
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
    assert(mask==FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL ||
           mask==FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7);
    claims++;last_claim_mask=mask;return claim_allowed?99U:0U;
}
bool furi_hal_resource_lease_release(uint32_t handle,uint32_t mask) {
    assert(handle==99U && mask==last_claim_mask);
    releases++;return release_ok;
}
bool furi_hal_bus_is_enabled(int bus) {assert(bus==1);return tim1_clock;}
void furi_hal_bus_enable(int bus) {assert(bus==1&&!tim1_clock);tim1_clock=true;writes++;}
void furi_hal_bus_disable(int bus) {assert(bus==1&&tim1_clock);tim1_clock=false;writes++;}
bool is_dma_enabled(int bus,int channel) {
    assert(bus==2);return channel==1?dma1:dma2;
}
#define LL_DMA_IsEnabledChannel(...) is_dma_enabled(__VA_ARGS__)
void enable_dma(int bus,int ch) {(void)bus;(void)ch;writes++;}
#define LL_DMA_EnableChannel(...) enable_dma(__VA_ARGS__)
#define LL_TIM_ClearFlag_UPDATE(x) ((void)(x),++writes)
#define LL_TIM_GenerateEvent_UPDATE(x) ((void)(x),++writes)
#define LL_TIM_EnableCounter(x) ((void)(x),++writes)
void LL_GPIO_ResetOutputPin(int port,int pin) {(void)port;(void)pin;writes++;}
void furi_hal_gpio_init_ex(const GpioPin* pin,int mode,int pull,int speed,int alt) {
 (void)pin;(void)mode;(void)pull;(void)speed;(void)alt;writes++;
}
void furi_hal_gpio_init(const GpioPin* pin,int mode,int pull,int speed) {
 (void)pin;(void)mode;(void)pull;(void)speed;writes++;
}
void furi_hal_interrupt_set_isr(int irq,void(*fn)(void*),void* ctx) {
 (void)irq;(void)fn;(void)ctx;writes++;
}
void furi_delay_us(uint32_t ms) {(void)ms;}
void furi_crash(void) {abort();}
void* controlled_malloc(size_t n) {
 allocs++;
 if(fail_malloc_on && allocs==fail_malloc_on) return NULL;
 void* p=malloc(n);
 if(p)allocated_ok++;
 return p;
}
void controlled_free(void* p) {if(p)freed++;free(p);}
#define malloc controlled_malloc
#define free controlled_free
FuriSemaphore fake_semaphore;
FuriSemaphore* furi_semaphore_alloc(int max,int start) {
 assert(max==1 && start==0);return &fake_semaphore;
}
void furi_semaphore_free(FuriSemaphore* sem) {assert(sem==&fake_semaphore);}
unsigned furi_ms_to_ticks(unsigned ms) {return ms;}
FuriStatus furi_semaphore_acquire(FuriSemaphore* sem,unsigned ticks) {
 assert(sem==&fake_semaphore && ticks==100);
 waits++;
 if(lose_clock) {tim1_clock=false;return FuriStatusErrorTimeout;}
 if(stop_signaled) return FuriStatusOk;
 assert(waits<8);return FuriStatusErrorTimeout;
}
static FuriHalInfraredTxGetDataState callback(void* ctx,uint32_t* duration,bool* level) {
 (void)ctx;*duration=24;*level=true;return FuriHalInfraredTxGetDataStateLastDone;
}
void furi_hal_infrared_tx_fill_buffer(uint8_t n,uint8_t shift) {
 assert(n<2 && shift==INFRARED_POLARITY_SHIFT);infrared_tim_tx.buffer[n].size=2;
}
void furi_hal_infrared_configure_tim_pwm_tx(uint32_t f,float d) {
 (void)f;(void)d;writes++;
}
void furi_hal_infrared_configure_tim_cmgr2_dma_tx(void) {writes++;}
void furi_hal_infrared_configure_tim_rcr_dma_tx(void) {writes++;}
void furi_hal_infrared_tx_dma_set_polarity(uint8_t n,uint8_t shift) {
 (void)n;(void)shift;writes++;
}
void furi_hal_infrared_tx_dma_set_buffer(uint8_t n) {(void)n;writes++;}
"""
TEST=r"""
static void initialize_callback(void) {infrared_tim_tx.data_callback=callback;}
static void reset_test(void) {
 assert(infrared_tim_tx.buffer[0].data==NULL);
 assert(infrared_tim_tx.buffer[1].data==NULL);
 assert(infrared_tim_tx.buffer[0].polarity==NULL);
 assert(infrared_tim_tx.buffer[1].polarity==NULL);
 assert(infrared_tim_tx.stop_semaphore==NULL);
 writes=claims=releases=allocs=allocated_ok=freed=waits=0;
 tim1_clock=dma1=dma2=lose_clock=false;
 claim_allowed=false;release_ok=true;fail_malloc_on=0;
 last_claim_mask=0;stop_signaled=0;
 furi_hal_infrared_state=InfraredStateIdle;
 infrared_e11_tx_handle=infrared_e11_tx_mask=0U;infrared_e11_tx_fault=false;
 infrared_tx_output=FuriHalInfraredTxPinInternal;
 initialize_callback();
}
int main(void) {
 reset_test();
 assert(!furi_hal_infrared_async_tx_try_start(38000U,0.33f));
 assert(writes==0 && allocs==0 && claims==1);
 assert(infrared_e11_tx_handle==0U && !infrared_e11_tx_fault);
 /* Existing native TIM1 / DMA active before claim: reject with NO GPIO. */
 reset_test();claim_allowed=true;tim1_clock=true;
 assert(!furi_hal_infrared_async_tx_try_start(38000U,0.33f));
 assert(writes==0 && allocs==0 && claims==1 && releases==1);
 reset_test();claim_allowed=true;dma2=true;
 assert(!furi_hal_infrared_async_tx_try_start(38000U,0.33f));
 assert(writes==0 && releases==1 && !infrared_e11_tx_handle);
 /* Faulting temporary release permanently denies unsafe retry. */
 reset_test();claim_allowed=true;tim1_clock=true;release_ok=false;
 assert(!furi_hal_infrared_async_tx_try_start(38000U,0.33f));
 assert(infrared_e11_tx_fault && infrared_e11_tx_handle==99U);
 assert(!furi_hal_infrared_async_tx_try_start(38000U,0.33f));
 assert(claims==1 && writes==0);
 /* Memory failures 1..4 are handled without timer/DMA/IRQ writes. */
 for(int fail=1;fail<=4;fail++) {
   reset_test();claim_allowed=true;fail_malloc_on=fail;
   assert(!furi_hal_infrared_async_tx_try_start(38000U,0.33f));
   assert(writes==0 && !infrared_e11_tx_handle && releases==1);
   assert(allocs==4 && allocated_ok==3 && freed==allocated_ok);
   assert(!infrared_tim_tx.stop_semaphore);
 }
 /* Valid TX claim, START and normal semaphore STOP release. */
 reset_test();claim_allowed=true;
 assert(furi_hal_infrared_async_tx_try_start(38000U,0.33f));
 assert(tim1_clock && writes>0 && infrared_e11_tx_handle==99U);
 assert(last_claim_mask==FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL);
 assert(furi_hal_infrared_state==InfraredStateAsyncTx);
 furi_hal_infrared_state=InfraredStateAsyncTxStopped;
 stop_signaled=1;
 assert(furi_hal_infrared_async_tx_try_wait_termination());
 assert(releases==1 && !tim1_clock && !infrared_e11_tx_handle);
 assert(freed==4 && infrared_tim_tx.stop_semaphore==NULL);
 /* External PA7 must be part of the atomic claim. */
 reset_test();claim_allowed=true;infrared_tx_output=FuriHalInfraredTxPinExtPA7;
 assert(furi_hal_infrared_async_tx_try_start(38000U,0.33f));
 assert(last_claim_mask==FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7);
 furi_hal_infrared_state=InfraredStateAsyncTxStopped;stop_signaled=1;
 assert(furi_hal_infrared_async_tx_try_wait_termination());
 /* STOP failed lease release -> sticky, no new start */
 reset_test();claim_allowed=true;release_ok=false;
 assert(furi_hal_infrared_async_tx_try_start(38000U,0.33f));
 furi_hal_infrared_state=InfraredStateAsyncTxStopped;stop_signaled=1;
 assert(!furi_hal_infrared_async_tx_try_wait_termination());
 assert(infrared_e11_tx_fault && infrared_e11_tx_handle==99U);
 assert(!furi_hal_infrared_async_tx_try_start(38000U,0.33f));
 /* Unexpected timer disappearance must abort bounded WAIT,
  * leaving GPIO/DMA/IRQ and original handle untouched.
  */
 reset_test();claim_allowed=true;
 assert(furi_hal_infrared_async_tx_try_start(38000U,0.33f));
 furi_hal_infrared_state=InfraredStateAsyncTxStopReq;
 lose_clock=true;
 int w=writes;
 assert(!furi_hal_infrared_async_tx_try_wait_termination());
 assert(infrared_e11_tx_fault && infrared_e11_tx_handle==99U);
 assert(writes==w && waits==1);
 puts("E11 IR TX actual START/free/WAIT C PASS: TIM1 DMA2/PA7, BUSY, malloc, release fault, clock loss");
 return 0;
}
"""

RESOURCE_TEST=r"""
#define REQUIRE(x) do{if(!(x)){fprintf(stderr,"IR TX lease test failure at %d\n",__LINE__);exit(1);}}while(0)
int main(void) {
 uint32_t a=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL);
 REQUIRE(a);
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_PWM_PA7));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_NFC_TIMERS));
 REQUIRE(furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_RX_TIM2));
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7));
 REQUIRE(!furi_hal_resource_lease_release(a,FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7));
 REQUIRE(furi_hal_resource_lease_release(a,FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL));
 uint32_t pin=furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_MONITOR_PA7);
 REQUIRE(pin);
 REQUIRE(!furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7));
 REQUIRE(furi_hal_resource_lease_release(pin,FURI_HAL_LEASE_MONITOR_PA7));
 REQUIRE(furi_hal_resource_lease_try_acquire(
    FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL|(1U<<31))==0U);
 puts("E11 IR TX actual firmware allocator masks PASS: TIM1/DMA2/PA7 conflicts");
 return 0;
}
"""

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("momentum_root",type=Path)
    args=ap.parse_args()
    root=args.momentum_root.resolve()
    ir=(root/"targets/f7/furi_hal/furi_hal_infrared.c").read_text()
    worker=(root/"lib/infrared/worker/infrared_worker.c").read_text()
    head=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    resource=(root/"targets/f7/furi_hal/furi_hal_resources.c").read_text()
    api=(root/"targets/f7/api_symbols.csv").read_text()
    assert "/* E11 native infrared TX timer/DMA/PA7 cooperative owner. */" in ir
    assert "FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7" in head
    assert "mask == FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7" in resource
    assert "Function,+,furi_hal_infrared_async_tx_try_start,_Bool," in api
    assert "furi_hal_infrared_async_tx_try_start(" in worker
    assert "if(!furi_hal_infrared_async_tx_try_wait_termination())" in worker
    assert worker.index("if(!furi_hal_infrared_async_tx_try_start(")<worker.index(
        "instance->state = InfraredWorkerStateStopTx;",
        worker.index("static int32_t infrared_worker_tx_thread("))
    assert ir.index("if(!infrared_e11_tx_claim()) return false;")<ir.index(
        "infrared_tim_tx.buffer[0].data = malloc(")
    assert ir.index("infrared_e11_tx_release();")<ir.index(
        "bool furi_hal_infrared_async_tx_try_start(")
    # exact patched production helper and TX start/free/stop code
    helpers=ir[ir.index("/* E11 native infrared TX timer/DMA/PA7 cooperative owner. */"):
               ir.index("static void furi_hal_infrared_tim_rx_isr(")]
    # e11 helper is inserted after function declarations before RX ISR
    funcs=ir[ir.index("static void furi_hal_infrared_async_tx_free_resources(void) {"):
             ir.index("void furi_hal_infrared_async_tx_set_data_isr_callback(")]
    with tempfile.TemporaryDirectory(prefix="labmate_ir_tx_e11_") as td:
        tmp=Path(td)
        exe=tmp/"test"
        (tmp/"host.c").write_text(STUB+"\n"+helpers+"\n"+funcs+"\n"+TEST)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-O0",str(tmp/"host.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
        resource_prefix=r"""
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
        macros=head[head.index("enum {\n    FuriHalLeaseTim1"):
                    head.index("/* Returns unique nonzero")]
        impl=resource[resource.index("/* Firmware-owned E11 lease primitive"):
                      resource.index("const GpioPinRecord* furi_hal_resources_pin_by_number")]
        (tmp/"lease.c").write_text(resource_prefix+macros+impl+RESOURCE_TEST)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-pedantic",
                        "-pthread",str(tmp/"lease.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 IR TX actual native C + native worker contract + firmware lease C HOST PASS; NO DEVICE")

if __name__=="__main__":
    main()
