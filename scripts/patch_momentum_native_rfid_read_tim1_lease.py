#!/usr/bin/env python3
"""E11 pinned native RFID READ TIM1 owner stage (source only, NO FLASH).

Independent RFID field/capture/emulation modes remain unmodified;
never claim whole RFID firmware-global safety from this stage.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
H="targets/f7/furi_hal/furi_hal_resources.h"
R="targets/f7/furi_hal/furi_hal_resources.c"
RFID="targets/f7/furi_hal/furi_hal_rfid.c"
RFID_H="targets/f7/furi_hal/furi_hal_rfid.h"
API="targets/f7/api_symbols.csv"
MARK="/* E11 native RFID read TIM1 owner. */"
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
    "targets/furi_hal_include/furi_hal_infrared.h",
    "lib/infrared/worker/infrared_worker.c",
    "lib/infrared/worker/infrared_worker.h",
}

def once(s:str,old:str,new:str)->str:
    if s.count(old)!=1:
        raise ValueError("Unexpected pinned RFID source anchor "+repr(old[:95]))
    return s.replace(old,new,1)

def patch(h:str,r:str,source:str,header:str,api:str):
    if MARK in source or "FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1" in h:
        raise ValueError("Native RFID already patched")
    h=once(h,
        "#define FURI_HAL_LEASE_NATIVE_IR_DETECT_PA7 (FuriHalLeasePa7)\n",
        "#define FURI_HAL_LEASE_NATIVE_IR_DETECT_PA7 (FuriHalLeasePa7)\n"
        "/* RFID read carrier uses TIM1 (native internal output, not PA7). */\n"
        "#define FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1 (FuriHalLeaseTim1)\n")
    r=once(r,
        "           mask == FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7 ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_IR_TX_EXT_PA7 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1 ||\n")
    source=once(source,
        "void furi_hal_rfid_tim_read_start(float freq, float duty_cycle) {",
        """/* E11 native RFID read TIM1 owner. */
static uint32_t e11_rfid_read_handle;
static bool e11_rfid_read_fault;

static bool e11_rfid_read_ready(void) {
    if(!e11_rfid_read_handle || e11_rfid_read_fault) return false;
    if(!furi_hal_bus_is_enabled(FURI_HAL_RFID_READ_TIMER_BUS)) {
        e11_rfid_read_fault=true;
        return false;
    }
    return true;
}

bool furi_hal_rfid_tim_read_try_start(float freq, float duty_cycle) {
    if(e11_rfid_read_handle || e11_rfid_read_fault) return false;
    const uint32_t lease =
        furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1);
    if(!lease) return false;
    /* An old noncooperating iButton, NFC, IR or native timer user. */
    if(furi_hal_bus_is_enabled(FURI_HAL_RFID_READ_TIMER_BUS)) {
        if(!furi_hal_resource_lease_release(
               lease,FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1)) {
            e11_rfid_read_handle=lease;
            e11_rfid_read_fault=true;
        }
        return false;
    }
    e11_rfid_read_handle=lease;""")
    source=once(source,
        """    furi_hal_rfid_tim_read_continue();
}

void furi_hal_rfid_tim_read_continue(void) {
    LL_TIM_EnableAllOutputs""",
        """    furi_hal_rfid_tim_read_continue();
    return true;
}

/* Original void API retained for existing native clients. */
void furi_hal_rfid_tim_read_start(float freq, float duty_cycle) {
    (void)furi_hal_rfid_tim_read_try_start(freq,duty_cycle);
}

void furi_hal_rfid_tim_read_continue(void) {
    if(!e11_rfid_read_ready()) return;
    LL_TIM_EnableAllOutputs""")
    source=once(source,
        """void furi_hal_rfid_tim_read_pause(void) {
    LL_TIM_DisableAllOutputs""",
        """void furi_hal_rfid_tim_read_pause(void) {
    if(!e11_rfid_read_ready()) return;
    LL_TIM_DisableAllOutputs""")
    source=once(source,
        """void furi_hal_rfid_tim_read_stop(void) {
    furi_hal_bus_disable(FURI_HAL_RFID_READ_TIMER_BUS);
}""",
        """void furi_hal_rfid_tim_read_stop(void) {
    /* STOP after denied START must not disable foreign TIM1. */
    if(!e11_rfid_read_ready()) return;
    furi_hal_bus_disable(FURI_HAL_RFID_READ_TIMER_BUS);
    const uint32_t owner=e11_rfid_read_handle;
    if(furi_hal_resource_lease_release(
           owner,FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1)) {
        e11_rfid_read_handle=0U;
    } else {
        e11_rfid_read_fault=true; /* sticky nonreusable owner */
    }
}""")
    source=once(source,
        """void furi_hal_rfid_set_read_period(uint32_t period) {
    LL_TIM_SetAutoReload""",
        """void furi_hal_rfid_set_read_period(uint32_t period) {
    if(!e11_rfid_read_ready()) return;
    LL_TIM_SetAutoReload""")
    source=once(source,
        """void furi_hal_rfid_set_read_pulse(uint32_t pulse) {
#if FURI_HAL_RFID_READ_TIMER_CHANNEL == LL_TIM_CHANNEL_CH1N""",
        """void furi_hal_rfid_set_read_pulse(uint32_t pulse) {
    if(!e11_rfid_read_ready()) return;
#if FURI_HAL_RFID_READ_TIMER_CHANNEL == LL_TIM_CHANNEL_CH1N""")
    header=once(header,
        "void furi_hal_rfid_tim_read_start(float freq, float duty_cycle);",
        "void furi_hal_rfid_tim_read_start(float freq, float duty_cycle);\n"
        "/* E11: returns false on cooperative or legacy native TIM1 BUSY. */\n"
        "bool furi_hal_rfid_tim_read_try_start(float freq,float duty_cycle);")
    api=once(api,'Function,+,furi_hal_rfid_tim_read_start,void,"float, float"\n',
        'Function,+,furi_hal_rfid_tim_read_start,void,"float, float"\n'
        'Function,+,furi_hal_rfid_tim_read_try_start,_Bool,"float, float"\n')
    return h,r,source,header,api

def main()->int:
    a=argparse.ArgumentParser()
    a.add_argument("firmware_root",type=Path)
    a.add_argument("--apply",action="store_true")
    args=a.parse_args()
    root=args.firmware_root.resolve()
    try:
        sha=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if sha!=PIN: raise ValueError("Not pinned Momentum source")
        seen=set()
        for ln in subprocess.check_output(["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(ln)<4 or ln[:2]=="??" or "->" in ln:
                raise ValueError("Unknown untracked/renamed native source")
            seen.add(ln[3:])
        if seen!=EXPECTED:
            raise ValueError("Unreviewed prior native patches: "+repr(sorted(seen^EXPECTED)))
        paths=(H,R,RFID,RFID_H,API)
        old=[(root/p).read_text(encoding="utf-8") for p in paths]
        new=patch(*old)
        print("E11 RFID TIM1 READ MODE EXACT SOURCE PREFLIGHT PASS")
        if args.apply:
            for p,c in zip(paths,new):
                (root/p).write_text(c,encoding="utf-8")
            print("RFID READ SOURCE PATCH ONLY, NO DEVICE/FLASH")
        else:
            print("READ ONLY — no native firmware changed")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 RFID READ SOURCE REFUSED: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
