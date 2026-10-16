#!/usr/bin/env python3
"""E11 legacy-native TIM2 risk contract; fail on changed pinned source footprint.

Intentionally DOES NOT patch RFID/SubGHz/digital_sequence: their public APIs
and state machines must not silently skip void-return timer starts. This is
a source-verified *negative safety gate*, NOT global native arbitration.
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
    "#define FURI_HAL_RFID_FIELD_COUNTER_TIMER_BUS FuriHalBusTIM2",
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
        for path in ROOTS.values():
            if path in changed:
                raise ValueError(f"Unreviewed critical native driver changed: {path}")
        for role,path in ROOTS.items():
            src=(root/path).read_text(encoding="utf-8")
            for signature in EXPECTED[role]:
                if signature not in src:
                    raise ValueError(f"{role}: legacy hardware control changed: {signature}")
            if "furi_hal_resource_lease_try_acquire(" in src:
                raise ValueError(f"{role}: new cooperative migration requires independent review")
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
