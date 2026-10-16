#!/usr/bin/env python3
"""E11 pinned Momentum NFC internal IRQ PA2+EXTI2 claim with owned callback.

Requires preexisting cooperative NFC TIM1/TIM17 + GPIO E11.1c TRY-ADD
and OneWire compare-and-remove stage. Source-only, never flashes device.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_onewire_slave_exti_lease import EXPECTED as OW_PRE, H, R, GH, GC, OH, OC, DALLAS, API
from patch_momentum_native_subghz_tx_lease import S as SUB

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
IRQ="targets/f7/furi_hal/furi_hal_nfc_irq.c"
NFC="targets/f7/furi_hal/furi_hal_nfc.c"
I="targets/f7/furi_hal/furi_hal_nfc_i.h"
MARK="/* E11 native NFC PA2+EXTI2 IRQ owner. */"
EXPECTED=OW_PRE | {H,R,SUB,GH,GC,OH,OC,DALLAS,API}

def once(s:str,old:str,new:str)->str:
    if s.count(old)!=1:
        raise ValueError("Pinned NFC IRQ source mismatch "+repr(old[:100]))
    return s.replace(old,new,1)

def patch(h:str,r:str,irq:str,nfc:str,internal:str):
    if MARK in irq or "FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2" in h:
        raise ValueError("NFC IRQ owner stage already applied")
    if "bool furi_hal_nfc_timers_init(void)" not in internal:
        raise ValueError("Missing cooperative NFC TIM1/TIM17 prerequisite")
    h=once(h,
        "#define FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14 (FuriHalLeasePb14|FuriHalLeaseExti14)\n",
        "#define FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14 (FuriHalLeasePb14|FuriHalLeaseExti14)\n"
        "/* NFC ST25R3916 IRQ/RFID_PULL is internal PA2 and EXTI2. */\n"
        "enum { FuriHalLeasePa2 = (1U << 29) };\n"
        "#define FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2 (FuriHalLeasePa2|FuriHalLeaseExti2)\n")
    r=once(r,
        "           mask == FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14 ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_ONEWIRE_SLAVE_PB14_EXTI14 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2 ||\n")
    irq=once(irq,
        "static void furi_hal_nfc_int_callback(void* context) {\n    UNUSED(context);\n",
        """/* E11 native NFC PA2+EXTI2 IRQ owner. */
static uint32_t e11_nfc_irq_handle;
static bool e11_nfc_irq_fault;

static void furi_hal_nfc_int_callback(void* context) {
    UNUSED(context);
    if(!e11_nfc_irq_handle || e11_nfc_irq_fault) return;
""")
    irq=once(irq,
        """void furi_hal_nfc_init_gpio_isr(void) {
    furi_hal_gpio_init(
        &gpio_nfc_irq_rfid_pull, GpioModeInterruptRise, GpioPullDown, GpioSpeedVeryHigh);
    furi_hal_gpio_add_int_callback(&gpio_nfc_irq_rfid_pull, furi_hal_nfc_int_callback, NULL);
    furi_hal_gpio_enable_int_callback(&gpio_nfc_irq_rfid_pull);
}

void furi_hal_nfc_deinit_gpio_isr(void) {
    furi_hal_gpio_remove_int_callback(&gpio_nfc_irq_rfid_pull);
    furi_hal_gpio_init(&gpio_nfc_irq_rfid_pull, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
}""",
        """bool furi_hal_nfc_try_init_gpio_isr(void) {
    if(e11_nfc_irq_handle || e11_nfc_irq_fault) return false;
    const uint32_t lease=furi_hal_resource_lease_try_acquire(
        FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2);
    if(!lease) return false;
    /* The already-tested GPIO E11.1c TRY-ADD checks the shared EXTI
     * callback slot atomically BEFORE any PA2 GPIO mode write.
     */
    e11_nfc_irq_handle=lease;
    if(!furi_hal_gpio_try_add_int_callback(
           &gpio_nfc_irq_rfid_pull, furi_hal_nfc_int_callback, NULL)) {
        if(furi_hal_resource_lease_release(lease,FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2)) {
            e11_nfc_irq_handle=0U;
        } else {
            e11_nfc_irq_fault=true;
        }
        return false;
    }
    furi_hal_gpio_init(
        &gpio_nfc_irq_rfid_pull, GpioModeInterruptRise, GpioPullDown, GpioSpeedVeryHigh);
    return true;
}

/* Keep native private void ABI for existing firmware callers. */
void furi_hal_nfc_init_gpio_isr(void) {
    (void)furi_hal_nfc_try_init_gpio_isr();
}

void furi_hal_nfc_deinit_gpio_isr(void) {
    if(!e11_nfc_irq_handle || e11_nfc_irq_fault) return;
    /* Mismatched callback is NEVER removed; no foreign PA2 reset. */
    if(!furi_hal_gpio_try_remove_int_callback(
           &gpio_nfc_irq_rfid_pull, furi_hal_nfc_int_callback, NULL)) {
        e11_nfc_irq_fault=true;
        return;
    }
    furi_hal_gpio_init(&gpio_nfc_irq_rfid_pull, GpioModeAnalog, GpioPullNo, GpioSpeedLow);
    const uint32_t owner=e11_nfc_irq_handle;
    if(furi_hal_resource_lease_release(owner,FURI_HAL_LEASE_NATIVE_NFC_IRQ_PA2_EXTI2)) {
        e11_nfc_irq_handle=0U;
    } else {
        e11_nfc_irq_fault=true;
    }
}""")
    internal=once(internal,
        "void furi_hal_nfc_init_gpio_isr(void);",
        "void furi_hal_nfc_init_gpio_isr(void);\n"
        "/* E11: NFC PA2/EXTI2 BUSY is reported before any GPIO mode changes. */\n"
        "bool furi_hal_nfc_try_init_gpio_isr(void);")
    nfc=once(nfc,
        """        // Enable interrupts
        furi_hal_nfc_init_gpio_isr();
        // Disable internal overheat protection""",
        """        // Enable interrupts, but never replace a live EXTI2 callback.
        if(!furi_hal_nfc_try_init_gpio_isr()) {
            error=FuriHalNfcErrorBusy;
            furi_hal_nfc_low_power_mode_start();
            furi_hal_nfc_release();
            break;
        }
        // Disable internal overheat protection""")
    nfc=once(nfc,
        """        furi_hal_nfc_init_gpio_isr();
        error = furi_hal_nfc_turn_on_osc(handle);
        if(error != FuriHalNfcErrorNone) {""",
        """        if(!furi_hal_nfc_try_init_gpio_isr()) {
            error=FuriHalNfcErrorBusy;
            furi_hal_nfc_timers_deinit(); /* Undo only successfully held timers. */
            break;
        }
        error = furi_hal_nfc_turn_on_osc(handle);
        if(error != FuriHalNfcErrorNone) {""")
    return h,r,irq,nfc,internal

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args();root=a.firmware_root.resolve()
    try:
        sha=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if sha!=PIN: raise ValueError("Unpinned Momentum SHA")
        dirty=set()
        for line in subprocess.check_output(["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Renamed/untracked native source")
            dirty.add(line[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unreviewed native source "+repr(sorted(dirty^EXPECTED)))
        ow=(root/OC).read_text(encoding="utf-8")
        gpio=(root/GC).read_text(encoding="utf-8")
        if "/* E11 native OneWire PB14+EXTI14 owner. */" not in ow or (
            "bool furi_hal_gpio_try_remove_int_callback(" not in gpio):
            raise ValueError("Native OneWire/EXTI exact-owner predecessor missing")
        paths=(H,R,IRQ,NFC,I)
        before=[(root/x).read_text(encoding="utf-8") for x in paths]
        after=patch(*before)
        print("E11 NFC PA2/EXTI2 SOURCE PREFLIGHT PASS")
        if a.apply:
            for x,v in zip(paths,after):
                (root/x).write_text(v,encoding="utf-8")
            print("NATIVE NFC IRQ SOURCE ONLY; NO FLASH, SD, USB OR DEVICE")
        else:
            print("READ ONLY; no modifications")
        return 0
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 NFC IRQ REFUSED: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
