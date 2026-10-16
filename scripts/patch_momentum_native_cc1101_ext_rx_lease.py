#!/usr/bin/env python3
"""Pin exact external CC1101 RX to TIM17+PB2+EXTI2, no callback stealing.

Scope intentionally excludes alternate G0 pins and debug mirror. Keeps the
upstream void device ABI; a new bool TRY_START returns BUSY to native callers.
NO flash, SD or main.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_serial_expansion_exti_lease import EXPECTED as SER_PRE, SER, PUB
from patch_momentum_native_nfc_irq_exti_lease import IRQ, NFC, I
from patch_momentum_native_onewire_slave_exti_lease import H, R, GH, GC, OH, OC, DALLAS, API
from patch_momentum_native_subghz_tx_lease import S as SUB

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
C="applications/drivers/subghz/cc1101_ext/cc1101_ext.c"
CH="applications/drivers/subghz/cc1101_ext/cc1101_ext.h"
EXPECTED=SER_PRE|{H,R,GH,GC,OH,OC,DALLAS,API,SUB,IRQ,NFC,I,SER,PUB}
MARK="/* E11 external CC1101 TIM17/PB2/EXTI2 exact RX owner. */"

def once(s,old,new):
    if s.count(old)!=1: raise ValueError("Unreviewed pinned CC1101 source "+repr(old[:125]))
    return s.replace(old,new,1)

def patch(h,r,src,header):
    if MARK in src or "FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX" in h:
        raise ValueError("External CC1101 RX already patched")
    h=once(h,
        "#define FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 (FuriHalLeaseLpuart1|FuriHalLeasePc0|FuriHalLeaseExti0)\n",
        "#define FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 (FuriHalLeaseLpuart1|FuriHalLeasePc0|FuriHalLeaseExti0)\n"
        "/* External CC1101 default G0=connector PB2; TIM17 shared NFC timer. */\n"
        "#define FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX (FuriHalLeaseTim17|FuriHalLeasePb2|FuriHalLeaseExti2)\n")
    r=once(r,
        "           mask == FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_SERIAL_EXP_LPUART1 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX ||\n")
    src=once(src,
        "static SubGhzDeviceCC1101Ext* subghz_device_cc1101_ext = NULL;",
        """/* E11 external CC1101 TIM17/PB2/EXTI2 exact RX owner. */
static uint32_t e11_cc1101_rx_handle;
static bool e11_cc1101_rx_fault;

static SubGhzDeviceCC1101Ext* subghz_device_cc1101_ext = NULL;""")
    src=once(src,
        "void subghz_device_cc1101_ext_set_async_mirror_pin(const GpioPin* pin) {\n    subghz_device_cc1101_ext->async_mirror_pin = pin;",
        "void subghz_device_cc1101_ext_set_async_mirror_pin(const GpioPin* pin) {\n"
        "    if(e11_cc1101_rx_handle || e11_cc1101_rx_fault) return;\n"
        "    subghz_device_cc1101_ext->async_mirror_pin = pin;")
    src=once(src,
        "static void subghz_device_cc1101_ext_capture_ISR(void* context) {\n    UNUSED(context);",
        "static void subghz_device_cc1101_ext_capture_ISR(void* context) {\n"
        "    UNUSED(context);\n"
        "    if(!e11_cc1101_rx_handle || e11_cc1101_rx_fault) return;\n"
        "    if(!furi_hal_bus_is_enabled(FuriHalBusTIM17)) {\n"
        "        e11_cc1101_rx_fault=true;\n"
        "        return;\n"
        "    }")
    src=once(src,
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
       e11_cc1101_rx_handle || e11_cc1101_rx_fault) return false;
    /* Unsupported alternate G0/debug pins must not silently operate
     * without atomic pin/EXTI/mirror resource coverage.
     */
    if(subghz_device_cc1101_ext->g0_pin != &gpio_ext_pb2 ||
       subghz_device_cc1101_ext->async_mirror_pin != NULL) return false;
    const uint32_t lease=furi_hal_resource_lease_try_acquire(
        FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX);
    if(!lease) return false;
    if(furi_hal_bus_is_enabled(FuriHalBusTIM17)) {
        if(!furi_hal_resource_lease_release(lease,FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX)) {
            e11_cc1101_rx_handle=lease;
            e11_cc1101_rx_fault=true;
        }
        return false;
    }
    e11_cc1101_rx_handle=lease;
    /* Atomic callback registration before any GPIO/timer/radio writes.
     * NEVER remove a pre-existing EXTI2 owner.
     */
    if(!furi_hal_gpio_try_add_int_callback(
           subghz_device_cc1101_ext->g0_pin,
           subghz_device_cc1101_ext_capture_ISR,
           (void*)callback)) {
        if(furi_hal_resource_lease_release(lease,FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX)) {
            e11_cc1101_rx_handle=0U;
        } else {
            e11_cc1101_rx_fault=true;
        }
        return false;
    }
    subghz_device_cc1101_ext->state = SubGhzDeviceCC1101ExtStateAsyncRx;""")
    src=once(src,
        """    furi_hal_gpio_init(
        subghz_device_cc1101_ext->g0_pin, GpioModeInterruptRiseFall, GpioPullUp, GpioSpeedVeryHigh);
    furi_hal_gpio_remove_int_callback(subghz_device_cc1101_ext->g0_pin);
    furi_hal_gpio_add_int_callback(
        subghz_device_cc1101_ext->g0_pin,
        subghz_device_cc1101_ext_capture_ISR,
        subghz_device_cc1101_ext->async_rx.capture_callback);""",
        """    furi_hal_gpio_init(
        subghz_device_cc1101_ext->g0_pin, GpioModeInterruptRiseFall, GpioPullUp, GpioSpeedVeryHigh);""")
    src=once(src,
        """    subghz_device_cc1101_ext->async_rx.capture_delta_duration = 0;
}

void subghz_device_cc1101_ext_stop_async_rx(void) {
    furi_assert(subghz_device_cc1101_ext->state == SubGhzDeviceCC1101ExtStateAsyncRx);
    subghz_device_cc1101_ext->state = SubGhzDeviceCC1101ExtStateIdle;""",
        """    subghz_device_cc1101_ext->async_rx.capture_delta_duration = 0;
    return true;
}

/* Retain legacy public void driver ABI. */
void subghz_device_cc1101_ext_start_async_rx(
    SubGhzDeviceCC1101ExtCaptureCallback callback, void* context) {
    (void)subghz_device_cc1101_ext_try_start_async_rx(callback,context);
}

void subghz_device_cc1101_ext_stop_async_rx(void) {
    if(!e11_cc1101_rx_handle || e11_cc1101_rx_fault ||
       !subghz_device_cc1101_ext ||
       subghz_device_cc1101_ext->state != SubGhzDeviceCC1101ExtStateAsyncRx)
        return;
    if(!furi_hal_bus_is_enabled(FuriHalBusTIM17)) {
        e11_cc1101_rx_fault=true;
        return;
    }
    /* Callback CAS removal MUST precede even the radio idle transition. */
    if(!furi_hal_gpio_try_remove_int_callback(
           subghz_device_cc1101_ext->g0_pin,
           subghz_device_cc1101_ext_capture_ISR,
           (void*)subghz_device_cc1101_ext->async_rx.capture_callback)) {
        e11_cc1101_rx_fault=true;
        return;
    }
    subghz_device_cc1101_ext->state = SubGhzDeviceCC1101ExtStateIdle;""")
    src=once(src,
        """    FURI_CRITICAL_EXIT();
    furi_hal_gpio_remove_int_callback(subghz_device_cc1101_ext->g0_pin);
    furi_hal_gpio_init(subghz_device_cc1101_ext->g0_pin, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
}

void subghz_device_cc1101_ext_async_tx_middleware_idle(""",
        """    FURI_CRITICAL_EXIT();
    furi_hal_gpio_init(subghz_device_cc1101_ext->g0_pin, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
    if(furi_hal_resource_lease_release(
           e11_cc1101_rx_handle,FURI_HAL_LEASE_NATIVE_CC1101_EXT_RX)) {
        e11_cc1101_rx_handle=0U;
        subghz_device_cc1101_ext->async_rx.capture_callback=NULL;
        subghz_device_cc1101_ext->async_rx.capture_callback_context=NULL;
    } else {
        e11_cc1101_rx_fault=true;
    }
}

void subghz_device_cc1101_ext_async_tx_middleware_idle(""")
    header=once(header,
        "void subghz_device_cc1101_ext_start_async_rx(",
        "/* E11: bool reports TIM17/PB2/EXTI2 BUSY, no callback theft. */\n"
        "bool subghz_device_cc1101_ext_try_start_async_rx(\n"
        "    SubGhzDeviceCC1101ExtCaptureCallback callback, void* context);\n"
        "void subghz_device_cc1101_ext_start_async_rx(")
    return h,r,src,header

def main():
    p=argparse.ArgumentParser();p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args();root=a.firmware_root.resolve()
    try:
        if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()!=PIN:
            raise ValueError("Unexpected Momentum source")
        changed=set()
        for ln in subprocess.check_output(["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(ln)<4 or ln[:2]=="??" or "->" in ln: raise ValueError("Untracked/renamed native source")
            changed.add(ln[3:])
        if changed!=EXPECTED: raise ValueError("Unexpected native source changes "+repr(sorted(changed^EXPECTED)))
        paths=(H,R,C,CH)
        old=[(root/x).read_text(encoding="utf-8") for x in paths]
        new=patch(*old)
        print("E11 EXTERNAL CC1101 PB2/EXTI2/TIM17 NATIVE SOURCE PREFLIGHT PASS")
        if a.apply:
            for name,content in zip(paths,new): (root/name).write_text(content,encoding="utf-8")
            print("SOURCE ONLY; NO DEVICE, SD OR FLASH")
        else: print("READ ONLY; NO MODIFICATIONS")
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 EXT CC1101 SOURCE REFUSED: "+str(e),file=sys.stderr);return 1
    return 0

if __name__=="__main__": raise SystemExit(main())
