#!/usr/bin/env python3
"""Pinned E11 external CC1101 TX TIM17/PB2 + DMA2 CH3/4/5 V2 lease.

Original bool TX API, region restrictions and plugin ABI unchanged. This
stage only supports the default external G0 PB2 with NO debug mirror;
unreviewed pins fail closed rather than running unleased. No flash.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_signal_reader_e11_lease import (
    EXPECTED as SIGNAL_PRE, READER, READER_H, PARSER, PARSER_H, NFC,
)
from patch_momentum_native_ext_cc1101_rx_lease import EXT
PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
EXPECTED=SIGNAL_PRE | {READER,READER_H,PARSER,PARSER_H,NFC}
MARK="/* E11 native external CC1101 TX TIM17/DMA2 V2 owner. */"

def one(s,old,new):
    if s.count(old)!=1:
        raise ValueError("Pinned CC1101 TX anchor missing/ambiguous "+repr(old[:120]))
    return s.replace(old,new,1)

def patch(s):
    if MARK in s: raise ValueError("External TX stage already present")
    if "/* E11 external CC1101 RX TIM17+PB2+EXTI2 owner. */" not in s:
        raise ValueError("No cooperative external RX prerequisite")
    s=one(s,
        "static bool e11_ext_rx_fault;\n",
        "static bool e11_ext_rx_fault;\n"
        "static uint32_t e11_ext_tx_owner;\n"
        "static bool e11_ext_tx_fault;\n")
    s=one(s,
        """void subghz_device_cc1101_ext_set_async_mirror_pin(const GpioPin* pin) {
    if(!subghz_device_cc1101_ext || e11_ext_rx_owner || e11_ext_rx_fault) return;""",
        """void subghz_device_cc1101_ext_set_async_mirror_pin(const GpioPin* pin) {
    if(!subghz_device_cc1101_ext || e11_ext_rx_owner || e11_ext_rx_fault ||
       e11_ext_tx_owner || e11_ext_tx_fault) return;""")
    s=one(s,
        """static void subghz_device_cc1101_ext_async_tx_dma_isr(void* context) {
    UNUSED(context);
    furi_assert(subghz_device_cc1101_ext->state == SubGhzDeviceCC1101ExtStateAsyncTx);""",
        """/* E11 native external CC1101 TX TIM17/DMA2 V2 owner. */
static bool e11_ext_tx_ready(void) {
    if(!e11_ext_tx_owner || e11_ext_tx_fault) return false;
    if(!furi_hal_bus_is_enabled(FuriHalBusTIM17) ||
       !LL_DMA_IsEnabledChannel(SUBGHZ_DEVICE_CC1101_EXT_DMA_CH3_DEF) ||
       !LL_DMA_IsEnabledChannel(SUBGHZ_DEVICE_CC1101_EXT_DMA_CH4_DEF)) {
        e11_ext_tx_fault=true;
        return false;
    }
    return true;
}

static void subghz_device_cc1101_ext_async_tx_dma_isr(void* context) {
    UNUSED(context);
    if(!e11_ext_tx_ready()) return;
    if(subghz_device_cc1101_ext->state != SubGhzDeviceCC1101ExtStateAsyncTx) {
        e11_ext_tx_fault=true;
        return;
    }""")
    s=one(s,
        """bool subghz_device_cc1101_ext_start_async_tx(SubGhzDeviceCC1101ExtCallback callback, void* context) {
    furi_assert(subghz_device_cc1101_ext->state == SubGhzDeviceCC1101ExtStateIdle);
    furi_assert(callback);

    //If transmission is prohibited by regional settings
    if(subghz_device_cc1101_ext->regulation != SubGhzDeviceCC1101ExtRegulationTxRx) return false;

    subghz_device_cc1101_ext->async_tx.callback = callback;""",
        """bool subghz_device_cc1101_ext_start_async_tx(SubGhzDeviceCC1101ExtCallback callback, void* context) {
    if(!subghz_device_cc1101_ext || !callback ||
       subghz_device_cc1101_ext->state != SubGhzDeviceCC1101ExtStateIdle ||
       e11_ext_tx_owner || e11_ext_tx_fault) return false;

    /* Original regional TX restrictions remain the first policy gate. */
    if(subghz_device_cc1101_ext->regulation != SubGhzDeviceCC1101ExtRegulationTxRx) return false;

    /* Default external G0 is PB2. The unreviewed arbitrary G0/mirror
     * paths must not configure a pin we cannot atomically lease.
     */
    if(subghz_device_cc1101_ext->g0_pin != &gpio_ext_pb2 ||
       subghz_device_cc1101_ext->async_mirror_pin != NULL) {
        FURI_LOG_W(TAG,"External CC1101 TX G0/mirror GPIO not lease-managed");
        return false;
    }
    const uint32_t lease=furi_hal_resource_lease_v2_try_acquire(
        FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX);
    if(!lease) return false;
    /* Check even CH5 (reserved for optional debug) because the V2 mask
     * claims all three channels. NO GPIO, DMA, IRQ or radio writes yet.
     */
    if(furi_hal_bus_is_enabled(FuriHalBusTIM17) ||
       LL_DMA_IsEnabledChannel(SUBGHZ_DEVICE_CC1101_EXT_DMA_CH3_DEF) ||
       LL_DMA_IsEnabledChannel(SUBGHZ_DEVICE_CC1101_EXT_DMA_CH4_DEF) ||
       LL_DMA_IsEnabledChannel(SUBGHZ_DEVICE_CC1101_EXT_DMA_CH5_DEF)) {
        if(!furi_hal_resource_lease_v2_release(
               lease,FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX)) {
            e11_ext_tx_owner=lease;
            e11_ext_tx_fault=true;
        }
        return false;
    }
    e11_ext_tx_owner=lease;

    subghz_device_cc1101_ext->async_tx.callback = callback;""")
    s=one(s,
        """    subghz_device_cc1101_ext->async_tx.buffer =
        malloc(SUBGHZ_DEVICE_CC1101_EXT_ASYNC_TX_BUFFER_FULL * sizeof(uint32_t));

    // here we do the same things""",
        """    subghz_device_cc1101_ext->async_tx.buffer =
        malloc(SUBGHZ_DEVICE_CC1101_EXT_ASYNC_TX_BUFFER_FULL * sizeof(uint32_t));
    if(!subghz_device_cc1101_ext->async_tx.buffer) {
        /* Fail allocation before any pin/timer/DMA write; rollback
         * only the exact V2 lease that we successfully acquired.
         */
        subghz_device_cc1101_ext->state=SubGhzDeviceCC1101ExtStateIdle;
        subghz_device_cc1101_ext->async_tx.callback=NULL;
        subghz_device_cc1101_ext->async_tx.callback_context=NULL;
        if(furi_hal_resource_lease_v2_release(
               e11_ext_tx_owner,FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX)) {
            e11_ext_tx_owner=0U;
        } else {
            e11_ext_tx_fault=true;
        }
        return false;
    }

    // here we do the same things""")
    s=one(s,
        """bool subghz_device_cc1101_ext_is_async_tx_complete(void) {
    return (subghz_device_cc1101_ext->state == SubGhzDeviceCC1101ExtStateAsyncTx) &&
           (LL_TIM_GetAutoReload(TIM17) == 0);
}""",
        """bool subghz_device_cc1101_ext_is_async_tx_complete(void) {
    if(!e11_ext_tx_ready()) return false;
    return (subghz_device_cc1101_ext->state == SubGhzDeviceCC1101ExtStateAsyncTx) &&
           (LL_TIM_GetAutoReload(TIM17) == 0);
}""")
    s=one(s,
        """void subghz_device_cc1101_ext_stop_async_tx(void) {
    furi_assert(subghz_device_cc1101_ext->state == SubGhzDeviceCC1101ExtStateAsyncTx);

    // Shutdown radio""",
        """void subghz_device_cc1101_ext_stop_async_tx(void) {
    if(!e11_ext_tx_ready()) return;
    if(subghz_device_cc1101_ext->state != SubGhzDeviceCC1101ExtStateAsyncTx ||
       LL_DMA_IsEnabledChannel(SUBGHZ_DEVICE_CC1101_EXT_DMA_CH5_DEF)) {
        e11_ext_tx_fault=true;
        return;
    }

    // Shutdown radio""")
    s=one(s,
        """    furi_hal_bus_disable(FuriHalBusTIM17);
    furi_hal_interrupt_set_isr(FuriHalInterruptIdTim1TrgComTim17, NULL, NULL);

    // Deinitialize DMA""",
        """    furi_hal_bus_disable(FuriHalBusTIM17);
    /* TIM1_TRG_COM_TIM17 is a shared vector; external TX never
     * installed a handler there. Do NOT clear another owner's ISR.
     */

    // Deinitialize DMA""")
    s=one(s,
        """    LL_DMA_DeInit(SUBGHZ_DEVICE_CC1101_EXT_DMA_CH3_DEF);
    LL_DMA_DisableChannel(SUBGHZ_DEVICE_CC1101_EXT_DMA_CH4_DEF);
    furi_hal_interrupt_set_isr(SUBGHZ_DEVICE_CC1101_EXT_DMA_CH3_IRQ, NULL, NULL);""",
        """    LL_DMA_DeInit(SUBGHZ_DEVICE_CC1101_EXT_DMA_CH3_DEF);
    LL_DMA_DeInit(SUBGHZ_DEVICE_CC1101_EXT_DMA_CH4_DEF);
    furi_hal_interrupt_set_isr(SUBGHZ_DEVICE_CC1101_EXT_DMA_CH3_IRQ, NULL, NULL);""")
    # This stage refuses mirror != NULL, therefore CH5 was never
    # configured by our TX owner; do not even disable an unused channel.
    s=one(s,
        """    free(subghz_device_cc1101_ext->async_tx.buffer);

    subghz_device_cc1101_ext->state = SubGhzDeviceCC1101ExtStateIdle;
}""",
        """    free(subghz_device_cc1101_ext->async_tx.buffer);
    subghz_device_cc1101_ext->async_tx.buffer=NULL;
    subghz_device_cc1101_ext->async_tx.callback=NULL;
    subghz_device_cc1101_ext->async_tx.callback_context=NULL;
    subghz_device_cc1101_ext->state = SubGhzDeviceCC1101ExtStateIdle;
    if(furi_hal_resource_lease_v2_release(
           e11_ext_tx_owner,FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX)) {
        e11_ext_tx_owner=0U;
    } else {
        e11_ext_tx_fault=true;
    }
}""")
    return s

def main():
    p=argparse.ArgumentParser();p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args();root=a.firmware_root.resolve()
    try:
        if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()!=PIN:
            raise ValueError("Unpinned source revision")
        dirty=set()
        for line in subprocess.check_output(["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Untracked or renamed source")
            dirty.add(line[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unreviewed previous source "+repr(sorted(dirty^EXPECTED)))
        resources=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
        if "FURI_HAL_RESOURCE_LEASE_API_V2 1" not in resources or (
            "FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX" not in resources):
            raise ValueError("Missing pinned V2 composite mask prerequisite")
        before=(root/EXT).read_text(encoding="utf-8")
        after=patch(before)
        print("E11 EXT CC1101 TX DMA2 CH3/4/5 V2 SOURCE PREFLIGHT PASS")
        if a.apply:
            (root/EXT).write_text(after,encoding="utf-8")
            print("ORIGINAL EXTERNAL RADIO SOURCE ONLY; NO FLASH, SD, USB OR TRANSMIT")
        else:
            print("READ-ONLY; no file modified")
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 EXT CC1101 TX SOURCE REFUSED: "+str(e),file=sys.stderr)
        raise SystemExit(1)

if __name__=="__main__":
    main()
