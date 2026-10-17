#!/usr/bin/env python3
"""E11 NFC ISO15693 transparent-mode EXIT must propagate NFC IRQ BUSY.

The original void re-registration silently assumed the PA2+EXTI2 slot
was free. Keep SPI cleanup, avoid unmasking IRQ when restoration fails,
and return BUSY from listener deinit. No device changes.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_e11_extended_dma_lease import EXPECTED as V2_PRE,H,R,API
SOURCE="targets/f7/furi_hal/furi_hal_nfc_iso15693.c"
EXPECTED=V2_PRE | {H,R,API}
PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
MARK="/* E11 ISO15693 exact NFC IRQ restoration BUSY return. */"

def one(s,old,new):
    if s.count(old)!=1: raise ValueError("Pinned ISO15693 restore source changed "+repr(old[:115]))
    return s.replace(old,new,1)

def patch(s):
    if MARK in s: raise ValueError("Already staged")
    s=one(s,
        """static void
    furi_hal_nfc_iso15693_listener_transparent_mode_exit(const FuriHalSpiBusHandle* handle) {
    // Configure gpio back to SPI and exit transparent mode
    furi_hal_nfc_init_gpio_isr();
    furi_hal_spi_bus_handle_init(handle);

    st25r3916_direct_cmd(handle, ST25R3916_CMD_UNMASK_RECEIVE_DATA);
}""",
        """/* E11 ISO15693 exact NFC IRQ restoration BUSY return. */
static bool
    furi_hal_nfc_iso15693_listener_transparent_mode_exit(const FuriHalSpiBusHandle* handle) {
    /* This NFC PA2/EXTI2 was released for SignalReader transparent
     * receive. If another owner holds EXTI2, do not overwrite callback,
     * reconfigure PA2 or unmask an IRQ with no owned handler.
     */
    const bool irq_restored=furi_hal_nfc_try_init_gpio_isr();
    furi_hal_spi_bus_handle_init(handle); /* Restore SPI even on BUSY. */
    if(!irq_restored) {
        FURI_LOG_W(TAG, "NFC ISO15693 IRQ restoration BUSY");
        return false;
    }
    st25r3916_direct_cmd(handle, ST25R3916_CMD_UNMASK_RECEIVE_DATA);
    return true;
}""")
    s=one(s,
        """    furi_hal_nfc_iso15693_listener_transparent_mode_exit(handle);

    furi_hal_nfc_iso15693_listener_free(furi_hal_nfc_iso15693_listener);
    furi_hal_nfc_iso15693_listener = NULL;

    return FuriHalNfcErrorNone;""",
        """    const bool e11_irq_restored=furi_hal_nfc_iso15693_listener_transparent_mode_exit(handle);

    furi_hal_nfc_iso15693_listener_free(furi_hal_nfc_iso15693_listener);
    furi_hal_nfc_iso15693_listener = NULL;

    /* Never claim a clean native listener deinit when its interrupt
     * callback could not be restored. The caller sees hardware BUSY.
     */
    return e11_irq_restored ? FuriHalNfcErrorNone : FuriHalNfcErrorBusy;""")
    return s

def main():
    p=argparse.ArgumentParser();p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args();root=a.firmware_root.resolve()
    try:
        if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()!=PIN:
            raise ValueError("Unpinned Momentum source")
        dirty=set()
        for line in subprocess.check_output(["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Untracked or renamed native source")
            dirty.add(line[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unreviewed source changes "+repr(sorted(dirty^EXPECTED)))
        source=(root/SOURCE).read_text(encoding="utf-8")
        modified=patch(source)
        print("E11 NFC ISO15693 TRANSPARENT IRQ RESTORE SOURCE PREFLIGHT PASS")
        if a.apply:
            (root/SOURCE).write_text(modified,encoding="utf-8")
            print("NFC SOURCE ONLY; NO FLASH/SD/DEVICE")
        else:
            print("READ ONLY; source unchanged")
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 NFC ISO15693 SOURCE REFUSED: "+str(e),file=sys.stderr)
        raise SystemExit(1)

if __name__=="__main__":
    main()
