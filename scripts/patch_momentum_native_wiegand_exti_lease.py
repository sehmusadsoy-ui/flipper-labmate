#!/usr/bin/env python3
"""E11 native debug Accessor Wiegand PA4+PA7 dual EXTI exact lifecycle.

Never overwrite native input callbacks; retain legacy begin()/end() ABI.
Source-only pinned Momentum patch, requires prior V2 firmware/RF owner stages.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_ext_cc1101_tx_lease import EXPECTED as TX_PRE, EXT

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
H="targets/f7/furi_hal/furi_hal_resources.h"
R="targets/f7/furi_hal/furi_hal_resources.c"
W="applications/debug/accessor/helpers/wiegand.cpp"
WH="applications/debug/accessor/helpers/wiegand.h"
APP="applications/debug/accessor/accessor_app.cpp"
MARK="/* E11 Accessor Wiegand PA4+PA7 EXTI4/EXTI7 owner. */"
EXPECTED=TX_PRE|{EXT}

def once(s,old,new):
    if s.count(old)!=1:
        raise ValueError("Pinned Wiegand exact-source anchor missing/ambiguous "+repr(old[:100]))
    return s.replace(old,new,1)

def patch(h,r,s,wh,app):
    if MARK in s or "FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7" in h:
        raise ValueError("Already-patched Wiegand")
    h=once(h,
        "#define FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 (FuriHalLeaseLpuart1|FuriHalLeasePc0|FuriHalLeaseExti0)\n",
        "#define FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 (FuriHalLeaseLpuart1|FuriHalLeasePc0|FuriHalLeaseExti0)\n"
        "/* Wiegand D0=PA4 and D1=PA7, both with shared physical EXTI aliases. */\n"
        "#define FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7 (FuriHalLeasePa4|FuriHalLeaseExti4|FuriHalLeasePa7|FuriHalLeaseExti7)\n")
    r=once(r,
        "           mask == FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7 ||\n")
    wh=once(wh,"#pragma once\n","#pragma once\n\n#include <stdint.h>\n")
    wh=once(wh,
        "    void begin(void);\n    void end(void);",
        "    void begin(void);\n    /* E11 true only after BOTH inputs and callback slots are owned. */\n"
        "    bool tryBegin(void);\n    /* Ignore stale callbacks after BUSY/fault. */\n"\n        "    bool e11IsActive(void) const { return e11_owner != 0U && !e11_fault; }\n"\n        "    void end(void);")
    wh=once(wh,
        "private:\n    static bool DoWiegandConversion(void);",
        "private:\n    uint32_t e11_owner = 0;\n    bool e11_fault = false;\n    static bool DoWiegandConversion(void);")
    s=once(s,
        "#include <furi_hal.h>\n",
        "#include <furi_hal.h>\n#include <furi_hal_resources.h>\n")
    s=once(s,
        """static void input_isr_d0(void* _ctx) {
    WIEGAND* _this = static_cast<WIEGAND*>(_ctx);
    _this->ReadD0();
}

static void input_isr_d1(void* _ctx) {
    WIEGAND* _this = static_cast<WIEGAND*>(_ctx);
    _this->ReadD1();
}""",
        """static void input_isr_d0(void* _ctx) {
    WIEGAND* _this = static_cast<WIEGAND*>(_ctx);
    if(!_this || !_this->e11IsActive()) return;
    _this->ReadD0();
}

static void input_isr_d1(void* _ctx) {
    WIEGAND* _this = static_cast<WIEGAND*>(_ctx);
    if(!_this || !_this->e11IsActive()) return;
    _this->ReadD1();
}""")
    s=once(s,
        """void WIEGAND::begin() {
    _lastWiegand = 0;
    _cardTempHigh = 0;
    _cardTemp = 0;
    _code = 0;
    _wiegandType = 0;
    _bitCount = 0;

    furi_hal_gpio_init_simple(pinD0, GpioModeInterruptFall); // Set D0 pin as input
    furi_hal_gpio_init_simple(pinD1, GpioModeInterruptFall); // Set D1 pin as input

    furi_hal_gpio_add_int_callback(pinD0, input_isr_d0, this);
    furi_hal_gpio_add_int_callback(pinD1, input_isr_d1, this);
}

void WIEGAND::end() {
    furi_hal_gpio_remove_int_callback(pinD0);
    furi_hal_gpio_remove_int_callback(pinD1);

    furi_hal_gpio_init_simple(pinD0, GpioModeAnalog);
    furi_hal_gpio_init_simple(pinD1, GpioModeAnalog);
}""",
        """/* E11 Accessor Wiegand PA4+PA7 EXTI4/EXTI7 owner. */
bool WIEGAND::tryBegin() {
    if(e11_owner || e11_fault) return false;
    const uint32_t lease=furi_hal_resource_lease_try_acquire(
        FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7);
    if(!lease) return false;

    e11_owner=lease;
    /* Two callback slots must both belong to this Wiegand object BEFORE
     * PA4/PA7 GPIO mode or signal counters are changed. On partial
     * reservation undo only OUR first callback, never foreign callbacks.
     */
    if(!furi_hal_gpio_try_add_int_callback(pinD0,input_isr_d0,this)) {
        if(furi_hal_resource_lease_release(
               lease,FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7)) {
            e11_owner=0U;
        } else {
            e11_fault=true;
        }
        return false;
    }
    if(!furi_hal_gpio_try_add_int_callback(pinD1,input_isr_d1,this)) {
        if(!furi_hal_gpio_try_remove_int_callback(pinD0,input_isr_d0,this)) {
            e11_fault=true;
            return false; /* A foreign replacement cannot be removed. */
        }
        if(furi_hal_resource_lease_release(
               lease,FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7)) {
            e11_owner=0U;
        } else {
            e11_fault=true;
        }
        return false;
    }
    _lastWiegand=0;
    _cardTempHigh=0;
    _cardTemp=0;
    _code=0;
    _wiegandType=0;
    _bitCount=0;
    furi_hal_gpio_init_simple(pinD0,GpioModeInterruptFall);
    furi_hal_gpio_init_simple(pinD1,GpioModeInterruptFall);
    return true;
}

void WIEGAND::begin() {
    if(!tryBegin()) FURI_LOG_W("Wiegand","PA4/PA7 EXTI resource BUSY");
}

void WIEGAND::end() {
    if(!e11_owner || e11_fault) return;
    /* Never force-remove another app's callback. On unexpected
     * replacement, enter sticky fault and avoid pin reset.
     */
    if(!furi_hal_gpio_try_remove_int_callback(pinD0,input_isr_d0,this)) {
        e11_fault=true;
        return;
    }
    if(!furi_hal_gpio_try_remove_int_callback(pinD1,input_isr_d1,this)) {
        e11_fault=true;
        return;
    }
    furi_hal_gpio_init_simple(pinD0,GpioModeAnalog);
    furi_hal_gpio_init_simple(pinD1,GpioModeAnalog);
    if(furi_hal_resource_lease_release(
           e11_owner,FURI_HAL_LEASE_NATIVE_WIEGAND_PA4_PA7)) {
        e11_owner=0U;
    } else {
        e11_fault=true;
    }
}""")
    # Accessor is a debug app; unlike the void Wiegand begin API, it
    # can explicitly avoid processing events when Wiegand cannot start.
    app=once(app,
        """    wiegand.begin();
    onewire_host_start(onewire_host);""",
        """    const bool wiegand_ready=wiegand.tryBegin();
    if(!wiegand_ready) FURI_LOG_W("Accessor","Wiegand PA4/PA7 resource BUSY");
    onewire_host_start(onewire_host);""")
    return h,r,s,wh,app

def main():
    p=argparse.ArgumentParser();p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args();root=a.firmware_root.resolve()
    try:
        sha=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if sha!=PIN: raise ValueError("Unpinned Momentum source")
        dirty=set()
        for line in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Untracked/renamed firmware source")
            dirty.add(line[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unknown source change(s): "+repr(sorted(dirty^EXPECTED)))
        paths=(H,R,W,WH,APP)
        before=[(root/p).read_text(encoding="utf-8") for p in paths]
        after=patch(*before)
        print("E11 NATIVE WIEGAND TWO-EXTI SOURCE PREFLIGHT PASS")
        if a.apply:
            for p,s in zip(paths,after): (root/p).write_text(s,encoding="utf-8")
            print("PATCHED ACCESSOR DEBUG APP ONLY; NO DEVICE OR FLASH")
        else: print("READ-ONLY; nothing written")
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:
        print("E11 NATIVE WIEGAND REFUSED: "+str(exc),file=sys.stderr);raise SystemExit(1)

if __name__=="__main__": main()
