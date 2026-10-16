#!/usr/bin/env python3
"""E11 NFC SignalReader TIM16 + DMA2 CH2/3/5 + DMAMUX RG0 + PA2/EXTI2.

Original pinned production sources, strict prior-diff gate. Bool START,
owned DMA ISR/STOP, status-bearing ISO15693 parser and no wait on BUSY.
No flash/device/SD/USB. Arbitrary SignalReader pins refused.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys
from patch_momentum_native_iso15693_irq_restore_busy import EXPECTED as ISO_PRE,SOURCE as NFC

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
READER="lib/signal_reader/signal_reader.c"
READER_H="lib/signal_reader/signal_reader.h"
PARSER="lib/signal_reader/parsers/iso15693/iso15693_parser.c"
PARSER_H="lib/signal_reader/parsers/iso15693/iso15693_parser.h"
EXPECTED=ISO_PRE | {NFC}
MARK="/* E11 native NFC SignalReader TIM16/DMA2/DMAMUX V2 owner. */"

def one(s,old,new):
    if s.count(old)!=1:
        raise ValueError("Pinned SignalReader/ISO source mismatch "+repr(old[:115]))
    return s.replace(old,new,1)

def patch(reader,header,parser,parser_header,nfc):
    if MARK in reader: raise ValueError("Already applied")
    if "/* E11 ISO15693 exact NFC IRQ restoration BUSY return. */" not in nfc:
        raise ValueError("NFC transparent EXIT fail-closed predecessor missing")
    reader=one(reader,"#include <furi_hal_bus.h>\n",
                   "#include <furi_hal_bus.h>\n#include <furi_hal_resources.h>\n")
    reader=one(reader,"    void* context;\n};",
        """    void* context;

    /* E11 native NFC SignalReader TIM16/DMA2/DMAMUX V2 owner. */
    uint32_t e11_owner;
    bool e11_fault;
};""")
    reader=one(reader,
        "    instance->event.data = &instance->event_data;\n",
        "    instance->event.data = &instance->event_data;\n"
        "    instance->e11_owner=0U;\n"
        "    instance->e11_fault=false;\n")
    reader=one(reader,
        """    furi_check(instance->bitstream_buffer);

    free(instance->gpio_buffer);""",
        """    furi_check(instance->bitstream_buffer);
    /* Never free buffers while an owned DMA IRQ could still reference them. */
    if(instance->e11_owner) return;

    free(instance->gpio_buffer);""")
    reader=one(reader,
        "static void furi_hal_sw_digital_pin_dma_rx_isr(void* context) {\n    SignalReader* instance = context;\n",
        """static void signal_reader_e11_exti_callback(void* context) {
    /* DMAMUX sees the EXTI edge; the CPU EXTI callback must not
     * manipulate any timer, GPIO or DMA channel.
     */
    UNUSED(context);
}
static bool signal_reader_e11_ready(SignalReader* instance) {
    if(!instance || !instance->e11_owner || instance->e11_fault) return false;
    if(!furi_hal_bus_is_enabled(FuriHalBusTIM16) ||
       !LL_DMA_IsEnabledChannel(SIGNAL_READER_DMA_GPIO_DEF) ||
       !LL_DMA_IsEnabledChannel(SIGNAL_READER_DMA_CNT_SYNC_DEF)) {
        instance->e11_fault=true;
        return false;
    }
    return true;
}
static void furi_hal_sw_digital_pin_dma_rx_isr(void* context) {
    SignalReader* instance = context;
    if(!signal_reader_e11_ready(instance)) return; /* Never touch a foreign DMA IRQ. */
""")
    reader=one(reader,
        """void signal_reader_start(SignalReader* instance, SignalReaderCallback callback, void* context) {
    furi_check(instance);
    furi_check(callback);

    instance->callback = callback;""",
        """bool signal_reader_try_start(
    SignalReader* instance, SignalReaderCallback callback, void* context) {
    if(!instance || !callback || instance->e11_owner || instance->e11_fault) return false;
    /* The sole pinned caller is ISO15693 NFC listener on internal PA2.
     * Other arbitrary GPIOs require their own exact EXTI+pin V2 masks.
     */
    if(instance->pin != &gpio_nfc_irq_rfid_pull) return false;
    const uint32_t owner=furi_hal_resource_lease_v2_try_acquire(
        FURI_HAL_LEASE_NATIVE_SIGNAL_READER_NFC);
    if(!owner) return false;
    /* Claim first; then check direct legacy users of clock, DMA2 and
     * DMAMUX generator, BEFORE callback, GPIO, timer or DMA writes.
     */
    if(furi_hal_bus_is_enabled(FuriHalBusTIM16) ||
       LL_DMA_IsEnabledChannel(SIGNAL_READER_DMA_GPIO_DEF) ||
       LL_DMA_IsEnabledChannel(SIGNAL_READER_DMA_TRIGGER_DEF) ||
       LL_DMA_IsEnabledChannel(SIGNAL_READER_DMA_CNT_SYNC_DEF) ||
       LL_DMAMUX_IsEnabledRequestGen(DMAMUX1,LL_DMAMUX_REQ_GEN_0)) {
        if(!furi_hal_resource_lease_v2_release(
               owner,FURI_HAL_LEASE_NATIVE_SIGNAL_READER_NFC)) {
            instance->e11_owner=owner;
            instance->e11_fault=true;
        }
        return false;
    }
    instance->e11_owner=owner;
    /* A foreign NFC/JS callback may not be replaced, even if its user
     * bypassed the resource allocator. Reserve exact native slot.
     */
    if(!furi_hal_gpio_try_add_int_callback(
           instance->pin,signal_reader_e11_exti_callback,instance)) {
        if(furi_hal_resource_lease_v2_release(
               owner,FURI_HAL_LEASE_NATIVE_SIGNAL_READER_NFC)) {
            instance->e11_owner=0U;
        } else {
            instance->e11_fault=true;
        }
        return false;
    }

    instance->callback = callback;""")
    reader=one(reader,
        """    LL_DMA_EnableIT_TC(SIGNAL_READER_DMA_GPIO_DEF);
    LL_DMA_EnableIT_HT(SIGNAL_READER_DMA_GPIO_DEF);
}

void signal_reader_stop(SignalReader* instance) {
    furi_check(instance);

    furi_hal_interrupt_set_isr(SIGNAL_READER_DMA_GPIO_IRQ, NULL, NULL);

    furi_hal_gpio_disable_int_callback(instance->pin);

    // Deinit DMA Rx pin
    LL_DMA_DeInit(SIGNAL_READER_DMA_GPIO_DEF);
    // Deinit DMA Sync timer
    LL_DMA_DeInit(SIGNAL_READER_DMA_CNT_SYNC_DEF);
    // Deinit DMA Trigger timer
    LL_DMA_DeInit(SIGNAL_READER_DMA_TRIGGER_DEF);

    furi_hal_bus_disable(FuriHalBusTIM16);
}""",
        """    LL_DMA_EnableIT_TC(SIGNAL_READER_DMA_GPIO_DEF);
    LL_DMA_EnableIT_HT(SIGNAL_READER_DMA_GPIO_DEF);
    return true;
}

/* Preserve existing ABI, but upper ISO15693 caller consumes bool TRY. */
void signal_reader_start(SignalReader* instance, SignalReaderCallback callback, void* context) {
    (void)signal_reader_try_start(instance,callback,context);
}

void signal_reader_stop(SignalReader* instance) {
    furi_check(instance);
    if(!signal_reader_e11_ready(instance)) return;
    if(!furi_hal_gpio_try_remove_int_callback(
           instance->pin,signal_reader_e11_exti_callback,instance)) {
        instance->e11_fault=true;
        return;
    }
    /* Detach own ISR and disable request generator FIRST. Original STOP
     * previously left DMAMUX RG0 active after DMA2 teardown.
     */
    furi_hal_interrupt_set_isr(SIGNAL_READER_DMA_GPIO_IRQ,NULL,NULL);
    LL_DMAMUX_DisableRequestGen(DMAMUX1,LL_DMAMUX_REQ_GEN_0);
    LL_DMA_DeInit(SIGNAL_READER_DMA_GPIO_DEF);
    LL_DMA_DeInit(SIGNAL_READER_DMA_CNT_SYNC_DEF);
    LL_DMA_DeInit(SIGNAL_READER_DMA_TRIGGER_DEF);
    furi_hal_bus_disable(FuriHalBusTIM16);
    furi_hal_gpio_init(instance->pin,GpioModeAnalog,GpioPullNo,GpioSpeedLow);
    instance->callback=NULL;
    instance->context=NULL;
    if(furi_hal_resource_lease_v2_release(
           instance->e11_owner,FURI_HAL_LEASE_NATIVE_SIGNAL_READER_NFC)) {
        instance->e11_owner=0U;
    } else {
        instance->e11_fault=true; /* Sticky failed release, no reuse. */
    }
}""")
    header=one(header,
        "void signal_reader_start(SignalReader* instance, SignalReaderCallback callback, void* context);",
        "/* E11 atomic owned bool start for NFC PA2/EXTI2 transparent listener. */\n"
        "bool signal_reader_try_start(SignalReader* instance, SignalReaderCallback callback, void* context);\n"
        "void signal_reader_start(SignalReader* instance, SignalReaderCallback callback, void* context);")
    parser=one(parser,
        """static void iso15693_parser_start_signal_reader(Iso15693Parser* instance) {
    iso15693_parser_reset(instance);
    signal_reader_start(instance->signal_reader, signal_reader_callback, instance);
}

void iso15693_parser_start(
    Iso15693Parser* instance,
    Iso15693ParserCallback callback,
    void* context) {
    furi_assert(instance);
    furi_assert(callback);

    instance->callback = callback;
    instance->context = context;
    iso15693_parser_start_signal_reader(instance);
}""",
        """static bool iso15693_parser_start_signal_reader(Iso15693Parser* instance) {
    iso15693_parser_reset(instance);
    return signal_reader_try_start(instance->signal_reader,signal_reader_callback,instance);
}

bool iso15693_parser_try_start(
    Iso15693Parser* instance,Iso15693ParserCallback callback,void* context) {
    if(!instance || !callback) return false;
    instance->callback=callback;
    instance->context=context;
    if(!iso15693_parser_start_signal_reader(instance)) {
        instance->callback=NULL;
        instance->context=NULL;
        return false;
    }
    return true;
}

/* Retain existing legacy parser void ABI. */
void iso15693_parser_start(
    Iso15693Parser* instance,Iso15693ParserCallback callback,void* context) {
    (void)iso15693_parser_try_start(instance,callback,context);
}""")
    parser_header=one(parser_header,
        "void iso15693_parser_start(\n",
        "/* E11: status-bearing DMA SignalReader acquisition. */\n"
        "bool iso15693_parser_try_start(\n"
        "    Iso15693Parser* instance,Iso15693ParserCallback callback,void* context);\n"
        "void iso15693_parser_start(\n")
    nfc=one(nfc,
        """    iso15693_parser_start(
        furi_hal_nfc_iso15693_listener->parser, furi_hal_nfc_iso15693_parser_callback, thread_id);

    while(true) {""",
        """    if(!iso15693_parser_try_start(
           furi_hal_nfc_iso15693_listener->parser,furi_hal_nfc_iso15693_parser_callback,
           thread_id)) {
        /* The existing NFC HAL event ABI has no resource-BUSY event bit.
         * Signal a non-RX abort and log the true reason, never enter
         * receive wait or STOP a foreign DMAMUX/TIM16 resource.
         */
        FURI_LOG_W(TAG,"ISO15693 SignalReader TIM16/DMA2/EXTI BUSY");
        return FuriHalNfcEventAbortRequest;
    }

    while(true) {""")
    return reader,header,parser,parser_header,nfc

def main():
    p=argparse.ArgumentParser()
    p.add_argument("firmware_root",type=Path)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args();root=a.firmware_root.resolve()
    try:
        if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()!=PIN:
            raise ValueError("Unpinned Momentum")
        dirty=set()
        for line in subprocess.check_output(["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(line)<4 or line[:2]=="??" or "->" in line:
                raise ValueError("Untracked/renamed native source")
            dirty.add(line[3:])
        if dirty!=EXPECTED:
            raise ValueError("Unreviewed native files "+repr(sorted(dirty^EXPECTED)))
        check=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
        if "#define FURI_HAL_RESOURCE_LEASE_API_V2 1" not in check:
            raise ValueError("Missing actual matched V2 DMA/DMAMUX allocator")
        paths=(READER,READER_H,PARSER,PARSER_H,NFC)
        old=[(root/p).read_text(encoding="utf-8") for p in paths]
        new=patch(*old)
        print("E11 NFC SIGNALREADER V2 DRIVER+PARSER+LISTENER SOURCE PREFLIGHT PASS")
        if a.apply:
            for p,s in zip(paths,new): (root/p).write_text(s,encoding="utf-8")
            print("SOURCE PATCH ONLY; NO FLASH/SD/USB")
        else:
            print("READ ONLY; NO MODIFICATIONS")
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 SIGNALREADER SOURCE REFUSED: "+str(e),file=sys.stderr)
        raise SystemExit(1)

if __name__=="__main__":
    main()
