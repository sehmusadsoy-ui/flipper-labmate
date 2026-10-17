#!/usr/bin/env python3
"""E11 pinned native RFID field detection atomic TIM1+TIM2+DMA2 owner.

Only pinned production HAL sources; does not flash hardware. Internal
iButton/NFC pin utilities and physical comparator/EXTI still need E11 review.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_lfrfid_emulate_busy import EXPECTED as EMU_DIRTY, SCENE

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
H="targets/f7/furi_hal/furi_hal_resources.h"
R="targets/f7/furi_hal/furi_hal_resources.c"
RFID="targets/f7/furi_hal/furi_hal_rfid.c"
RFID_H="targets/f7/furi_hal/furi_hal_rfid.h"
API="targets/f7/api_symbols.csv"
EXPECTED=EMU_DIRTY | {SCENE}
MARK="/* E11 native RFID field atomic TIM1/TIM2/DMA2 owner. */"

def once(source:str,old:str,new:str)->str:
    if source.count(old)!=1:
        raise ValueError("Pinned native RFID field anchor missing/ambiguous "+repr(old[:110]))
    return source.replace(old,new,1)

def patch(h:str,resource:str,rfid:str,header:str,api:str):
    if MARK in rfid or "FURI_HAL_LEASE_NATIVE_RFID_FIELD" in h:
        raise ValueError("Native RFID field owner already patched")
    if "/* E11 native RFID emulate TIM2/DMA2 composite owner. */" not in rfid:
        raise ValueError("Native RFID emulate DMA owner prerequisite missing")
    h=once(h,
        "#define FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA (FuriHalLeaseTim2|FuriHalLeaseDma2Ch1|FuriHalLeaseDma2Ch2)\n",
        "#define FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA (FuriHalLeaseTim2|FuriHalLeaseDma2Ch1|FuriHalLeaseDma2Ch2)\n"
        "/* Field detection spans BOTH TIM1 and TIM2 plus shared DMA2 CH1/CH2. */\n"
        "#define FURI_HAL_LEASE_NATIVE_RFID_FIELD (FuriHalLeaseTim1|FuriHalLeaseTim2|FuriHalLeaseDma2Ch1|FuriHalLeaseDma2Ch2)\n")
    resource=once(resource,
        "           mask == FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_RFID_EMULATE_DMA ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_RFID_FIELD ||\n")
    rfid=once(rfid,
        "void furi_hal_rfid_field_detect_start(void) {\n",
        """/* E11 native RFID field atomic TIM1/TIM2/DMA2 owner. */
static uint32_t e11_rfid_field_handle;
static bool e11_rfid_field_fault;

static bool e11_rfid_field_ready(void) {
    if(!e11_rfid_field_handle || e11_rfid_field_fault) return false;
    if(!furi_hal_bus_is_enabled(FURI_HAL_RFID_FIELD_COUNTER_TIMER_BUS) ||
       !furi_hal_bus_is_enabled(FURI_HAL_RFID_FIELD_TIMEOUT_TIMER_BUS) ||
       !LL_DMA_IsEnabledChannel(RFID_DMA_CH1_DEF) ||
       !LL_DMA_IsEnabledChannel(RFID_DMA_CH2_DEF)) {
        e11_rfid_field_fault=true;
        return false;
    }
    return true;
}

bool furi_hal_rfid_field_detect_try_start(void) {
    if(e11_rfid_field_handle || e11_rfid_field_fault) return false;
    const uint32_t lease =
        furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_FIELD);
    if(!lease) return false;
    /* No internal pin, timer, DMA or ISR is written before all four
     * resources have been claimed AND legacy clocks/DMA are checked.
     */
    if(furi_hal_bus_is_enabled(FURI_HAL_RFID_FIELD_COUNTER_TIMER_BUS) ||
       furi_hal_bus_is_enabled(FURI_HAL_RFID_FIELD_TIMEOUT_TIMER_BUS) ||
       LL_DMA_IsEnabledChannel(RFID_DMA_CH1_DEF) ||
       LL_DMA_IsEnabledChannel(RFID_DMA_CH2_DEF)) {
        if(!furi_hal_resource_lease_release(lease,FURI_HAL_LEASE_NATIVE_RFID_FIELD)) {
            e11_rfid_field_handle=lease;
            e11_rfid_field_fault=true;
        }
        return false;
    }
    e11_rfid_field_handle=lease;
""")
    rfid=once(rfid,
        """    LL_TIM_EnableCounter(FURI_HAL_RFID_FIELD_TIMEOUT_TIMER);
    LL_TIM_EnableIT_UPDATE(FURI_HAL_RFID_FIELD_TIMEOUT_TIMER);
}

void furi_hal_rfid_field_detect_stop(void) {
    LL_TIM_DisableCounter""",
        """    LL_TIM_EnableCounter(FURI_HAL_RFID_FIELD_TIMEOUT_TIMER);
    LL_TIM_EnableIT_UPDATE(FURI_HAL_RFID_FIELD_TIMEOUT_TIMER);
    return true;
}

/* Legacy public void HAL ABI retained. */
void furi_hal_rfid_field_detect_start(void) {
    (void)furi_hal_rfid_field_detect_try_start();
}

void furi_hal_rfid_field_detect_stop(void) {
    /* A rejected field start must NOT reset foreign TIM1/TIM2/DMA or
     * reconfigure unrelated iButton/NFC/RFID internal pin state.
     */
    if(!e11_rfid_field_ready()) return;
    LL_TIM_DisableIT_UPDATE(FURI_HAL_RFID_FIELD_TIMEOUT_TIMER);
    LL_TIM_DisableCounter""")
    rfid=once(rfid,
        """    furi_hal_rfid_pins_reset();

    FURI_CRITICAL_EXIT();
}

bool furi_hal_rfid_field_is_present(uint32_t* frequency) {
    furi_check(frequency);

    *frequency = furi_hal_rfid->field.counter * 10;""",
        """    furi_hal_rfid_pins_reset();

    FURI_CRITICAL_EXIT();
    const uint32_t owner=e11_rfid_field_handle;
    if(furi_hal_resource_lease_release(owner,FURI_HAL_LEASE_NATIVE_RFID_FIELD)) {
        e11_rfid_field_handle=0U;
    } else {
        e11_rfid_field_fault=true; /* Sticky: never reuse this claim. */
    }
}

bool furi_hal_rfid_field_is_present(uint32_t* frequency) {
    furi_check(frequency);
    if(!e11_rfid_field_ready()) {
        *frequency=0U;
        return false;
    }
    *frequency = furi_hal_rfid->field.counter * 10;""")
    header=once(header,
        "void furi_hal_rfid_field_detect_start(void);",
        "void furi_hal_rfid_field_detect_start(void);\n"
        "/* E11: atomic TIM1+TIM2+DMA2 claim, BUSY without GPIO/timer writes. */\n"
        "bool furi_hal_rfid_field_detect_try_start(void);")
    api=once(api,
        "Function,+,furi_hal_rfid_field_detect_start,void,\n",
        "Function,+,furi_hal_rfid_field_detect_start,void,\n"
        "Function,+,furi_hal_rfid_field_detect_try_start,_Bool,\n")
    return h,resource,rfid,header,api

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args()
    root=a.firmware_root.resolve()
    try:
        head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if head!=PIN: raise ValueError("Unpinned Momentum revision")
        dirty=set()
        for ln in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(ln)<4 or ln[:2]=="??" or "->" in ln:
                raise ValueError("Untracked/renamed checkout")
            dirty.add(ln[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unreviewed native source "+repr(sorted(dirty^EXPECTED)))
        paths=(H,R,RFID,RFID_H,API)
        original=[(root/p).read_text(encoding="utf-8") for p in paths]
        updated=patch(*original)
        print("E11 NATIVE RFID FIELD TIM1/TIM2/DMA2 ATOMIC SOURCE PREFLIGHT PASS")
        if a.apply:
            for name,data in zip(paths,updated):
                (root/name).write_text(data,encoding="utf-8")
            print("FIELD SOURCE ONLY; NO FLASH/DEVICE, INTERNAL GPIO/EXTI STILL OPEN")
        else:
            print("READ ONLY; no source files changed")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 NATIVE FIELD SOURCE REFUSED: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
