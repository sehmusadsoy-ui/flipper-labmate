#!/usr/bin/env python3
"""E11 legacy-native TIM2 risk contract; fail on changed pinned source footprint.

Audit only: DigitalSequence and RFID read TIM1 are explicitly
reviewed cooperating native owners; other RFID modes and SubGHz
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
            if path in changed and role not in ("digital","rfid"):
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
                    src.count("furi_hal_resource_lease_try_acquire(")!=1):
                    raise ValueError("RFID source changes exceed one reviewed READ TIM1 owner")
                read=src[src.index("bool furi_hal_rfid_tim_read_try_start("):
                         src.index("static void furi_hal_rfid_tim_emulate(void)")]
                if (read.index("furi_hal_resource_lease_try_acquire(") >
                    read.index("furi_hal_rfid_pins_read();")):
                    raise ValueError("RFID READ claim occurs after GPIO mutation")
                if ("if(!e11_rfid_read_ready()) return;" not in src or
                    "e11_rfid_read_fault=true;" not in src or
                    "furi_hal_bus_enable(RFID_CAPTURE_TIM_BUS)" not in src or
                    "furi_hal_bus_enable(FURI_HAL_RFID_EMULATE_TIMER_BUS)" not in src or
                    "furi_hal_bus_enable(FURI_HAL_RFID_FIELD_COUNTER_TIMER_BUS)" not in src):
                    raise ValueError("RFID read guard or still-unmigrated modes changed")
                print("E11 RFID READ TIM1 cooperative SOURCE VERIFIED; capture/emulate/field UNCOORDINATED")
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
