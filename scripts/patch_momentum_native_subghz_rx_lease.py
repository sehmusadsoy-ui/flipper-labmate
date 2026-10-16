#!/usr/bin/env python3
"""Pinned E11 native SubGHz RX TIM2 cooperative owner, source-only.

Preserves legacy void API. This stage supports mirror OFF or verified
external PA7/PB3 mirror with atomic masks; remaining pin choices fail
closed and are explicitly OPEN, never silently unprotected.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_rfid_field_owner import EXPECTED as FIELD_DIRTY

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
H="targets/f7/furi_hal/furi_hal_resources.h"
R="targets/f7/furi_hal/furi_hal_resources.c"
S="targets/f7/furi_hal/furi_hal_subghz.c"
PUB="targets/f7/furi_hal/furi_hal_subghz.h"
API="targets/f7/api_symbols.csv"
MARK="/* E11 native SubGHz RX TIM2 cooperative owner. */"
EXPECTED=FIELD_DIRTY

def once(s,old,new):
    if s.count(old)!=1:
        raise ValueError("Pinned SubGHz RX source anchor missing/ambiguous "+repr(old[:130]))
    return s.replace(old,new,1)

def patch(h,r,s,pub,api):
    if MARK in s or "FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_TIM2" in h:
        raise ValueError("Native SubGHz RX stage already present")
    h=once(h,
        "#define FURI_HAL_LEASE_NATIVE_RFID_FIELD (FuriHalLeaseTim1|FuriHalLeaseTim2|FuriHalLeaseDma2Ch1|FuriHalLeaseDma2Ch2)\n",
        "#define FURI_HAL_LEASE_NATIVE_RFID_FIELD (FuriHalLeaseTim1|FuriHalLeaseTim2|FuriHalLeaseDma2Ch1|FuriHalLeaseDma2Ch2)\n"
        "/* CC1101 G0 = internal PA1, not external PB3. TIM2 shared. */\n"
        "#define FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_TIM2 (FuriHalLeaseTim2)\n"
        "#define FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PA7 (FuriHalLeaseTim2|FuriHalLeasePa7)\n"
        "#define FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PB3 (FuriHalLeaseTim2|FuriHalLeasePb3)\n")
    r=once(r,
        "           mask == FURI_HAL_LEASE_NATIVE_RFID_FIELD ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_RFID_FIELD ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_TIM2 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PA7 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PB3 ||\n")
    s=once(s,
        'void furi_hal_subghz_set_async_mirror_pin(const GpioPin* pin) {\n'
        '    furi_hal_subghz.async_mirror_pin = pin;\n}',
        'void furi_hal_subghz_set_async_mirror_pin(const GpioPin* pin) {\n'
        '    /* Do not switch debug GPIO identity during an owned RX session. */\n'
        '    if(e11_subghz_rx_handle || e11_subghz_rx_fault) return;\n'
        '    furi_hal_subghz.async_mirror_pin = pin;\n}')
    # Define handle *before* setter. Cannot permit duplicate symbol after this stage.
    s=once(s,
        '#define TAG "FuriHalSubGhz"\n',
        '''#define TAG "FuriHalSubGhz"

/* E11 native SubGHz RX TIM2 cooperative owner. */
static uint32_t e11_subghz_rx_handle;
static uint32_t e11_subghz_rx_mask;
static bool e11_subghz_rx_fault;

static bool e11_subghz_rx_ready(void) {
    if(!e11_subghz_rx_handle || e11_subghz_rx_fault) return false;
    if(!furi_hal_bus_is_enabled(FuriHalBusTIM2)) {
        e11_subghz_rx_fault=true;
        return false;
    }
    return true;
}

/* Internal CC1101 G0 uses PA1. An optional *external* debug mirror
 * needs a separate GPIO alias claim. Other mirror pins are unsupported
 * here and must return BUSY, never run without a pin lease.
 */
static uint32_t e11_subghz_rx_mask_for_mirror(const GpioPin* mirror) {
    if(!mirror) return FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_TIM2;
    if(mirror==&gpio_ext_pa7) return FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PA7;
    if(mirror==&gpio_ext_pb3) return FURI_HAL_LEASE_NATIVE_SUBGHZ_RX_MIRROR_PB3;
    return 0U;
}
''')
    s=once(s,
        'static void furi_hal_subghz_capture_ISR(void* context) {\n    UNUSED(context);\n',
        'static void furi_hal_subghz_capture_ISR(void* context) {\n'
        '    UNUSED(context);\n'
        '    /* A denied START may not read or clear any foreign TIM2 flags. */\n'
        '    if(!e11_subghz_rx_ready()) return;\n')
    s=once(s,
        '''void furi_hal_subghz_start_async_rx(FuriHalSubGhzCaptureCallback callback, void* context) {
    furi_check(furi_hal_subghz.state == SubGhzStateIdle);
    furi_check(callback);

    furi_hal_subghz.state = SubGhzStateAsyncRx;''',
        '''bool furi_hal_subghz_async_rx_try_start(FuriHalSubGhzCaptureCallback callback, void* context) {
    if(!callback || furi_hal_subghz.state != SubGhzStateIdle ||
       e11_subghz_rx_handle || e11_subghz_rx_fault) return false;
    const uint32_t mask=e11_subghz_rx_mask_for_mirror(furi_hal_subghz.async_mirror_pin);
    if(!mask) {
        FURI_LOG_W(TAG, "SubGHz RX debug mirror GPIO not yet lease-managed");
        return false;
    }
    const uint32_t lease=furi_hal_resource_lease_try_acquire(mask);
    if(!lease) return false;
    /* Legacy/direct TIM2 users can exist outside the cooperative table.
     * Refuse before callback, radio, debug pin, IRQ or timer writes.
     */
    if(furi_hal_bus_is_enabled(FuriHalBusTIM2)) {
        if(!furi_hal_resource_lease_release(lease,mask)) {
            e11_subghz_rx_handle=lease;
            e11_subghz_rx_mask=mask;
            e11_subghz_rx_fault=true;
        }
        return false;
    }
    e11_subghz_rx_handle=lease;
    e11_subghz_rx_mask=mask;
    furi_hal_subghz.state = SubGhzStateAsyncRx;''')
    s=once(s,
        '''    furi_hal_subghz_capture_delta_duration = 0;
}

void furi_hal_subghz_stop_async_rx(void) {
    furi_check(furi_hal_subghz.state == SubGhzStateAsyncRx);
    furi_hal_subghz.state = SubGhzStateIdle;''',
        '''    furi_hal_subghz_capture_delta_duration = 0;
    return true;
}

/* ABI compatibility for existing published/native void clients.
 * Cooperative application/service clients must use the bool API.
 */
void furi_hal_subghz_start_async_rx(FuriHalSubGhzCaptureCallback callback, void* context) {
    (void)furi_hal_subghz_async_rx_try_start(callback,context);
}

void furi_hal_subghz_stop_async_rx(void) {
    /* STOP after BUSY or unexpectedly removed TIM2 cannot mutate another owner. */
    if(!e11_subghz_rx_ready()) return;
    if(furi_hal_subghz.state != SubGhzStateAsyncRx) {
        e11_subghz_rx_fault=true;
        return;
    }
    furi_hal_subghz.state = SubGhzStateIdle;''')
    s=once(s,
        '''    furi_hal_gpio_init(&gpio_cc1101_g0, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
}

typedef enum {
    FuriHalSubGhzAsyncTxMiddlewareStateIdle,''',
        '''    furi_hal_gpio_init(&gpio_cc1101_g0, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
    furi_hal_subghz_capture_callback=NULL;
    furi_hal_subghz_capture_callback_context=NULL;
    const uint32_t owner=e11_subghz_rx_handle;
    if(furi_hal_resource_lease_release(owner,e11_subghz_rx_mask)) {
        e11_subghz_rx_handle=0U;
        e11_subghz_rx_mask=0U;
    } else {
        e11_subghz_rx_fault=true; /* Sticky failed release. */
    }
}

typedef enum {
    FuriHalSubGhzAsyncTxMiddlewareStateIdle,''')
    pub=once(pub,
        'void furi_hal_subghz_start_async_rx(FuriHalSubGhzCaptureCallback callback, void* context);',
        'void furi_hal_subghz_start_async_rx(FuriHalSubGhzCaptureCallback callback, void* context);\n'
        '/* E11: false if TIM2 or supported debug mirror GPIO is BUSY. */\n'
        'bool furi_hal_subghz_async_rx_try_start(FuriHalSubGhzCaptureCallback callback, void* context);')
    api=once(api,
        'Function,+,furi_hal_subghz_start_async_rx,void,"FuriHalSubGhzCaptureCallback, void*"\n',
        'Function,+,furi_hal_subghz_start_async_rx,void,"FuriHalSubGhzCaptureCallback, void*"\n'
        'Function,+,furi_hal_subghz_async_rx_try_start,_Bool,"FuriHalSubGhzCaptureCallback, void*"\n')
    return h,r,s,pub,api

def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("firmware_root",type=Path)
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    root=args.firmware_root.resolve()
    try:
        head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if head!=PIN: raise ValueError("Unexpected Momentum revision")
        dirty=set()
        for line in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Untracked/renamed native source forbidden")
            dirty.add(line[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unexpected changed source "+repr(sorted(dirty^EXPECTED)))
        paths=(H,R,S,PUB,API)
        old=[(root/p).read_text(encoding="utf-8") for p in paths]
        updated=patch(*old)
        print("E11 NATIVE SUBGHZ RX PINNED SOURCE PREFLIGHT PASS")
        if args.apply:
            for p,s in zip(paths,updated):
                (root/p).write_text(s,encoding="utf-8")
            print("PATCHED RX HAL ONLY; RX UPPER CALLERS / TX OPEN; NO FLASH")
        else:
            print("READ ONLY, NO FILES WRITTEN")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:
        print("E11 SUBGHZ RX SOURCE REFUSED: "+str(exc),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
