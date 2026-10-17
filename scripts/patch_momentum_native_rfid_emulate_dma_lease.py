#!/usr/bin/env python3
"""E11 native RFID TIM2 + DMA2 CH1/CH2 atomic emulation lease, pinned only.

No device/flash/Stable changes. Caller BUSY handling and field mode are
separate gates: this patch alone does not prove end-to-end LF RFID safety.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_lfrfid_busy_ui import EXPECTED as UI_DIRTY, APPH, READ, RAW

PIN = "d3f89dfe2ef6b01839201598e9be1590cba80322"
H = "targets/f7/furi_hal/furi_hal_resources.h"
R = "targets/f7/furi_hal/furi_hal_resources.c"
RFID = "targets/f7/furi_hal/furi_hal_rfid.c"
RFID_H = "targets/f7/furi_hal/furi_hal_rfid.h"
API = "targets/f7/api_symbols.csv"
MARK = "/* E11 native RFID emulate TIM2/DMA2 composite owner. */"
EXPECTED = UI_DIRTY | {APPH, READ, RAW}

def once(s: str, old: str, new: str) -> str:
    if s.count(old) != 1:
        raise ValueError("Ambiguous/missing pinned RFID emulate source anchor: "+repr(old[:110]))
    return s.replace(old, new, 1)

def patch(h: str, res: str, rfid: str, pub: str, api: str):
    if MARK in rfid or "FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA" in h:
        raise ValueError("Emulate DMA stage already present")
    if "/* E11 native RFID capture TIM2 owner. */" not in rfid:
        raise ValueError("Native READ and CAPTURE predecessor absent")
    h=once(h,
        "#define FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2 (FuriHalLeaseTim2)\n",
        "#define FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2 (FuriHalLeaseTim2)\n"
        "/* RFID internal LF emulate: TIM2 + both shared DMA2 hardware channels. */\n"
        "#define FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA (FuriHalLeaseTim2|FuriHalLeaseDma2Ch1|FuriHalLeaseDma2Ch2)\n")
    res=once(res,
        "           mask == FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2 ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA ||\n")
    rfid=once(rfid,
        "static void furi_hal_rfid_dma_isr(void* context) {\n    UNUSED(context);\n",
        """/* E11 native RFID emulate TIM2/DMA2 composite owner. */
static uint32_t e11_rfid_emulate_handle;
static bool e11_rfid_emulate_fault;

static bool e11_rfid_emulate_ready(void) {
    if(!e11_rfid_emulate_handle || e11_rfid_emulate_fault) return false;
    if(!furi_hal_bus_is_enabled(FURI_HAL_RFID_EMULATE_TIMER_BUS) ||
       !LL_DMA_IsEnabledChannel(RFID_DMA_CH1_DEF) ||
       !LL_DMA_IsEnabledChannel(RFID_DMA_CH2_DEF)) {
        e11_rfid_emulate_fault=true;
        return false;
    }
    return true;
}

static void furi_hal_rfid_dma_isr(void* context) {
    UNUSED(context);
    /* No foreign DMA flags, callbacks or interrupt state touched. */
    if(!e11_rfid_emulate_ready()) return;
""")
    rfid=once(rfid,
        """void furi_hal_rfid_tim_emulate_dma_start(
    uint32_t* duration,
    uint32_t* pulse,
    size_t length,
    FuriHalRfidDMACallback callback,
    void* context) {
    furi_check(furi_hal_rfid);

    // setup interrupts""",
        """bool furi_hal_rfid_tim_emulate_dma_try_start(
    uint32_t* duration,
    uint32_t* pulse,
    size_t length,
    FuriHalRfidDMACallback callback,
    void* context) {
    furi_check(furi_hal_rfid);
    if(!duration || !pulse || !length || !callback ||
       e11_rfid_emulate_handle || e11_rfid_emulate_fault) return false;
    const uint32_t lease =
        furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA);
    if(!lease) return false;
    /* Check legacy noncooperating HAL consumers before ANY pin/callback/
     * IRQ/timer/DMA state change. This is not a fix for their LL races.
     */
    if(furi_hal_bus_is_enabled(FURI_HAL_RFID_EMULATE_TIMER_BUS) ||
       LL_DMA_IsEnabledChannel(RFID_DMA_CH1_DEF) ||
       LL_DMA_IsEnabledChannel(RFID_DMA_CH2_DEF)) {
        if(!furi_hal_resource_lease_release(
               lease,FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA)) {
            e11_rfid_emulate_handle=lease;
            e11_rfid_emulate_fault=true;
        }
        return false;
    }
    e11_rfid_emulate_handle=lease;

    // setup interrupts""")
    rfid=once(rfid,
        """    LL_TIM_SetCounter(FURI_HAL_RFID_EMULATE_TIMER, 0);
    LL_TIM_EnableCounter(FURI_HAL_RFID_EMULATE_TIMER);
}

void furi_hal_rfid_tim_emulate_dma_stop(void) {
    LL_TIM_DisableCounter""",
        """    LL_TIM_SetCounter(FURI_HAL_RFID_EMULATE_TIMER, 0);
    LL_TIM_EnableCounter(FURI_HAL_RFID_EMULATE_TIMER);
    return true;
}

/* Original public void ABI retained. Native workers use bool START. */
void furi_hal_rfid_tim_emulate_dma_start(
    uint32_t* duration,
    uint32_t* pulse,
    size_t length,
    FuriHalRfidDMACallback callback,
    void* context) {
    (void)furi_hal_rfid_tim_emulate_dma_try_start(
        duration,pulse,length,callback,context);
}

void furi_hal_rfid_tim_emulate_dma_stop(void) {
    /* STOP after denied START is harmless, even with foreign TIM2/DMA. */
    if(!e11_rfid_emulate_ready()) return;
    LL_TIM_DisableCounter""")
    rfid=once(rfid,
        """    furi_hal_bus_disable(FURI_HAL_RFID_EMULATE_TIMER_BUS);

    FURI_CRITICAL_EXIT();
}

void furi_hal_rfid_set_read_period""",
        """    furi_hal_bus_disable(FURI_HAL_RFID_EMULATE_TIMER_BUS);

    FURI_CRITICAL_EXIT();
    furi_hal_rfid->dma_callback = NULL;
    const uint32_t owner=e11_rfid_emulate_handle;
    if(furi_hal_resource_lease_release(
           owner,FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA)) {
        e11_rfid_emulate_handle=0U;
    } else {
        e11_rfid_emulate_fault=true;
    }
}

void furi_hal_rfid_set_read_period""")
    pub=once(pub,
        """void furi_hal_rfid_tim_emulate_dma_stop(void);""",
        """/* Atomic TIM2+DMA2 owner; false means BUSY/invalid before hardware change. */
bool furi_hal_rfid_tim_emulate_dma_try_start(
    uint32_t* duration,
    uint32_t* pulse,
    size_t length,
    FuriHalRfidDMACallback callback,
    void* context);

void furi_hal_rfid_tim_emulate_dma_stop(void);""")
    api=once(api,
        'Function,+,furi_hal_rfid_tim_emulate_dma_start,void,"uint32_t*, uint32_t*, size_t, FuriHalRfidDMACallback, void*"\n',
        'Function,+,furi_hal_rfid_tim_emulate_dma_start,void,"uint32_t*, uint32_t*, size_t, FuriHalRfidDMACallback, void*"\n'
        'Function,+,furi_hal_rfid_tim_emulate_dma_try_start,_Bool,"uint32_t*, uint32_t*, size_t, FuriHalRfidDMACallback, void*"\n')
    return h,res,rfid,pub,api

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    args=p.parse_args()
    root=args.firmware_root.resolve()
    try:
        head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if head!=PIN: raise ValueError("Not pinned Momentum source")
        seen=set()
        for ln in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(ln)<4 or ln[:2]=="??" or "->" in ln:
                raise ValueError("Untracked or renamed native source")
            seen.add(ln[3:])
        if seen!=EXPECTED:
            raise ValueError("Unreviewed native source changes: "+repr(sorted(seen^EXPECTED)))
        paths=(H,R,RFID,RFID_H,API)
        originals=[(root/name).read_text(encoding="utf-8") for name in paths]
        changed=patch(*originals)
        print("E11 RFID EMULATE DMA2 ATOMIC SOURCE PREFLIGHT PASS")
        if args.apply:
            for name,data in zip(paths,changed):
                (root/name).write_text(data,encoding="utf-8")
            print("EMULATE SOURCE PATCH ONLY; FIELD/CALLERS UNMIGRATED; NO FLASH")
        else:
            print("READ ONLY; no files changed")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as ex:
        print("E11 RFID EMULATE SOURCE REFUSED: "+str(ex),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
