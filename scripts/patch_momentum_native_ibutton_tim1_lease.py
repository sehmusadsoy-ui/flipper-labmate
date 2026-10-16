#!/usr/bin/env python3
"""E11 native iButton TIM1: pinned Momentum source-only lease migration.

No flash, no device. Only TIM1 and its native timer ISR are guarded.
iButton GPIO pin functions are OUTSIDE this lease's scope. The existing
void-return start API cannot report BUSY to higher-level callers.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

PINNED = "d3f89dfe2ef6b01839201598e9be1590cba80322"
HEADER = "targets/f7/furi_hal/furi_hal_resources.h"
RESOURCE = "targets/f7/furi_hal/furi_hal_resources.c"
IBUTTON = "targets/f7/furi_hal/furi_hal_ibutton.c"
EXPECTED_DIRTY = {
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
}
MARKER = "/* E11 native iButton TIM1 cooperative lease (timer only)."

def replace_once(s: str, needle: str, replacement: str) -> str:
    if s.count(needle) != 1:
        raise ValueError("Missing or ambiguous iButton patch signature: " + repr(needle[:95]))
    return s.replace(needle, replacement, 1)

def patch(h: str, r: str, b: str) -> tuple[str, str, str]:
    if MARKER in b or "FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1" in h:
        raise ValueError("Already patched native iButton")
    h = replace_once(
        h,
        "#define FURI_HAL_LEASE_DIGITAL_PA7 (FURI_HAL_LEASE_DIGITAL_CORE | FuriHalLeasePa7)\n",
        "#define FURI_HAL_LEASE_DIGITAL_PA7 (FURI_HAL_LEASE_DIGITAL_CORE | FuriHalLeasePa7)\n"
        "/* iButton operates TIM1 without touching the PA7 generator pin. */\n"
        "#define FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1 (FuriHalLeaseTim1)\n")
    r = replace_once(
        r, "           mask == FURI_HAL_LEASE_DIGITAL_PA7 ||\n",
        "           mask == FURI_HAL_LEASE_DIGITAL_PA7 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1 ||\n")
    b = replace_once(b,
        "    void* context;\n} FuriHalIbutton;",
        "    void* context;\n    uint32_t e11_lease_handle;\n    bool e11_lease_fault;\n} FuriHalIbutton;")
    b = replace_once(b,
        "    furi_hal_ibutton->state = FuriHalIbuttonStateIdle;\n\n    FURI_LOG_I",
        "    furi_hal_ibutton->state = FuriHalIbuttonStateIdle;\n"
        "    furi_hal_ibutton->e11_lease_handle = 0U;\n"
        "    furi_hal_ibutton->e11_lease_fault = false;\n\n    FURI_LOG_I")
    b = replace_once(b,
        "static void furi_hal_ibutton_emulate_isr(void* context) {\n    UNUSED(context);\n",
        "static void furi_hal_ibutton_emulate_isr(void* context) {\n    UNUSED(context);\n"
        "    if(!furi_hal_ibutton || !furi_hal_ibutton->e11_lease_handle ||\n"
        "       furi_hal_ibutton->e11_lease_fault ||\n"
        "       furi_hal_ibutton->state != FuriHalIbuttonStateRunning) return;\n")
    b = replace_once(b,
        "    furi_check(furi_hal_ibutton->state == FuriHalIbuttonStateIdle);\n\n"
        "    furi_hal_ibutton->state = FuriHalIbuttonStateRunning;",
        """    furi_check(furi_hal_ibutton->state == FuriHalIbuttonStateIdle);
    /* E11 native iButton TIM1 cooperative lease (timer only).
     * Denial may not register ISR or mutate timer/callback state.
     */
    if(furi_hal_ibutton->e11_lease_fault ||
       furi_hal_ibutton->e11_lease_handle) return;
    const uint32_t lease =
        furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1);
    if(!lease) return; /* BUSY: native public start is void */
    if(furi_hal_bus_is_enabled(FURI_HAL_IBUTTON_TIMER_BUS)) {
        if(!furi_hal_resource_lease_release(
               lease, FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1)) {
            furi_hal_ibutton->e11_lease_handle = lease;
            furi_hal_ibutton->e11_lease_fault = true;
        }
        return; /* A legacy TIM1 user is not a new iButton owner. */
    }
    furi_hal_ibutton->e11_lease_handle = lease;
    furi_hal_ibutton->state = FuriHalIbuttonStateRunning;""")
    b = replace_once(b,
        "void furi_hal_ibutton_emulate_set_next(uint32_t period) {\n    LL_TIM_SetAutoReload",
        """void furi_hal_ibutton_emulate_set_next(uint32_t period) {
    if(!furi_hal_ibutton ||
       furi_hal_ibutton->state != FuriHalIbuttonStateRunning ||
       !furi_hal_ibutton->e11_lease_handle ||
       furi_hal_ibutton->e11_lease_fault) return;
    if(!furi_hal_bus_is_enabled(FURI_HAL_IBUTTON_TIMER_BUS)) {
        furi_hal_ibutton->e11_lease_fault = true;
        return;
    }
    LL_TIM_SetAutoReload""")
    b = replace_once(b,
        """    if(furi_hal_ibutton->state == FuriHalIbuttonStateRunning) {
        furi_hal_ibutton->state = FuriHalIbuttonStateIdle;
        LL_TIM_DisableCounter""",
        """    if(furi_hal_ibutton->state == FuriHalIbuttonStateRunning) {
        if(!furi_hal_ibutton->e11_lease_handle ||
           furi_hal_ibutton->e11_lease_fault) return;
        if(!furi_hal_bus_is_enabled(FURI_HAL_IBUTTON_TIMER_BUS)) {
            /* Unexpected foreign clock teardown; do not touch IRQ/timer.
             * Retain reservation and permanently deny this session.
             */
            furi_hal_ibutton->e11_lease_fault = true;
            return;
        }
        furi_hal_ibutton->state = FuriHalIbuttonStateIdle;
        LL_TIM_DisableCounter""")
    b = replace_once(b,
        """        furi_hal_ibutton->callback = NULL;
        furi_hal_ibutton->context = NULL;
    }
}""",
        """        furi_hal_ibutton->callback = NULL;
        furi_hal_ibutton->context = NULL;
        if(furi_hal_resource_lease_release(
               furi_hal_ibutton->e11_lease_handle,
               FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1)) {
            furi_hal_ibutton->e11_lease_handle = 0U;
        } else {
            furi_hal_ibutton->e11_lease_fault = true;
        }
    }
}""")
    return h,r,b

def main() -> int:
    a=argparse.ArgumentParser()
    a.add_argument("firmware_root",type=Path)
    a.add_argument("--apply",action="store_true")
    args=a.parse_args()
    root=args.firmware_root.resolve()
    try:
        head=subprocess.check_output(
            ["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if head != PINNED: raise ValueError("Wrong pinned Momentum SHA")
        lines=subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines()
        dirty=set()
        for line in lines:
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Untracked/renamed native sources refused")
            dirty.add(line[3:])
        if dirty!=EXPECTED_DIRTY:
            raise ValueError("Unreviewed Momentum source changes "+repr(sorted(dirty)))
        h=(root/HEADER).read_text()
        r=(root/RESOURCE).read_text()
        b=(root/IBUTTON).read_text()
        if ("FURI_HAL_LEASE_DIGITAL_CORE" not in h or
            "/* LabMate E11 native DigitalSequence owner. */" not in
            (root/"lib/digital_signal/digital_sequence.c").read_text()):
            raise ValueError("Missing prior native DigitalSequence lease stage")
        nh,nr,nb=patch(h,r,b)
        print("E11 IBUTTON TIM1 EXACT SOURCE PATCH PASS; timer/ISR only")
        if args.apply:
            for p,c in ((HEADER,nh),(RESOURCE,nr),(IBUTTON,nb)):
                (root/p).write_text(c)
            print("E11 IBUTTON PATCH SOURCE ONLY; NO USB/SD/FLASH")
        else:
            print("READ ONLY; NO FIRMWARE FILES CHANGED")
        return 0
    except (OSError,subprocess.CalledProcessError,ValueError) as e:
        print("REFUSED native iButton TIM1: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
