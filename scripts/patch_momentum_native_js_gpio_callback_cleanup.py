#!/usr/bin/env python3
"""Stage native JS GPIO exact-owner callback teardown after pinned E11 IMU.

Prevents foreign EXTI disable/removal in mode transitions and module destroy.
Strict Momentum SHA and expected predecessor diff; never flashes hardware.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_imu_fifo_exti_lease import EXPECTED as IMU_PRE, DR, DH, IMU
from patch_momentum_native_js_gpio_lease import TARGET as JS

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
EXPECTED=IMU_PRE|{DR,DH,IMU}
MARK="/* E11 JS GPIO exact callback-and-semaphore owner cleanup. */"

def exactly(source: str,old: str,new: str)->str:
    if source.count(old)!=1:
        raise ValueError("Pinned JS GPIO teardown source mismatch "+repr(old[:110]))
    return source.replace(old,new,1)

def patch(src: str)->str:
    if MARK in src:
        raise ValueError("Already applied callback cleanup")
    if ("/* LabMate E11 native JS GPIO connector-owner contract. */" not in src or
        "furi_hal_gpio_try_add_int_callback(" not in src or
        "bool lease_fault;" not in src):
        raise ValueError("Missing native E11 JS GPIO predecessor")
    src=exactly(src,
        "/* LabMate E11 native JS GPIO connector-owner contract. */",
        "static void js_gpio_int_cb(void* arg);\n"
        "/* LabMate E11 native JS GPIO connector-owner contract. */")
    src=exactly(src,
        "static bool js_gpio_e11_claim(JsGpioPinInst* manager_data) {",
        """/* E11 JS GPIO exact callback-and-semaphore owner cleanup.
 * The mode transition and destructor must never use the old raw
 * remove/disable calls: both can disable a foreign EXTI2/4/7 owner.
 * A lost callback slot is a sticky fault. Keep the semaphore/lease
 * alive on refused destruction rather than risk interrupt use-after-free.
 */
static bool js_gpio_e11_try_remove_callback(JsGpioPinInst* data) {
    if(!data || data->lease_fault) return false;
    if(!data->had_interrupt) return true;
    if(!furi_hal_gpio_try_remove_int_callback(
           data->pin,js_gpio_int_cb,data->interrupt_semaphore)) {
        data->lease_fault=true;
        return false;
    }
    data->had_interrupt=false;
    return true;
}

static bool js_gpio_e11_claim(JsGpioPinInst* manager_data) {""")
    src=exactly(src,
        """    } else if(!is_interrupt && manager_data->had_interrupt) {
        furi_hal_gpio_disable_int_callback(manager_data->pin);
        furi_hal_gpio_remove_int_callback(manager_data->pin);
        manager_data->had_interrupt = false;
    }""",
        """    } else if(!is_interrupt && manager_data->had_interrupt) {
        if(!js_gpio_e11_try_remove_callback(manager_data))
            JS_ERROR_AND_RETURN(mjs,MJS_BAD_ARGS_ERROR,"GPIO callback ownership lost");
    }""")
    src=exactly(src,
        """            if(manager_data->had_interrupt) {
                furi_hal_gpio_disable_int_callback(manager_data->pin);
                furi_hal_gpio_remove_int_callback(manager_data->pin);
            }
            if(manager_data->pwm_owned) {""",
        """            if(!js_gpio_e11_try_remove_callback(manager_data)) {
                /* Sticky exceptional failure: never release the physical
                 * EXTI/pin claim or free a possibly live IRQ semaphore.
                 * Prefer a bounded resource leak over a foreign removal
                 * or use-after-free during teardown.
                 */
                FURI_LOG_E("JSGpio","GPIO callback owner lost on destroy");
                continue;
            }
            if(manager_data->pwm_owned) {""")
    if "furi_hal_gpio_remove_int_callback(manager_data->pin);" in src:
        raise ValueError("Unmigrated raw callback removal")
    if "furi_hal_gpio_disable_int_callback(manager_data->pin);" in src:
        raise ValueError("Unmigrated raw interrupt disable")
    return src

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("firmware_root",type=Path)
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args()
    root=args.firmware_root.resolve()
    try:
        head=subprocess.check_output(
            ["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if head!=PIN:
            raise ValueError("Unpinned native Momentum revision")
        dirty=set()
        for line in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Untracked or renamed firmware file")
            dirty.add(line[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unexpected native modified paths "+repr(sorted(dirty^EXPECTED)))
        gpio=(root/"targets/f7/furi_hal/furi_hal_gpio.c").read_text()
        if "bool furi_hal_gpio_try_remove_int_callback(" not in gpio:
            raise ValueError("Missing E11 native exact callback removal")
        dest=root/JS
        next_src=patch(dest.read_text(encoding="utf-8"))
        print("E11 JS GPIO EXACT CALLBACK CLEANUP SOURCE PREFLIGHT PASS")
        if args.apply:
            dest.write_text(next_src,encoding="utf-8")
            print("ORIGINAL JS SOURCE ONLY; NO FLASH/USB/SD")
        else:
            print("READ-ONLY; NO MODIFICATIONS")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 JS GPIO CALLBACK REFUSED: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
