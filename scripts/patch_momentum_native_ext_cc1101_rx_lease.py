#!/usr/bin/env python3
"""E11 external CC1101 RX: TIM17 + PB2 + shared EXTI2 atomic lease.

Pinned Momentum source only, existing void plugin interconnect ABI unchanged.
Conservatively refuse unsupported configurable G0 or debug mirror GPIO.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_serial_expansion_exti_lease import EXPECTED as SERIAL_PRE,H,R,SER,PUB,API

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
EXT="applications/drivers/subghz/cc1101_ext/cc1101_ext.c"
EXT_H="applications/drivers/subghz/cc1101_ext/cc1101_ext.h"
EXPECTED=SERIAL_PRE | {H,R,SER,PUB,API}
MARK="/* E11 external CC1101 RX TIM17+PB2+EXTI2 owner. */"

def one(s,old,new):
    if s.count(old)!=1:
        raise ValueError("Pinned external CC1101 source mismatch "+repr(old[:105]))
    return s.replace(old,new,1)

def patch(h,r,s,header):
    if MARK in s or "FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX" in h:
        raise ValueError("Already patched")
    h=one(h,
        "#define FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 (FuriHalLeaseLpuart1|FuriHalLeasePc0|FuriHalLeaseExti0)\n",
        "#define FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 (FuriHalLeaseLpuart1|FuriHalLeasePc0|FuriHalLeaseExti0)\n"
        "/* External CC1101 G0 is PB2; EXTI2 aliases internal NFC PA2. */\n"
        "#define FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX (FuriHalLeaseTim17|FuriHalLeasePb2|FuriHalLeaseExti2)\n")
    r=one(r,
        "           mask == FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX ||\n")
    s=one(s,
        '#define TAG "SubGhzDeviceCc1101Ext"\n',
        '''#define TAG "SubGhzDeviceCc1101Ext"

/* E11 external CC1101 RX TIM17+PB2+EXTI2 owner. */
static uint32_t e11_ext_rx_owner;
static bool e11_ext_rx_fault;

static bool e11_ext_rx_ready(void) {
    if(!e11_ext_rx_owner || e11_ext_rx_fault) return false;
    if(!furi_hal_bus_is_enabled(FuriHalBusTIM17)) {
        e11_ext_rx_fault=true;
        return false;
    }
    return true;
}
''')
    # Do not free live RX callback context / owner after a denied STOP.
    # The void device free API cannot report BUSY, so retain the object
    # until a controlled, verified recovery instead of risking UAF.
    s=one(s,
        """void subghz_device_cc1101_ext_free(void) {
    furi_assert(subghz_device_cc1101_ext != NULL);""",
        """void subghz_device_cc1101_ext_free(void) {
    if(!subghz_device_cc1101_ext) return;
    if(e11_ext_rx_owner || e11_ext_rx_fault) {
        FURI_LOG_E(TAG, "E11 external RX lease still held; skip radio free");
        return;
    }""")
    s=one(s,
        """void subghz_device_cc1101_ext_set_async_mirror_pin(const GpioPin* pin) {
    subghz_device_cc1101_ext->async_mirror_pin = pin;
}""",
        """void subghz_device_cc1101_ext_set_async_mirror_pin(const GpioPin* pin) {
    if(!subghz_device_cc1101_ext || e11_ext_rx_owner || e11_ext_rx_fault) return;
    subghz_device_cc1101_ext->async_mirror_pin = pin;
}""")
    s=one(s,
        """static void subghz_device_cc1101_ext_capture_ISR(void* context) {
    UNUSED(context);
    if(!furi_hal_gpio_read""",
        """static void subghz_device_cc1101_ext_capture_ISR(void* context) {
    UNUSED(context);
    if(!e11_ext_rx_ready()) return; /* No stale foreign PB2/TIM17 writes. */
    if(!furi_hal_gpio_read""")
    s=one(s,
        """void subghz_device_cc1101_ext_start_async_rx(
    SubGhzDeviceCC1101ExtCaptureCallback callback,
    void* context) {
    furi_assert(subghz_device_cc1101_ext->state == SubGhzDeviceCC1101ExtStateIdle);
    subghz_device_cc1101_ext->state = SubGhzDeviceCC1101ExtStateAsyncRx;""",
        """bool subghz_device_cc1101_ext_try_start_async_rx(
    SubGhzDeviceCC1101ExtCaptureCallback callback,
    void* context) {
    if(!subghz_device_cc1101_ext || !callback ||
       subghz_device_cc1101_ext->state != SubGhzDeviceCC1101ExtStateIdle ||
       e11_ext_rx_owner || e11_ext_rx_fault) return false;
    /* External G0 is PB2 in this pinned firmware. Non-PB2 G0 and
     * arbitrary debug mirror pins require other atomic resource masks;
     * fail CLOSED rather than overwrite foreign GPIO/EXTI callbacks.
     */
    if(subghz_device_cc1101_ext->g0_pin != &gpio_ext_pb2 ||
       subghz_device_cc1101_ext->async_mirror_pin != NULL) {
        FURI_LOG_W(TAG, "External CC1101 RX pin/mirror requires E11 owner");
        return false;
    }
    const uint32_t owner=furi_hal_resource_lease_try_acquire(
        FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX);
    if(!owner) return false;
    if(furi_hal_bus_is_enabled(FuriHalBusTIM17)) {
        if(!furi_hal_resource_lease_release(owner,FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX)) {
            e11_ext_rx_owner=owner;
            e11_ext_rx_fault=true;
        }
        return false;
    }
    /* Claim native callback slot BEFORE any TIM17, radio or GPIO writes.
     * NEVER remove somebody else's EXTI2 callback to force start.
     */
    e11_ext_rx_owner=owner;
    if(!furi_hal_gpio_try_add_int_callback(
           subghz_device_cc1101_ext->g0_pin,
           subghz_device_cc1101_ext_capture_ISR,
           subghz_device_cc1101_ext)) {
        if(furi_hal_resource_lease_release(owner,FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX)) {
            e11_ext_rx_owner=0U;
        } else {
            e11_ext_rx_fault=true;
        }
        return false;
    }
    subghz_device_cc1101_ext->state = SubGhzDeviceCC1101ExtStateAsyncRx;""")
    s=one(s,
        """    furi_hal_gpio_init(
        subghz_device_cc1101_ext->g0_pin, GpioModeInterruptRiseFall, GpioPullUp, GpioSpeedVeryHigh);
    furi_hal_gpio_remove_int_callback(subghz_device_cc1101_ext->g0_pin);
    furi_hal_gpio_add_int_callback(
        subghz_device_cc1101_ext->g0_pin,
        subghz_device_cc1101_ext_capture_ISR,
        subghz_device_cc1101_ext->async_rx.capture_callback);""",
        """    furi_hal_gpio_init(
        subghz_device_cc1101_ext->g0_pin, GpioModeInterruptRiseFall, GpioPullUp, GpioSpeedVeryHigh);""")
    s=one(s,
        """    subghz_device_cc1101_ext->async_rx.capture_delta_duration = 0;
}

void subghz_device_cc1101_ext_stop_async_rx(void) {
    furi_assert(subghz_device_cc1101_ext->state == SubGhzDeviceCC1101ExtStateAsyncRx);
    subghz_device_cc1101_ext->state = SubGhzDeviceCC1101ExtStateIdle;""",
        """    subghz_device_cc1101_ext->async_rx.capture_delta_duration = 0;
    return true;
}

/* Preserve the radio-plugin's original void interconnect callback ABI. */
void subghz_device_cc1101_ext_start_async_rx(
    SubGhzDeviceCC1101ExtCaptureCallback callback, void* context) {
    (void)subghz_device_cc1101_ext_try_start_async_rx(callback,context);
}

void subghz_device_cc1101_ext_stop_async_rx(void) {
    if(!e11_ext_rx_ready()) return;
    if(subghz_device_cc1101_ext->state != SubGhzDeviceCC1101ExtStateAsyncRx) {
        e11_ext_rx_fault=true;
        return;
    }
    /* Callback remove first. If replaced, do not disable radio/TIM17
     * nor reset someone else's G0 configuration.
     */
    if(!furi_hal_gpio_try_remove_int_callback(
           subghz_device_cc1101_ext->g0_pin,
           subghz_device_cc1101_ext_capture_ISR,
           subghz_device_cc1101_ext)) {
        e11_ext_rx_fault=true;
        return;
    }
    subghz_device_cc1101_ext->state = SubGhzDeviceCC1101ExtStateIdle;""")
    s=one(s,
        """    furi_hal_gpio_remove_int_callback(subghz_device_cc1101_ext->g0_pin);
    furi_hal_gpio_init(subghz_device_cc1101_ext->g0_pin, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
}

void subghz_device_cc1101_ext_async_tx_middleware_idle(""",
        """    furi_hal_gpio_init(subghz_device_cc1101_ext->g0_pin, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
    if(furi_hal_resource_lease_release(
           e11_ext_rx_owner,FURI_HAL_LEASE_NATIVE_EXT_CC1101_RX)) {
        e11_ext_rx_owner=0U;
        subghz_device_cc1101_ext->async_rx.capture_callback=NULL;
        subghz_device_cc1101_ext->async_rx.capture_callback_context=NULL;
    } else {
        e11_ext_rx_fault=true; /* Sticky exact-owner failure. */
    }
}

void subghz_device_cc1101_ext_async_tx_middleware_idle(""")
    header=one(header,
        "void subghz_device_cc1101_ext_start_async_rx(",
        "/* E11: BUSY before TIM17/PB2/EXTI2 mutation; old void ABI retained. */\n"
        "bool subghz_device_cc1101_ext_try_start_async_rx(\n"
        "    SubGhzDeviceCC1101ExtCaptureCallback callback, void* context);\n"
        "void subghz_device_cc1101_ext_start_async_rx(")
    return h,r,s,header

def main():
    p=argparse.ArgumentParser();p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args();root=a.firmware_root.resolve()
    try:
        if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()!=PIN:
            raise ValueError("Unpinned Momentum SHA")
        dirty=set()
        for line in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Untracked/renamed source")
            dirty.add(line[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unreviewed native changes "+repr(sorted(dirty^EXPECTED)))
        paths=(H,R,EXT,EXT_H)
        old=[(root/path).read_text(encoding="utf-8") for path in paths]
        new=patch(*old)
        print("E11 EXT CC1101 TIM17/PB2/EXTI2 PINNED SOURCE PREFLIGHT PASS")
        if a.apply:
            for path,content in zip(paths,new):
                (root/path).write_text(content,encoding="utf-8")
            print("EXTERNAL PLUGIN + SHARED ALLOCATOR SOURCE ONLY; NO FLASH")
        else:
            print("READ-ONLY; no firmware files modified")
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:
        print("E11 EXTERNAL CC1101 SOURCE REFUSED: "+str(exc),file=sys.stderr)
        raise SystemExit(1)

if __name__=="__main__":
    main()
