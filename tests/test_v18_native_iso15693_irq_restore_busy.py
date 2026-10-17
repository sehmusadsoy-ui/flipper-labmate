#!/usr/bin/env python3
"""Compile original patched NFC ISO15693 transparent exit and deinit C.

Tests successful and denied PA2/EXTI2 restoration without unmasking
the ST25R receive IRQ on BUSY. No NFC radio/device simulation claimed.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import tempfile

STUB=r"""
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <assert.h>
#define furi_check(x) assert(x)
#define TAG "Iso15693"
#define FURI_LOG_W(...) ((void)0)
enum { FuriHalNfcErrorNone=0,FuriHalNfcErrorBusy=42,
 ST25R3916_CMD_UNMASK_RECEIVE_DATA=1 };
typedef int FuriHalNfcError;
typedef struct {int id;} FuriHalSpiBusHandle;
typedef struct {int dummy;} FuriHalNfcIso15693Listener;
static FuriHalNfcIso15693Listener listener={0};
static FuriHalNfcIso15693Listener* furi_hal_nfc_iso15693_listener=&listener;
static bool accept_irq;
static int irq_requests,spi_resets,unmask_calls,frees;
static bool furi_hal_nfc_try_init_gpio_isr(void) {
 irq_requests++;return accept_irq;
}
static void furi_hal_spi_bus_handle_init(const FuriHalSpiBusHandle* handle) {
 assert(handle && handle->id==1);spi_resets++;
}
static void st25r3916_direct_cmd(const FuriHalSpiBusHandle* handle,int cmd) {
 assert(handle && cmd==ST25R3916_CMD_UNMASK_RECEIVE_DATA);
 unmask_calls++;
}
static void furi_hal_nfc_iso15693_listener_free(FuriHalNfcIso15693Listener* l) {
 assert(l==&listener);frees++;
}
"""
RUN=r"""
int main(void) {
 FuriHalSpiBusHandle handle={1};
 accept_irq=false;
 assert(!furi_hal_nfc_iso15693_listener_transparent_mode_exit(&handle));
 assert(irq_requests==1 && spi_resets==1 && unmask_calls==0);
 assert(furi_hal_nfc_iso15693_listener_deinit(&handle)==FuriHalNfcErrorBusy);
 assert(irq_requests==2 && spi_resets==2 && unmask_calls==0 && frees==1);
 assert(furi_hal_nfc_iso15693_listener==NULL);
 furi_hal_nfc_iso15693_listener=&listener;
 accept_irq=true;
 assert(furi_hal_nfc_iso15693_listener_deinit(&handle)==FuriHalNfcErrorNone);
 assert(irq_requests==3 && spi_resets==3 && unmask_calls==1 && frees==2);
 assert(furi_hal_nfc_iso15693_listener==NULL);
 puts("E11 original ISO15693 NFC IRQ restoration: BUSY without unmask, cleanup PASS");
 return 0;
}
"""

def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    file=(root/"targets/f7/furi_hal/furi_hal_nfc_iso15693.c").read_text()
    nfc=(root/"targets/f7/furi_hal/furi_hal_nfc_irq.c").read_text()
    assert "/* E11 ISO15693 exact NFC IRQ restoration BUSY return. */" in file
    assert "bool furi_hal_nfc_try_init_gpio_isr(void)" in nfc
    assert "furi_hal_nfc_init_gpio_isr();" not in file[
        file.index("/* E11 ISO15693 exact NFC IRQ restoration BUSY return. */"):
        file.index("static FuriHalNfcError furi_hal_nfc_iso15693_listener_init")]
    helper=file[file.index("/* E11 ISO15693 exact NFC IRQ restoration BUSY return. */"):
                file.index("static FuriHalNfcError furi_hal_nfc_iso15693_listener_init")]
    deinit=file[file.index("static FuriHalNfcError furi_hal_nfc_iso15693_listener_deinit("):
                file.index("static FuriHalNfcError\n    furi_hal_nfc_iso15693_listener_tx_transparent")]
    assert "return e11_irq_restored ? FuriHalNfcErrorNone : FuriHalNfcErrorBusy;" in deinit
    assert "if(!irq_restored)" in helper
    assert helper.index("if(!irq_restored)") < helper.index(
        "st25r3916_direct_cmd(handle, ST25R3916_CMD_UNMASK_RECEIVE_DATA)")
    with tempfile.TemporaryDirectory(prefix="e11_iso15693_restore_") as tmp:
        d=Path(tmp);exe=d/"test"
        (d/"test.c").write_text(STUB+"\n"+helper+"\n"+deinit+"\n"+RUN)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
                        "-pedantic",str(d/"test.c"),"-o",str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print("E11 genuine NFC ISO15693 transparent callback restore C HOST PASS")
    print("SignalReader DMA start/STOP and full NFC RF card hardware remain OPEN.")

if __name__=="__main__":
    main()
