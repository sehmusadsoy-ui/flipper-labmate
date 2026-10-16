#!/usr/bin/env python3
"""Non-ABI-breaking RX BUSY result sidechannel for the matched external CC1101.

Legacy plugin v1 uses a void RX callback. A synchronous per-attempt report
lets the matching native CC1101 external driver return its actual bool
without changing SubGhzDeviceInterconnect layout. Unknown v1 radios
retain legacy behavior with explicit *unverified* diagnostics.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_js_gpio_callback_cleanup import EXPECTED as JS_PRE, JS
from patch_momentum_native_subghz_rx_busy_callers import D,DH,API
from patch_momentum_native_ext_cc1101_rx_lease import EXT

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
EXT_I="applications/drivers/subghz/cc1101_ext/cc1101_ext_interconnect.c"
EXPECTED=JS_PRE|{JS}
MARK="/* E11 matched radio plugin v1 RX status sidechannel; ABI unchanged."

def once(s,old,new):
    if s.count(old)!=1: raise ValueError("Pinned external radio status source anchor "+repr(old[:110]))
    return s.replace(old,new,1)

def patch(d,dh,ext_i,api):
    if MARK in d: raise ValueError("External status sidechannel already staged")
    d=once(d,
        '#include "registry.h"\n',
        '#include "registry.h"\n#include <string.h>\n')
    d=once(d,
        """/* E11 cooperative SubGHz RX BUSY path; plugin interconnect ABI unchanged. */
bool subghz_devices_try_start_async_rx(""",
        """/* E11 matched radio plugin v1 RX status sidechannel; ABI unchanged.
 * Plugin callback runs synchronously. Only the exact device pointer
 * owning the current transaction may report one result.
 * A missing result is UNKNOWN, never an invented bool success for the
 * matched official CC1101 external plugin.
 */
static const SubGhzDevice* e11_rx_start_pending;
static bool e11_rx_start_reported;
static bool e11_rx_start_result;

void subghz_devices_report_async_rx_start_result(
    const SubGhzDevice* device,bool started) {
    if(e11_rx_start_pending!=NULL &&
       e11_rx_start_pending==device &&
       !e11_rx_start_reported) {
        e11_rx_start_reported=true;
        e11_rx_start_result=started;
    }
}

/* E11 cooperative SubGHz RX BUSY path; plugin interconnect ABI unchanged. */
bool subghz_devices_try_start_async_rx(""")
    d=once(d,
        """    /* External radio plugins still implement the old void function
     * pointer, and cannot communicate a new BUSY result. Do not
     * reinterpret plugin binary layouts or bump plugin API version.
     */
    device->interconnect->start_async_rx(callback, context);
    return true;""",
        """    /* No struct or vtable changes: older third-party plugins
     * remain ABI-valid. The official matching external CC1101 driver
     * reports via the new optional firmware function. A copied/
     * outdated official plugin that does not report is FAIL CLOSED.
     * Other unknown v1 plugins retain the old statusless behavior,
     * explicitly logged as UNKNOWN rather than falsely certified.
     */
    if(e11_rx_start_pending) {
        FURI_LOG_W("SubGhzDevices","Nested external RX START refused");
        return false;
    }
    e11_rx_start_pending=device;
    e11_rx_start_reported=false;
    e11_rx_start_result=false;
    device->interconnect->start_async_rx(callback, context);
    const bool valid=e11_rx_start_reported;
    const bool accepted=e11_rx_start_result;
    e11_rx_start_pending=NULL;
    e11_rx_start_reported=false;
    e11_rx_start_result=false;
    if(valid) return accepted;
    if(device->name && strcmp(device->name,"cc1101_ext")==0) {
        FURI_LOG_W("SubGhzDevices","External CC1101 RX lacks E11 status; deny unknown start");
        return false;
    }
    FURI_LOG_W("SubGhzDevices","Legacy radio RX start unverified (plugin API v1)");
    return true;""")
    dh=once(dh,
        """bool subghz_devices_try_start_async_rx(const SubGhzDevice* device, void* callback, void* context);""",
        """bool subghz_devices_try_start_async_rx(const SubGhzDevice* device, void* callback, void* context);
/* Optional v1 plugin sidechannel: call synchronously from the RX callback.
 * Never extend the published SubGhzDeviceInterconnect ABI or cast vtables.
 */
void subghz_devices_report_async_rx_start_result(
    const SubGhzDevice* device,bool started);""")
    ext_i=once(ext_i,
        '#include "cc1101_ext.h"\n',
        '#include "cc1101_ext.h"\n#include <lib/subghz/devices/devices.h>\n')
    ext_i=once(ext_i,
        """static void subghz_device_cc1101_ext_interconnect_start_async_rx(void* callback, void* context) {
    subghz_device_cc1101_ext_start_async_rx(
        (SubGhzDeviceCC1101ExtCaptureCallback)callback, context);
}""",
        """extern const SubGhzDevice subghz_device_cc1101_ext;
static void subghz_device_cc1101_ext_interconnect_start_async_rx(void* callback, void* context) {
    /* Native E11 TIM17/PB2/EXTI2 owner supplies truthful BUSY.
     * The original external radio v1 ABI stays void; the matching
     * firmware consumes this optional synchronous result sidechannel.
     */
    const bool started=subghz_device_cc1101_ext_try_start_async_rx(
        (SubGhzDeviceCC1101ExtCaptureCallback)callback,context);
    subghz_devices_report_async_rx_start_result(&subghz_device_cc1101_ext,started);
}""")
    api=once(api,
        'Function,+,subghz_devices_try_start_async_rx,_Bool,"const SubGhzDevice*, void*, void*"\n',
        'Function,+,subghz_devices_try_start_async_rx,_Bool,"const SubGhzDevice*, void*, void*"\n'
        'Function,+,subghz_devices_report_async_rx_start_result,void,"const SubGhzDevice*, _Bool"\n')
    return d,dh,ext_i,api

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("firmware_root",type=Path)
    ap.add_argument("--apply",action="store_true")
    args=ap.parse_args();root=args.firmware_root.resolve()
    try:
        pinned=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if pinned!=PIN: raise ValueError("Unpinned Momentum SHA")
        changed=set()
        for line in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Renamed/untracked native firmware source")
            changed.add(line[3:])
        if changed!=EXPECTED:
            raise ValueError("Unexpected preceding source paths "+repr(sorted(changed^EXPECTED)))
        ext=(root/EXT).read_text(encoding="utf-8")
        if "bool subghz_device_cc1101_ext_try_start_async_rx(" not in ext:
            raise ValueError("Missing real cooperative CC1101 external RX bool predecessor")
        paths=(D,DH,EXT_I,API)
        prior=[(root/p).read_text(encoding="utf-8") for p in paths]
        result=patch(*prior)
        print("E11 EXTERNAL RADIO MATCHED PLUGIN v1 RX STATUS PREFLIGHT PASS")
        if args.apply:
            for p,txt in zip(paths,result):
                (root/p).write_text(txt,encoding="utf-8")
            print("Native firmware/plugin-source only, NO FIRMWARE FLASH")
        else: print("READ ONLY")
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 RADIO STATUS REFUSED: "+str(e),file=sys.stderr)
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
