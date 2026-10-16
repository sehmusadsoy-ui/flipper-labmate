#!/usr/bin/env python3
"""E11 native infrared RX TIM2: exact pinned-source, zero-write BUSY guard.

This is intentionally RX ONLY: native infrared TX uses TIM1 + DMA2 CH1/2
and optional PA7. Void-return TX START plus worker STOP/WAIT can hang if
a claim is silently refused; no unsafe partial TX patch is attempted.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

BASE = "d3f89dfe2ef6b01839201598e9be1590cba80322"
HEADER = "targets/f7/furi_hal/furi_hal_resources.h"
SOURCE = "targets/f7/furi_hal/furi_hal_resources.c"
INFRARED = "targets/f7/furi_hal/furi_hal_infrared.c"
PREPATCHED = {
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
}
MARKER = "/* LabMate E11 native infrared TIM2 RX owner. */"

def sub(s: str, old: str, new: str) -> str:
    if s.count(old) != 1:
        raise ValueError("Missing/ambiguous Momentum infrared anchor "+repr(old[:95]))
    return s.replace(old,new,1)

def patch(h: str,r: str,ir: str) -> tuple[str,str,str]:
    if MARKER in ir or "FURI_HAL_LEASE_NATIVE_IR_RX_TIM2" in h:
        raise ValueError("Infrared RX lease already applied")
    h=sub(h,
        "#define FURI_HAL_LEASE_NATIVE_NFC_TIMERS (FuriHalLeaseTim1 | FuriHalLeaseTim17)\n",
        "#define FURI_HAL_LEASE_NATIVE_NFC_TIMERS (FuriHalLeaseTim1 | FuriHalLeaseTim17)\n"
        "/* Infrared internal RX is TIM2 only; not an external GPIO pin. */\n"
        "#define FURI_HAL_LEASE_NATIVE_IR_RX_TIM2 (FuriHalLeaseTim2)\n")
    r=sub(r,
        "           mask == FURI_HAL_LEASE_NATIVE_NFC_TIMERS ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_NFC_TIMERS ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_IR_RX_TIM2 ||\n")
    ir=sub(ir,
        "static InfraredTimRx infrared_tim_rx;\n",
        """static InfraredTimRx infrared_tim_rx;
/* LabMate E11 native infrared TIM2 RX owner. */
static uint32_t infrared_e11_rx_handle;
static bool infrared_e11_rx_fault;

static bool infrared_e11_rx_ready(void) {
    if(!infrared_e11_rx_handle || infrared_e11_rx_fault ||
       furi_hal_infrared_state != InfraredStateAsyncRx) return false;
    if(!furi_hal_bus_is_enabled(INFRARED_RX_TIMER_BUS)) {
        infrared_e11_rx_fault = true;
        return false;
    }
    return true;
}
""")
    ir=sub(ir,
        """static void furi_hal_infrared_tim_rx_isr(void* context) {
    UNUSED(context);

    static uint32_t previous_captured_ch2 = 0;""",
        """static void furi_hal_infrared_tim_rx_isr(void* context) {
    UNUSED(context);
    if(!infrared_e11_rx_ready()) return;

    static uint32_t previous_captured_ch2 = 0;""")
    ir=sub(ir,
        """void furi_hal_infrared_async_rx_start(void) {
    furi_check(furi_hal_infrared_state == InfraredStateIdle);

    furi_hal_gpio_init_ex(""",
        """void furi_hal_infrared_async_rx_start(void) {
    furi_check(furi_hal_infrared_state == InfraredStateIdle);

    /* Acquire before native GPIO alternate function, timer, ISR or clock.
     * This legacy void START cannot convey BUSY to callers. STOP and
     * set_timeout are guarded below to avoid foreign TIM2 writes.
     */
    if(infrared_e11_rx_handle || infrared_e11_rx_fault) return;
    const uint32_t lease =
        furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IR_RX_TIM2);
    if(!lease) return;
    if(furi_hal_bus_is_enabled(INFRARED_RX_TIMER_BUS)) {
        /* Legacy TIM2 holder did not take an E11 lease. */
        if(!furi_hal_resource_lease_release(
               lease,FURI_HAL_LEASE_NATIVE_IR_RX_TIM2)) {
            infrared_e11_rx_handle=lease;
            infrared_e11_rx_fault=true;
        }
        return;
    }
    infrared_e11_rx_handle=lease;

    furi_hal_gpio_init_ex(""")
    ir=sub(ir,
        """void furi_hal_infrared_async_rx_stop(void) {
    furi_check(furi_hal_infrared_state == InfraredStateAsyncRx);

    FURI_CRITICAL_ENTER();
    furi_hal_bus_disable(INFRARED_RX_TIMER_BUS);
    furi_hal_interrupt_set_isr(INFRARED_RX_IRQ, NULL, NULL);
    furi_hal_infrared_state = InfraredStateIdle;
    FURI_CRITICAL_EXIT();
}""",
        """void furi_hal_infrared_async_rx_stop(void) {
    /* If void START was denied, STOP must not disable a foreign TIM2. */
    if(furi_hal_infrared_state == InfraredStateIdle) return;
    furi_check(furi_hal_infrared_state == InfraredStateAsyncRx);
    if(!infrared_e11_rx_ready()) return;

    FURI_CRITICAL_ENTER();
    /* This RX timer was initialized by this holder. Release IRQ/clock
     * BEFORE returning its opaque firmware reservation.
     */
    furi_hal_bus_disable(INFRARED_RX_TIMER_BUS);
    furi_hal_interrupt_set_isr(INFRARED_RX_IRQ, NULL, NULL);
    furi_hal_infrared_state = InfraredStateIdle;
    FURI_CRITICAL_EXIT();
    const uint32_t handle=infrared_e11_rx_handle;
    if(furi_hal_resource_lease_release(handle,FURI_HAL_LEASE_NATIVE_IR_RX_TIM2)) {
        infrared_e11_rx_handle=0U;
    } else {
        infrared_e11_rx_fault=true;
    }
}""")
    ir=sub(ir,
        """void furi_hal_infrared_async_rx_set_timeout(uint32_t timeout_us) {
    LL_TIM_OC_SetCompareCH3""",
        """void furi_hal_infrared_async_rx_set_timeout(uint32_t timeout_us) {
    if(!infrared_e11_rx_ready()) return;
    LL_TIM_OC_SetCompareCH3""")
    # Preserve the RX+TX semantics otherwise. TX needs a separate mode
    # and worker-level bool start, stop/wait rollback design.
    return h,r,ir

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("firmware_root",type=Path)
    ap.add_argument("--apply",action="store_true")
    a=ap.parse_args()
    root=a.firmware_root.resolve()
    try:
        head=subprocess.check_output(
            ["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if head!=BASE:
            raise ValueError("Wrong Momentum source SHA")
        dirty=set()
        for line in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Unexpected untracked/renamed firmware file")
            dirty.add(line[3:])
        if dirty!=PREPATCHED:
            raise ValueError("Unexpected firmware prior source state "+repr(sorted(dirty)))
        paths=(HEADER,SOURCE,INFRARED)
        before=[(root/p).read_text(encoding="utf-8") for p in paths]
        after=patch(*before)
        print("E11 NATIVE IR RX TIM2 exact source preflight PASS")
        if a.apply:
            for p,c in zip(paths,after):
                (root/p).write_text(c,encoding="utf-8")
            print("PATCHED IR RX ONLY; TX UNMIGRATED; NO DEVICE/FLASH/USB/SD")
        else:
            print("READ-ONLY SOURCE CHECK")
        return 0
    except (OSError,subprocess.CalledProcessError,ValueError) as e:
        print("E11 IR RX SOURCE REFUSED: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
