#!/usr/bin/env python3
"""Route pinned native SubGHz RX BUSY to in-firmware app without plugin ABI change.

The external SubGhzDeviceInterconnect start_async_rx void callback is
unchanged. Existing third-party plugins use the original fallback.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_subghz_rx_lease import EXPECTED as RX_PRE, S as SUB, PUB

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
I="lib/subghz/devices/cc1101_int/cc1101_int_interconnect.c"
IH="lib/subghz/devices/cc1101_int/cc1101_int_interconnect.h"
D="lib/subghz/devices/devices.c"
DH="lib/subghz/devices/devices.h"
APP="applications/main/subghz/helpers/subghz_txrx.c"
API="targets/f7/api_symbols.csv"
EXPECTED=RX_PRE | {SUB,PUB}
MARK="/* E11 cooperative SubGHz RX BUSY path; plugin interconnect ABI unchanged. */"

def once(s,old,new):
    if s.count(old)!=1:
        raise ValueError("Pinned SubGHz RX caller source anchor missing/ambiguous "+repr(old[:125]))
    return s.replace(old,new,1)

def patch(i,ih,d,dh,app,api):
    if MARK in d:
        raise ValueError("SubGHz RX callers already patched")
    i=once(i,
        """static void subghz_device_cc1101_int_interconnect_start_async_rx(void* callback, void* context) {
    furi_hal_subghz_start_async_rx((FuriHalSubGhzCaptureCallback)callback, context);
}""",
        """/* Existing plugin ABI remains void; new in-firmware client uses
 * the dedicated boolean native RX path to observe TIM2/mirror BUSY.
 */
bool subghz_device_cc1101_int_interconnect_try_start_async_rx(
    void* callback, void* context) {
    return furi_hal_subghz_async_rx_try_start(
        (FuriHalSubGhzCaptureCallback)callback, context);
}

static void subghz_device_cc1101_int_interconnect_start_async_rx(void* callback, void* context) {
    (void)subghz_device_cc1101_int_interconnect_try_start_async_rx(callback, context);
}""")
    ih=once(ih,
        "extern const SubGhzDevice subghz_device_cc1101_int;",
        "extern const SubGhzDevice subghz_device_cc1101_int;\n"
        "/* New firmware-local bool start; do not change plugin function pointers. */\n"
        "bool subghz_device_cc1101_int_interconnect_try_start_async_rx(void* callback, void* context);")
    d=once(d,
        '#include "registry.h"\n',
        '#include "registry.h"\n#include "cc1101_int/cc1101_int_interconnect.h"\n')
    d=once(d,
        """void subghz_devices_start_async_rx(const SubGhzDevice* device, void* callback, void* context) {
    furi_check(device);
    if(device->interconnect->start_async_rx) {
        device->interconnect->start_async_rx(callback, context);
    }
}""",
        """/* E11 cooperative SubGHz RX BUSY path; plugin interconnect ABI unchanged. */
bool subghz_devices_try_start_async_rx(
    const SubGhzDevice* device, void* callback, void* context) {
    furi_check(device);
    if(!device->interconnect->start_async_rx) return false;
    if(device == &subghz_device_cc1101_int) {
        return subghz_device_cc1101_int_interconnect_try_start_async_rx(callback, context);
    }
    /* External radio plugins still implement the old void function
     * pointer, and cannot communicate a new BUSY result. Do not
     * reinterpret plugin binary layouts or bump plugin API version.
     */
    device->interconnect->start_async_rx(callback, context);
    return true;
}

void subghz_devices_start_async_rx(const SubGhzDevice* device, void* callback, void* context) {
    (void)subghz_devices_try_start_async_rx(device, callback, context);
}""")
    dh=once(dh,
        "void subghz_devices_start_async_rx(const SubGhzDevice* device, void* callback, void* context);",
        "void subghz_devices_start_async_rx(const SubGhzDevice* device, void* callback, void* context);\n"
        "/* E11: truthful bool for built-in CC1101, legacy plugin ABI unchanged. */\n"
        "bool subghz_devices_try_start_async_rx(const SubGhzDevice* device, void* callback, void* context);")
    app=once(app,
        """    subghz_devices_flush_rx(instance->radio_device);
    subghz_txrx_speaker_on(instance);

    subghz_devices_start_async_rx(
        instance->radio_device, subghz_worker_rx_callback, instance->worker);
    subghz_worker_start(instance->worker);""",
        """    subghz_devices_flush_rx(instance->radio_device);
    /* A denied native timer is NOT a started receiver or worker. */
    if(!subghz_devices_try_start_async_rx(
           instance->radio_device, subghz_worker_rx_callback, instance->worker)) {
        FURI_LOG_W(TAG, "SubGHz RX TIM2/mirror resource BUSY");
        instance->txrx_state=SubGhzTxRxStateIDLE;
        return 0U;
    }
    subghz_txrx_speaker_on(instance);
    subghz_worker_start(instance->worker);""")
    api=once(api,
        'Function,+,subghz_devices_start_async_rx,void,"const SubGhzDevice*, void*, void*"\n',
        'Function,+,subghz_devices_start_async_rx,void,"const SubGhzDevice*, void*, void*"\n'
        'Function,+,subghz_devices_try_start_async_rx,_Bool,"const SubGhzDevice*, void*, void*"\n')
    return i,ih,d,dh,app,api

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    args=p.parse_args()
    root=args.firmware_root.resolve()
    try:
        head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if head!=PIN: raise ValueError("Unexpected pinned Momentum SHA")
        dirty=set()
        for line in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Untracked or renamed Momentum source")
            dirty.add(line[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unreviewed native source "+repr(sorted(dirty^EXPECTED)))
        hal=(root/SUB).read_text(encoding="utf-8")
        if "/* E11 native SubGHz RX TIM2 cooperative owner. */" not in hal:
            raise ValueError("Missing reviewed native SubGHz RX HAL stage")
        paths=(I,IH,D,DH,APP,API)
        orig=[(root/p).read_text(encoding="utf-8") for p in paths]
        new=patch(*orig)
        print("E11 NATIVE SUBGHZ RX CALLER SOURCE PREFLIGHT PASS")
        if args.apply:
            for p,txt in zip(paths,new):
                (root/p).write_text(txt,encoding="utf-8")
            print("SOURCE PATCHED; NO FLASH; EXTERNAL PLUGIN ABI UNCHANGED")
        else:
            print("READ ONLY; NO FILES WRITTEN")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:
        print("E11 SUBGHZ RX CALLER REFUSED: "+str(exc),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
