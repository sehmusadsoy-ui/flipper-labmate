#!/usr/bin/env python3
"""Source-ground EXTI2/DMA2 channel mapping and listener handoff audit.

A passing audit proves dependency discovery only, not SignalReader
ownership, hardware safety or physical ISO15693 acceptance.
"""
from __future__ import annotations
import argparse
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument("root",type=Path)
    root=p.parse_args().root.resolve()
    reader=(root/"lib/signal_reader/signal_reader.c").read_text()
    parser=(root/"lib/signal_reader/parsers/iso15693/iso15693_parser.c").read_text()
    listener=(root/"targets/f7/furi_hal/furi_hal_nfc_iso15693.c").read_text()
    resources=(root/"targets/f7/furi_hal/furi_hal_resources.h").read_text()
    ext=(root/"applications/drivers/subghz/cc1101_ext/cc1101_ext.c").read_text()
    expected=(
        "#define SIGNAL_READER_CAPTURE_TIM         (TIM16)",
        "#define SIGNAL_READER_DMA_GPIO     LL_DMA_CHANNEL_2",
        "#define SIGNAL_READER_DMA_TRIGGER     LL_DMA_CHANNEL_3",
        "#define SIGNAL_READER_DMA_CNT_SYNC     LL_DMA_CHANNEL_5",
        "LL_DMAMUX_REQ_GEN_0",
        "void signal_reader_start(",
        "void signal_reader_stop(",
        "LL_DMA_DeInit(SIGNAL_READER_DMA_GPIO_DEF);",
        "LL_DMA_DeInit(SIGNAL_READER_DMA_TRIGGER_DEF);",
        "LL_DMA_DeInit(SIGNAL_READER_DMA_CNT_SYNC_DEF);",
    )
    for term in expected:
        assert term in reader, f"SignalReader source drift: {term}"
    assert "signal_reader_start(instance->signal_reader" in parser
    assert "signal_reader_stop(instance->signal_reader);" in parser
    assert "iso15693_parser_alloc(&gpio_nfc_irq_rfid_pull," in listener
    assert "furi_hal_nfc_deinit_gpio_isr();" in listener
    assert "/* E11 ISO15693 exact NFC IRQ restoration BUSY return. */" in listener
    assert "furi_hal_nfc_try_init_gpio_isr();" in listener
    assert "return e11_irq_restored ? FuriHalNfcErrorNone : FuriHalNfcErrorBusy;" in listener
    assert "FURI_HAL_LEASE_NATIVE_SIGNAL_READER_NFC" in resources
    assert "FURI_HAL_LEASE_NATIVE_EXT_CC1101_TX" in resources
    for k in ("LL_DMA_CHANNEL_3","LL_DMA_CHANNEL_4","LL_DMA_CHANNEL_5"):
        assert k in ext, f"External TX expected DMA channel absent: {k}"
    assert reader.index("furi_hal_gpio_init(") < reader.index(
        "LL_DMAMUX_SetRequestSignalID(")
    assert reader.index("LL_DMAMUX_EnableRequestGen(") < reader.index(
        "void signal_reader_stop(")
    stop=reader[reader.index("void signal_reader_stop("):]
    assert "LL_DMAMUX_DisableRequestGen" not in stop, (
        "SignalReader teardown changed: require new original C/ISR safety gate")
    assert "furi_hal_resource_lease_v2_try_acquire" not in reader, (
        "SignalReader migrated: replace this pre-migration audit with native-C fault tests")
    print("E11 pinned SignalReader/NFC handoff/DMA2 source CONTRACT DISCOVERY PASS")
    print("SIGNALREADER OWNERSHIP STILL OPEN: no V2 claim, no DMA2 RG0 STOP, no bool START")

if __name__=="__main__":
    main()
