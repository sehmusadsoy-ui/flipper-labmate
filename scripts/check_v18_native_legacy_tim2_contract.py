#!/usr/bin/env python3
"""E11 legacy-native TIM2 risk contract; fail on changed pinned source footprint.

Audit only: DigitalSequence plus RFID READ/CAPTURE/EMULATE/FIELD
native stages are reviewed; SubGHz remains a direct TIM2/DMA bypass
remain native/direct HAL bypasses. No silent void-start veto.
This is a negative safety gate, NOT firmware-global arbitration.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

PINNED="d3f89dfe2ef6b01839201598e9be1590cba80322"
ROOTS={
 "subghz":"targets/f7/furi_hal/furi_hal_subghz.c",
 "rfid":"targets/f7/furi_hal/furi_hal_rfid.c",
 "digital":"lib/digital_signal/digital_sequence.c",
 "bus":"targets/f7/furi_hal/furi_hal_bus.c",
}
EXPECTED={
 "subghz":(
    "furi_hal_subghz_start_async_rx(",
    "furi_hal_subghz_stop_async_rx(",
    "furi_hal_subghz_start_async_tx(",
    "furi_hal_subghz_stop_async_tx(",
    "furi_hal_bus_enable(FuriHalBusTIM2)",
    "furi_hal_bus_disable(FuriHalBusTIM2)",
    "LL_TIM_Init(TIM2",
    "SubGhzStateAsyncRx",
 ),
 "rfid":(
    "#define FURI_HAL_RFID_EMULATE_TIMER_BUS     FuriHalBusTIM2",
    "#define RFID_CAPTURE_TIM_BUS FuriHalBusTIM2",
    "#define FURI_HAL_RFID_FIELD_COUNTER_TIMER_BUS     FuriHalBusTIM2",
    "#define FURI_HAL_RFID_READ_TIMER_BUS            FuriHalBusTIM1",
    "#define FURI_HAL_RFID_FIELD_TIMEOUT_TIMER_BUS FuriHalBusTIM1",
 ),
 "digital":(
    "static inline void digital_sequence_start_timer(void)",
    "static void digital_sequence_stop_timer(void)",
    "furi_hal_bus_enable(FuriHalBusTIM2)",
    "furi_hal_bus_disable(FuriHalBusTIM2)",
    "LL_DMA_DisableChannel(DMA1, LL_DMA_CHANNEL_1)",
 ),
 "bus":(
    "[FuriHalBusTIM2] = LL_APB1_GRP1_PERIPH_TIM2",
    "[FuriHalBusTIM1] = LL_APB2_GRP1_PERIPH_TIM1",
    "void furi_hal_bus_enable(",
    "void furi_hal_bus_disable(",
 ),
}

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("momentum_root",type=Path)
    ap.add_argument("labmate_root",type=Path)
    a=ap.parse_args()
    root=a.momentum_root.resolve()
    dev=a.labmate_root.resolve()
    try:
        head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
            text=True).strip()
        if head!=PINNED:
            raise ValueError("Pinned Momentum commit mismatch")
        changed=subprocess.check_output(
            ["git","-C",str(root),"diff","--name-only","HEAD"],text=True).splitlines()
        for role,path in ROOTS.items():
            if path in changed and role not in ("digital","rfid","subghz"):
                raise ValueError(f"Unreviewed critical native driver changed: {path}")
        for role,path in ROOTS.items():
            src=(root/path).read_text(encoding="utf-8")
            for signature in EXPECTED[role]:
                if signature not in src:
                    raise ValueError(f"{role}: legacy hardware control changed: {signature}")
            if role=="digital" and path in changed:
                if ("/* LabMate E11 native DigitalSequence owner. */" not in src or
                    "digital_sequence_e11_claim(sequence)" not in src or
                    "digital_sequence_e11_release(sequence)" not in src or
                    "sequence->e11_lease_fault = true;" not in src):
                    raise ValueError("digital_sequence changed without verified lease lifecycle")
                if src.index("digital_sequence_e11_claim(sequence)") > src.index(
                    "furi_hal_gpio_init(sequence->gpio, GpioModeOutputPushPull"):
                    raise ValueError("digital_sequence claims AFTER GPIO changes")
                print("E11 NATIVE DIGITAL: TIM2/DMA cooperative lifecycle SOURCE VERIFIED")
            elif role=="rfid" and path in changed:
                if ("/* E11 native RFID read TIM1 owner. */" not in src or
                    "bool furi_hal_rfid_tim_read_try_start(" not in src or
                    "furi_hal_rfid_tim_read_stop(void)" not in src or
                    "/* E11 native RFID capture TIM2 owner. */" not in src or
                    "bool furi_hal_rfid_tim_read_capture_try_start(" not in src or
                    "/* E11 native RFID emulate TIM2/DMA2 composite owner. */" not in src or
                    "bool furi_hal_rfid_tim_emulate_dma_try_start(" not in src or
                    "/* E11 native RFID field atomic TIM1/TIM2/DMA2 owner. */" not in src or
                    "bool furi_hal_rfid_field_detect_try_start(void)" not in src or
                    src.count("furi_hal_resource_lease_try_acquire(")!=4):
                    raise ValueError("RFID changes exceed READ/CAPTURE/EMULATE/FIELD reviewed modes")
                read=src[src.index("bool furi_hal_rfid_tim_read_try_start("):
                         src.index("static void furi_hal_rfid_tim_emulate(void)")]
                if (read.index("furi_hal_resource_lease_try_acquire(") >
                    read.index("furi_hal_rfid_pins_read();")):
                    raise ValueError("RFID READ claim occurs after GPIO mutation")
                capture=src[src.index("bool furi_hal_rfid_tim_read_capture_try_start("):
                            src.index("static void furi_hal_rfid_dma_isr(void* context)")]
                if (capture.index("furi_hal_resource_lease_try_acquire(") >
                    capture.index("furi_hal_rfid->read_capture_callback = callback;") or
                    capture.index("furi_hal_resource_lease_try_acquire(") >
                    capture.index("furi_hal_bus_enable(RFID_CAPTURE_TIM_BUS);") or
                    capture.count("if(!e11_rfid_capture_ready()) return;") < 1 or
                    "if(!e11_rfid_capture_ready()) return;" not in src or
                    "e11_rfid_capture_fault = true;" not in src):
                    raise ValueError("RFID CAPTURE TIM2 claim/IRQ/STOP guard missing")
                emulate=src[src.index("bool furi_hal_rfid_tim_emulate_dma_try_start("):
                            src.index("void furi_hal_rfid_set_read_period(uint32_t period) {")]
                if (emulate.index("furi_hal_resource_lease_try_acquire(") >
                    emulate.index("furi_hal_rfid_pins_emulate();") or
                    emulate.index("furi_hal_resource_lease_try_acquire(") >
                    emulate.index("furi_hal_rfid->dma_callback = callback;") or
                    "LL_DMA_IsEnabledChannel(RFID_DMA_CH1_DEF)" not in emulate or
                    "LL_DMA_IsEnabledChannel(RFID_DMA_CH2_DEF)" not in emulate or
                    "if(!e11_rfid_emulate_ready()) return;" not in src or
                    "e11_rfid_emulate_fault=true;" not in src):
                    raise ValueError("RFID EMULATE TIM2/DMA2 claim/ISR/STOP guard missing")
                field=src[src.index("bool furi_hal_rfid_field_detect_try_start(void)"):]
                if (field.index("furi_hal_resource_lease_try_acquire(") >
                    field.index("furi_hal_rfid_pins_field();") or
                    field.index("furi_hal_resource_lease_try_acquire(") >
                    field.index("furi_hal_rfid_field_tim_setup();") or
                    "FURI_HAL_LEASE_NATIVE_RFID_FIELD" not in field or
                    "if(!e11_rfid_field_ready()) return;" not in field or
                    "if(!e11_rfid_field_ready()) {" not in field or
                    "LL_TIM_DisableIT_UPDATE(FURI_HAL_RFID_FIELD_TIMEOUT_TIMER);" not in field or
                    "*frequency=0U;" not in field):
                    raise ValueError("Unreviewed RFID FIELD TIM1/TIM2/DMA2 safety contract")
                if ("if(!e11_rfid_read_ready()) return;" not in src or
                    "e11_rfid_read_fault=true;" not in src or
                    "furi_hal_bus_enable(RFID_CAPTURE_TIM_BUS)" not in src or
                    "furi_hal_bus_enable(FURI_HAL_RFID_EMULATE_TIMER_BUS)" not in src or
                    "furi_hal_bus_enable(FURI_HAL_RFID_FIELD_COUNTER_TIMER_BUS)" not in src):
                    raise ValueError("RFID read guard or still-unmigrated modes changed")
                print("E11 RFID READ/CAPTURE/EMULATE/FIELD cooperative SOURCE VERIFIED; SUBGHZ TX OPEN")
            elif role=="subghz" and path in changed:
                if ("/* E11 native SubGHz RX TIM2 cooperative owner. */" not in src or
                    "bool furi_hal_subghz_async_rx_try_start(" not in src or
                    "e11_subghz_rx_mask_for_mirror" not in src or
                    "if(!e11_subghz_rx_ready()) return;" not in src or
                    src.count("furi_hal_resource_lease_try_acquire(")!=2 or
                    "/* E11 native SubGHz TX TIM2/DMA2 lease owner. */" not in src or
                    "e11_subghz_rx_fault=true;" not in src or
                    "e11_subghz_tx_fault=true;" not in src):
                    raise ValueError("SubGHz RX lease/ISR/STOP guard unreviewed")
                rx=src[src.index("bool furi_hal_subghz_async_rx_try_start("):
                       src.index("typedef enum {\n    FuriHalSubGhzAsyncTxMiddlewareStateIdle")]
                if (rx.index("furi_hal_resource_lease_try_acquire(") >
                    rx.index("furi_hal_subghz_capture_callback = callback;") or
                    rx.index("furi_hal_resource_lease_try_acquire(") >
                    rx.index("furi_hal_gpio_init_ex(") or
                    rx.index("furi_hal_resource_lease_try_acquire(") >
                    rx.index("furi_hal_subghz_rx();")):
                    raise ValueError("SubGHz RX claim occurs after hardware side effect")
                tx=src[src.index("bool furi_hal_subghz_start_async_tx("):]
                if (tx.index("furi_hal_resource_lease_try_acquire(") >
                    tx.index("furi_hal_subghz_async_tx.callback = callback;") or
                    tx.index("furi_hal_resource_lease_try_acquire(") >
                    tx.index("furi_hal_gpio_init_ex(") or
                    "FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_BASE" not in tx or
                    "FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PA7" not in src or
                    "FURI_HAL_LEASE_NATIVE_SUBGHZ_TX_MIRROR_PB3" not in src or
                    "LL_DMA_IsEnabledChannel(SUBGHZ_DMA_CH1_DEF)" not in tx or
                    "if(!e11_subghz_tx_ready()) return;" not in src or
                    "(void)e11_subghz_tx_release();" not in src):
                    raise ValueError("Native SubGHz TX composite TIM2/DMA2 guard missing")
                if ("e11_subghz_tx_handle || e11_subghz_tx_fault" not in src or
                    "e11_subghz_rx_handle || e11_subghz_rx_fault" not in src):
                    raise ValueError("Debug mirror setter can switch during active owner")
                print("E11 native SubGHz RX TIM2 + TX TIM2/DMA2 source VERIFIED; mirror/physical OPEN")
            else:
                if "furi_hal_resource_lease_try_acquire(" in src:
                    raise ValueError(f"{role}: unreviewed native lease migration")
                print(f"E11 LEGACY {role.upper()}: TIM footprint VERIFIED, but UNCOORDINATED")
        tim2=(dev/"src/labmate_frequency_tim2.c").read_text(encoding="utf-8")
        counter=(dev/"src/labmate_event_counter.c").read_text(encoding="utf-8")
        measurement=(dev/"src/labmate_measurements.c").read_text(encoding="utf-8")
        before=tim2.index("bool labmate_frequency_tim2_configure(")
        after=tim2.index("/* Keep the v1.6.1 TIM2_CH2")
        prepare=tim2[before:after]
        if ("furi_hal_bus_is_enabled(FuriHalBusTIM2)" not in prepare or
            "furi_hal_resource_lease_release(lease," not in prepare or
            "return false;" not in prepare):
            raise ValueError("Counter no longer denies pre-enabled TIM2 before writes")
        if (tim2.index("labmate_frequency_tim2_capture_valid(void)") >
            tim2.index("void labmate_frequency_tim2_shutdown(void)")):
            raise ValueError("Counter health guard not defined before STOP")
        if "if(!labmate_frequency_tim2_capture_valid()) return;" not in tim2:
            raise ValueError("Counter control no longer checks owner/clock health")
        if "if(!labmate_frequency_tim2_capture_valid())" not in counter:
            raise ValueError("Counter poll may convert guarded zero into wrapped edges")
        if "if(!labmate_frequency_tim2_capture_valid())" not in measurement:
            raise ValueError("HIGH frequency mode may publish invalid TIM2 rate")
        print("E11 LOCAL TIM2 LEGACY-ENABLED DENIAL + HEALTH-GUARD SOURCE PASS")
        print("E11 GLOBAL RADIO/RFID/TIM2 CONCURRENCY REMAINS OPEN: void HAL")
        print("API + native direct registers cannot be safely intercepted here.")
        print("NO CORE HAL PATCH, NO FLASH, NO DEVICE/SD MODIFICATIONS.")
        return 0
    except (OSError,subprocess.CalledProcessError,ValueError) as e:
        print("E11 LEGACY TIM2 SAFETY CONTRACT REFUSED: "+str(e),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
