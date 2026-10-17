#!/usr/bin/env python3
"""E11 native infrared TX TIM1+DMA2 ch1/2 + optional PA7 lease stage.

PINNED source only, after tested native infrared RX patch. Source
edits include worker bool BUSY route, guarded DMA completion,
unstarted allocation rollback and nonblocking failure shutdown.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

PINNED="d3f89dfe2ef6b01839201598e9be1590cba80322"
HEADER="targets/f7/furi_hal/furi_hal_resources.h"
RES="targets/f7/furi_hal/furi_hal_resources.c"
IR="targets/f7/furi_hal/furi_hal_infrared.c"
PUBLIC="targets/furi_hal_include/furi_hal_infrared.h"
WORKER="lib/infrared/worker/infrared_worker.c"
SYMBOLS="targets/f7/api_symbols.csv"
MARKER="/* E11 native infrared TX timer/DMA/PA7 cooperative owner. */"
EXPECTED={
    "targets/furi_hal_include/furi_hal_i2c.h",
    "targets/f7/furi_hal/furi_hal_i2c.c",
    "targets/f7/furi_hal/furi_hal_resources.h",
    "targets/f7/furi_hal/furi_hal_resources.c",
    "targets/f7/furi_hal/furi_hal_gpio.h",
    "targets/f7/furi_hal/furi_hal_gpio.c",
    "targets/f7/furi_hal/furi_hal_pwm.c",
    "targets/f7/api_symbols.csv",
    "applications/system/js_app/modules/js_gpio.c",
    "lib/pulse_reader/pulse_reader.c",
    "lib/digital_signal/digital_sequence.c",
    "targets/f7/furi_hal/furi_hal_ibutton.c",
    "targets/f7/furi_hal/furi_hal_ibutton.h",
    "lib/ibutton/protocols/misc/protocol_group_misc.c",
    "targets/f7/furi_hal/furi_hal_nfc_timer.c",
    "targets/f7/furi_hal/furi_hal_nfc_i.h",
    "targets/f7/furi_hal/furi_hal_nfc.c",
    "targets/f7/furi_hal/furi_hal_infrared.c",
}

def change(s: str, old: str, new: str) -> str:
    if s.count(old)!=1:
        raise ValueError("Unrecognized native infrared TX source signature: "+repr(old[:95]))
    return s.replace(old,new,1)

LEASE_HELPERS="""/* E11 native infrared TX timer/DMA/PA7 cooperative owner. */
static uint32_t infrared_e11_tx_handle;
static uint32_t infrared_e11_tx_mask;
static bool infrared_e11_tx_fault;

static bool infrared_e11_tx_ready(void) {
    if(!infrared_e11_tx_handle || infrared_e11_tx_fault) return false;
    if(!furi_hal_bus_is_enabled(INFRARED_DMA_TIMER_BUS)) {
        infrared_e11_tx_fault = true;
        return false;
    }
    return true;
}

static void infrared_e11_tx_release(void) {
    if(!infrared_e11_tx_handle || infrared_e11_tx_fault) return;
    if(furi_hal_resource_lease_release(infrared_e11_tx_handle, infrared_e11_tx_mask)) {
        infrared_e11_tx_handle = 0U;
        infrared_e11_tx_mask = 0U;
    } else {
        infrared_e11_tx_fault = true;
    }
}

static bool infrared_e11_tx_claim(void) {
    if(infrared_e11_tx_handle || infrared_e11_tx_fault) return false;
    const uint32_t mask = infrared_tx_output == FuriHalInfraredTxPinExtPA7 ?
        FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7 : FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL;
    const uint32_t handle = furi_hal_resource_lease_try_acquire(mask);
    if(!handle) return false;
    /* Defend against pre-existing noncooperating LL users before
     * touching DMA, timer registers, peripheral IRQs or PA7.
     * Cannot eliminate races with direct native LL users.
     */
    if(furi_hal_bus_is_enabled(INFRARED_DMA_TIMER_BUS) ||
       LL_DMA_IsEnabledChannel(INFRARED_DMA_CH1_DEF) ||
       LL_DMA_IsEnabledChannel(INFRARED_DMA_CH2_DEF)) {
        if(!furi_hal_resource_lease_release(handle,mask)) {
            infrared_e11_tx_handle=handle;
            infrared_e11_tx_mask=mask;
            infrared_e11_tx_fault=true;
        }
        return false;
    }
    infrared_e11_tx_handle=handle;
    infrared_e11_tx_mask=mask;
    return true;
}

static bool infrared_e11_tx_abort_unstarted(void) {
    /* No DMA/IRQ or output GPIO was modified yet. Release only
     * the newly allocated CPU resources and the exact claimed mask.
     */
    if(infrared_tim_tx.stop_semaphore) {
        furi_semaphore_free(infrared_tim_tx.stop_semaphore);
        infrared_tim_tx.stop_semaphore=NULL;
    }
    for(size_t i=0;i<2;i++) {
        free(infrared_tim_tx.buffer[i].data);
        free(infrared_tim_tx.buffer[i].polarity);
        infrared_tim_tx.buffer[i].data=NULL;
        infrared_tim_tx.buffer[i].polarity=NULL;
    }
    infrared_e11_tx_release();
    return false;
}

"""

def patch(h:str,r:str,ir:str,pub:str,worker:str,api:str):
    if MARKER in ir or "FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL" in h:
        raise ValueError("Native IR TX patch previously applied")
    if "/* LabMate E11 native infrared TIM2 RX owner. */" not in ir:
        raise ValueError("Native RX prerequisite missing")
    h=change(h,
        "#define FURI_HAL_LEASE_NATIVE_IR_RX_TIM2 (FuriHalLeaseTim2)\n",
        "#define FURI_HAL_LEASE_NATIVE_IR_RX_TIM2 (FuriHalLeaseTim2)\n"
        "/* IR TX: DMA2 ch1/2 are unique hardware resources, NOT DMA1. */\n"
        "enum { FuriHalLeaseDma2Ch1=(1U<<25), FuriHalLeaseDma2Ch2=(1U<<26) };\n"
        "#define FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL (FuriHalLeaseTim1|FuriHalLeaseDma2Ch1|FuriHalLeaseDma2Ch2)\n"
        "#define FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7 (FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL|FuriHalLeasePa7)\n"
        "/* Pa7-only short acquisition during accessory presence detection. */\n"
        "#define FURI_HAL_LEASE_NATIVE_IR_DETECT_PA7 (FuriHalLeasePa7)\n")
    r=change(r,
        "           mask == FURI_HAL_LEASE_NATIVE_IR_RX_TIM2 ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_IR_RX_TIM2 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_IR_TX_INTERNAL ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7 ||\n")
    ir=change(ir,
        "static void furi_hal_infrared_tx_dma_isr(void*);\n",
        "static void furi_hal_infrared_tx_dma_isr(void*);\n\n"+LEASE_HELPERS)
    ir=change(ir,
        "static void furi_hal_infrared_tx_dma_terminate(void) {\n",
        "static void furi_hal_infrared_tx_dma_terminate(void) {\n"
        "    if(!infrared_e11_tx_ready()) return;\n")
    ir=change(ir,
        "static void furi_hal_infrared_tx_dma_polarity_isr(void* context) {\n    UNUSED(context);\n",
        "static void furi_hal_infrared_tx_dma_polarity_isr(void* context) {\n"
        "    UNUSED(context);\n"
        "    if(!infrared_e11_tx_ready()) return;\n")
    ir=change(ir,
        "static void furi_hal_infrared_tx_dma_isr(void* context) {\n    UNUSED(context);\n",
        "static void furi_hal_infrared_tx_dma_isr(void* context) {\n"
        "    UNUSED(context);\n"
        "    if(!infrared_e11_tx_ready()) return;\n")
    ir=change(ir,
        """static void furi_hal_infrared_async_tx_free_resources(void) {
    furi_check(""",
        """static void furi_hal_infrared_async_tx_free_resources(void) {
    /* An unexpected TIM1 clock loss is not authorization to tear
     * down a newly started foreign DMA/IRQ/GPIO owner.
     */
    if(!infrared_e11_tx_ready()) return;
    furi_check(""")
    ir=change(ir,
        """    infrared_tim_tx.buffer[1].polarity = NULL;
}

void furi_hal_infrared_async_tx_start""",
        """    infrared_tim_tx.buffer[1].polarity = NULL;
    infrared_tim_tx.stop_semaphore = NULL;
    infrared_e11_tx_release();
}

void furi_hal_infrared_async_tx_start""")
    ir=change(ir,
        "void furi_hal_infrared_async_tx_start(uint32_t freq, float duty_cycle) {",
        "bool furi_hal_infrared_async_tx_try_start(uint32_t freq, float duty_cycle) {")
    ir=change(ir,
        """    furi_check(furi_hal_infrared_state == InfraredStateIdle);
    furi_check(infrared_tim_tx.buffer[0].data == NULL);""",
        """    /* Sticky failed release must deny a new start before the legacy
     * state assertion. Otherwise a STOP-release fault would crash.
     */
    if(infrared_e11_tx_handle || infrared_e11_tx_fault) return false;
    furi_check(furi_hal_infrared_state == InfraredStateIdle);
    furi_check(infrared_tim_tx.buffer[0].data == NULL);""")
    ir=change(ir,
        """    furi_check(infrared_tim_tx.buffer[1].polarity == NULL);

    size_t alloc_size_data""",
        """    furi_check(infrared_tim_tx.buffer[1].polarity == NULL);

    /* BUSY must be observable by the worker BEFORE any semaphore
     * or DMA buffers are allocated. Never enter WAIT/STOP on deny.
     */
    if(!infrared_e11_tx_claim()) return false;

    size_t alloc_size_data""")
    ir=change(ir,
        """    infrared_tim_tx.stop_semaphore = furi_semaphore_alloc(1, 0);
    infrared_tim_tx.cycle_duration""",
        """    if(!infrared_tim_tx.buffer[0].data || !infrared_tim_tx.buffer[1].data ||
       !infrared_tim_tx.buffer[0].polarity || !infrared_tim_tx.buffer[1].polarity)
        return infrared_e11_tx_abort_unstarted();
    infrared_tim_tx.stop_semaphore = furi_semaphore_alloc(1, 0);
    if(!infrared_tim_tx.stop_semaphore) return infrared_e11_tx_abort_unstarted();
    infrared_tim_tx.cycle_duration""")
    ir=change(ir,
        """    furi_hal_infrared_tx_fill_buffer(0, INFRARED_POLARITY_SHIFT);

    furi_hal_bus_enable(INFRARED_DMA_TIMER_BUS);""",
        """    furi_hal_infrared_tx_fill_buffer(0, INFRARED_POLARITY_SHIFT);

    /* A legacy caller might have enabled TIM1 during CPU allocation.
     * There are still no timer/DMA/IRQ/GPIO changes by this TX.
     */
    if(furi_hal_bus_is_enabled(INFRARED_DMA_TIMER_BUS) ||
       LL_DMA_IsEnabledChannel(INFRARED_DMA_CH1_DEF) ||
       LL_DMA_IsEnabledChannel(INFRARED_DMA_CH2_DEF))
        return infrared_e11_tx_abort_unstarted();

    furi_hal_bus_enable(INFRARED_DMA_TIMER_BUS);""")
    ir=change(ir,
        """    LL_TIM_EnableCounter(INFRARED_DMA_TIMER);
    FURI_CRITICAL_EXIT();
}

void furi_hal_infrared_async_tx_wait_termination(void) {""",
        """    LL_TIM_EnableCounter(INFRARED_DMA_TIMER);
    FURI_CRITICAL_EXIT();
    return true;
}

/* Legacy void ABI stays available; worker uses the bool BUSY interface. */
void furi_hal_infrared_async_tx_start(uint32_t freq, float duty_cycle) {
    (void)furi_hal_infrared_async_tx_try_start(freq,duty_cycle);
}

bool furi_hal_infrared_async_tx_try_wait_termination(void) {""")
    ir=change(ir,
        """bool furi_hal_infrared_async_tx_try_wait_termination(void) {
    furi_check(furi_hal_infrared_state >= InfraredStateAsyncTx);
    furi_check(furi_hal_infrared_state < InfraredStateMAX);

    FuriStatus status;
    status = furi_semaphore_acquire(infrared_tim_tx.stop_semaphore, FuriWaitForever);
    furi_check(status == FuriStatusOk);
    furi_hal_infrared_async_tx_free_resources();
    furi_hal_infrared_state = InfraredStateIdle;
}

void furi_hal_infrared_async_tx_stop(void) {""",
        """bool furi_hal_infrared_async_tx_try_wait_termination(void) {
    if(!infrared_e11_tx_handle || infrared_e11_tx_fault ||
       furi_hal_infrared_state < InfraredStateAsyncTx ||
       furi_hal_infrared_state >= InfraredStateMAX) return false;
    /* Poll the original completion signal with a bounded interval.
     * A removed TIM1 clock cannot trap worker STOP/WAIT forever.
     */
    FuriStatus status;
    do {
        if(!infrared_e11_tx_ready()) return false;
        status = furi_semaphore_acquire(
            infrared_tim_tx.stop_semaphore,furi_ms_to_ticks(100));
    } while(status == FuriStatusErrorTimeout);
    if(status != FuriStatusOk) {
        infrared_e11_tx_fault=true;
        return false;
    }
    if(!infrared_e11_tx_ready()) return false;
    furi_hal_infrared_async_tx_free_resources();
    if(infrared_e11_tx_fault) return false;
    furi_hal_infrared_state = InfraredStateIdle;
    return true;
}

void furi_hal_infrared_async_tx_wait_termination(void) {
    (void)furi_hal_infrared_async_tx_try_wait_termination();
}

void furi_hal_infrared_async_tx_stop(void) {""")
    ir=change(ir,
        """void furi_hal_infrared_async_tx_stop(void) {
    furi_check(furi_hal_infrared_state >= InfraredStateAsyncTx);
    furi_check(furi_hal_infrared_state < InfraredStateMAX);

    FURI_CRITICAL_ENTER();""",
        """void furi_hal_infrared_async_tx_stop(void) {
    /* Called only after a real START by the patched worker.
     * Legacy clients may call it after a denied void START.
     */
    if(!infrared_e11_tx_handle || infrared_e11_tx_fault ||
       furi_hal_infrared_state < InfraredStateAsyncTx ||
       furi_hal_infrared_state >= InfraredStateMAX) return;
    if(!infrared_e11_tx_ready()) return;

    FURI_CRITICAL_ENTER();""")
    ir=change(ir,
        """FuriHalInfraredTxPin furi_hal_infrared_detect_tx_output(void) {
    for(FuriHalInfraredTxPin pin = FuriHalInfraredTxPinInternal + 1; //-V1008
        pin < FuriHalInfraredTxPinMax;
        ++pin) {
        const GpioPin* gpio = infrared_tx_pins[pin];
        furi_hal_gpio_init(gpio, GpioModeInput, GpioPullUp, GpioSpeedLow);
        furi_hal_cortex_delay_us(1000U);
        const bool level = furi_hal_gpio_read(gpio);
        furi_hal_gpio_init(gpio, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
        if(!level) return pin;
    }

    return FuriHalInfraredTxPinInternal;
}""",
        """FuriHalInfraredTxPin furi_hal_infrared_detect_tx_output(void) {
    /* Even accessory detection reconfigures PA7 twice. Protect the
     * temporary GPIO transaction, not only the TX timer session.
     */
    if(infrared_e11_tx_handle || infrared_e11_tx_fault ||
       furi_hal_infrared_state != InfraredStateIdle)
        return FuriHalInfraredTxPinInternal;
    const uint32_t mask=FURI_HAL_LEASE_NATIVE_IR_DETECT_PA7;
    const uint32_t lease=furi_hal_resource_lease_try_acquire(mask);
    if(!lease) return FuriHalInfraredTxPinInternal;
    FuriHalInfraredTxPin found=FuriHalInfraredTxPinInternal;
    for(FuriHalInfraredTxPin pin = FuriHalInfraredTxPinInternal + 1; //-V1008
        pin < FuriHalInfraredTxPinMax;
        ++pin) {
        const GpioPin* gpio = infrared_tx_pins[pin];
        furi_hal_gpio_init(gpio, GpioModeInput, GpioPullUp, GpioSpeedLow);
        furi_hal_cortex_delay_us(1000U);
        const bool level = furi_hal_gpio_read(gpio);
        furi_hal_gpio_init(gpio, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
        if(!level) {
            found=pin;
            break;
        }
    }
    if(!furi_hal_resource_lease_release(lease,mask)) {
        infrared_e11_tx_handle=lease;
        infrared_e11_tx_mask=mask;
        infrared_e11_tx_fault=true;
        return FuriHalInfraredTxPinInternal;
    }
    return found;
}
""")
    ir=change(ir,
        """    furi_check(tx_pin < FuriHalInfraredTxPinMax);
    infrared_tx_output = tx_pin;
}""",
        """    furi_check(tx_pin < FuriHalInfraredTxPinMax);
    /* Do not change GPIO identity beneath an owned DMA/PA7 lease. */
    if(furi_hal_infrared_state != InfraredStateIdle ||
       infrared_e11_tx_handle || infrared_e11_tx_fault) return;
    infrared_tx_output = tx_pin;
}""")
    pub=change(pub,
        "void furi_hal_infrared_async_tx_start(uint32_t freq, float duty_cycle);",
        """void furi_hal_infrared_async_tx_start(uint32_t freq, float duty_cycle);
/* E11: native worker uses this status-bearing, pre-side-effect START.
 * The published legacy void ABI remains unchanged.
 */
bool furi_hal_infrared_async_tx_try_start(uint32_t freq,float duty_cycle);
bool furi_hal_infrared_async_tx_try_wait_termination(void);""")
    worker=change(worker,
        """            furi_hal_infrared_async_tx_start(instance->tx.frequency, instance->tx.duty_cycle);

            if(!new_data_available) {""",
        """            if(!furi_hal_infrared_async_tx_try_start(
                   instance->tx.frequency,instance->tx.duty_cycle)) {
                /* No running DMA, no allocated stop semaphore. Never
                 * enter StopTx/WaitTxEnd or block on a denied START.
                 */
                running = false;
                break;
            }

            if(!new_data_available) {""")
    worker=change(worker,
        """        case InfraredWorkerStateWaitTxEnd:
            furi_hal_infrared_async_tx_wait_termination();
            instance->state = InfraredWorkerStateStartTx;""",
        """        case InfraredWorkerStateWaitTxEnd:
            if(!furi_hal_infrared_async_tx_try_wait_termination()) {
                running=false;
                break;
            }
            instance->state = InfraredWorkerStateStartTx;""")
    api=change(api,
        'Function,+,furi_hal_infrared_async_tx_start,void,"uint32_t, float"\n',
        'Function,+,furi_hal_infrared_async_tx_start,void,"uint32_t, float"\n'
        'Function,+,furi_hal_infrared_async_tx_try_start,_Bool,"uint32_t, float"\n'
        'Function,+,furi_hal_infrared_async_tx_try_wait_termination,_Bool,\n')
    return h,r,ir,pub,worker,api

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("firmware_root",type=Path)
    ap.add_argument("--apply",action="store_true")
    a=ap.parse_args()
    root=a.firmware_root.resolve()
    try:
        sha=subprocess.check_output(
            ["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if sha!=PINNED: raise ValueError("Wrong pinned Momentum SHA")
        dirty=set()
        for l in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(l)<4 or l[:2]=="??" or "->" in l:
                raise ValueError("Untracked or renamed firmware source refused")
            dirty.add(l[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unreviewed firmware source state "+repr(sorted(dirty)))
        paths=(HEADER,RES,IR,PUBLIC,WORKER,SYMBOLS)
        before=[(root/p).read_text(encoding="utf-8") for p in paths]
        after=patch(*before)
        print("E11 NATIVE INFRARED TX PINNED TIM1/DMA2/PA7+WORKER SOURCE CHECK PASS")
        if a.apply:
            for p,s in zip(paths,after):
                (root/p).write_text(s,encoding="utf-8")
            print("IR TX SOURCE PATCHED; NEVER FLASH THIS CI CANDIDATE")
        else:
            print("READ ONLY; NO FIRMWARE MODIFICATION")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as ex:
        print("E11 INFRARED TX REFUSED: "+str(ex),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
