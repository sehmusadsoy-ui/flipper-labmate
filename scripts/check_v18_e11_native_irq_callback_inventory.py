#!/usr/bin/env python3
"""E11 fail-closed pinned Momentum native GPIO callback inventory gate.

All raw add/remove callsites must either be the implementation itself or
the boot-time **system button** service. Cooperative clients must use
try_add/try_remove before changing pin modes. Detect new raw callsites
without claiming to globally intercept every GPIO/EXTI register write.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import subprocess
import sys

PINNED="d3f89dfe2ef6b01839201598e9be1590cba80322"
HAL="targets/f7/furi_hal/furi_hal_gpio.c"
INPUT="applications/services/input/input.c"
MIGRATED={
    "targets/f7/furi_hal/furi_hal_nfc_irq.c",
    "lib/one_wire/one_wire_slave.c",
    "applications/system/js_app/modules/js_gpio.c",
    "applications/system/js_app/modules/js_vgm/ICM42688P/ICM42688P.c",
    "applications/debug/accessor/helpers/wiegand.cpp",
    "applications/drivers/subghz/cc1101_ext/cc1101_ext.c",
    "targets/f7/furi_hal/furi_hal_serial_control.c",
}
NEEDED={
    "targets/f7/furi_hal/furi_hal_nfc_irq.c":"furi_hal_gpio_try_remove_int_callback(",
    "lib/one_wire/one_wire_slave.c":"furi_hal_gpio_try_remove_int_callback(",
    "applications/system/js_app/modules/js_gpio.c":"js_gpio_e11_try_remove_callback(",
    "applications/system/js_app/modules/js_vgm/ICM42688P/ICM42688P.c":"furi_hal_gpio_try_remove_int_callback(",
    "applications/debug/accessor/helpers/wiegand.cpp":"furi_hal_gpio_try_remove_int_callback(",
    "applications/drivers/subghz/cc1101_ext/cc1101_ext.c":"furi_hal_gpio_try_remove_int_callback(",
    "targets/f7/furi_hal/furi_hal_serial_control.c":"furi_hal_gpio_try_remove_int_callback(",
}
RE=re.compile(r"furi_hal_gpio_(?:add|remove)_int_callback\s*\(")

def scan(root:Path)->list[tuple[str,int,str]]:
    output=subprocess.check_output(
        ["git","-C",str(root),"grep","-n","-E",
         r"furi_hal_gpio_(add|remove)_int_callback[[:space:]]*\(",
         "--","*.c","*.cpp"],text=True)
    found=[]
    for line in output.splitlines():
        m=re.match(r"([^:]+):(\d+):(.*)",line)
        if not m: raise ValueError("Unexpected git grep result "+repr(line))
        if RE.search(m.group(3)):
            found.append((m.group(1),int(m.group(2)),m.group(3).strip()))
    return found

def check(root:Path):
    sha=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if sha!=PINNED: raise ValueError("Not exact pinned Momentum")
    changed=set(subprocess.check_output(
        ["git","-C",str(root),"diff","--name-only","HEAD"],text=True).splitlines())
    if INPUT in changed: raise ValueError("System input button service changed: unsafe global EXTI policy")
    native=(root/INPUT).read_text(encoding="utf-8")
    if "furi_hal_gpio_add_int_callback(input_pins[i].gpio, input_isr, thread_id);" not in native:
        raise ValueError("System-input button listener no longer preserved")
    for path,required in NEEDED.items():
        source=(root/path).read_text(encoding="utf-8")
        if required not in source: raise ValueError("Missing safe EXTI callback client "+path)
    results=scan(root)
    active={p for p,_,_ in results}
    unexpected=[x for x in results if x[0] not in {HAL,INPUT}]
    if unexpected:
        raise ValueError("Native raw GPIO callback bypasses: "+repr(unexpected[:20]))
    if HAL not in active or INPUT not in active:
        raise ValueError("Expected HAL primitive or reserved system input missing")
    print("E11 pinned GPIO callback registration/removal inventory PASS")
    print("Only HAL primitive and reserved Momentum input service use legacy add/remove.")
    print("All seven surveyed native clients use their reviewed guarded callback CAS.")
    print("Boundary: direct register writes / custom IRQ/EXTI aliases still need reviews.")
    return 0

def main():
    ap=argparse.ArgumentParser();ap.add_argument("firmware_root",type=Path)
    args=ap.parse_args()
    try: return check(args.firmware_root.resolve())
    except (OSError,subprocess.CalledProcessError,ValueError) as e:
        print("E11 callback inventory FAIL CLOSED: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__": raise SystemExit(main())
