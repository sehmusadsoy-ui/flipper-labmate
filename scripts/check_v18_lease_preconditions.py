#!/usr/bin/env python3
"""Read-only E11 contract preconditions for pinned Momentum source.

SUCCESS means known ASSERT/lease gaps were reproduced in source,
NOT that global ownership is protected on-device. Any upstream HAL
change must be reviewed instead of silently accepted.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess

PINNED_MOMENTUM = "d3f89dfe2ef6b01839201598e9be1590cba80322"

def read(root: Path, name: str) -> str:
    return (root / name).read_text(encoding="utf-8")

def check(cond: bool, message: str) -> None:
    if not cond:
        raise RuntimeError("PINNED OWNER CONTRACT AUDIT REFUSED: " + message)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("momentum_root", type=Path)
    parser.add_argument("--labmate-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    fw = args.momentum_root.resolve()
    lm = args.labmate_root.resolve()

    revision = subprocess.check_output(
        ["git", "-C", str(fw), "rev-parse", "HEAD"], text=True).strip()
    check(revision == PINNED_MOMENTUM, "unexpected Momentum HEAD " + revision)

    bus = read(fw, "targets/f7/furi_hal/furi_hal_bus.c")
    gpio = read(fw, "targets/f7/furi_hal/furi_hal_gpio.c")
    pwm = read(fw, "targets/f7/furi_hal/furi_hal_pwm.c")
    tim2 = read(lm, "src/labmate_frequency_tim2.c")
    btn = read(lm, "src/labmate_button_capture.c")
    gen = read(lm, "src/labmate_generator.c")

    check("void furi_hal_bus_enable(FuriHalBus bus)" in bus,
          "TIM bus-enable code moved")
    check("furi_check(FURI_HAL_BUS_IS_PERIPH_DISABLED(APB1, value, 1))" in bus,
          "TIM2 HAL clock assertion contract changed")
    check("furi_check(FURI_HAL_BUS_IS_PERIPH_DISABLED(APB2, value))" in bus,
          "TIM1 HAL clock assertion contract changed")
    check("furi_check(gpio_interrupt[pin_num].callback == NULL)" in gpio,
          "EXTI callback-add assertion contract changed")
    check("void furi_hal_pwm_start(FuriHalPwmOutputId channel" in pwm and
          "furi_hal_bus_enable(FuriHalBusTIM1)" in pwm,
          "TIM1 HAL config path changed")
    check("furi_hal_bus_enable(FuriHalBusTIM2)" in tim2 and
          "LL_TIM_Init(TIM2" in tim2,
          "LabMate direct TIM2 access changed")
    check("furi_hal_gpio_add_int_callback(pin," in btn,
          "LabMate EXTI callback install path changed")
    check("furi_hal_pwm_start(" in gen,
          "LabMate hardware PWM driver path changed")

    print("E11 PINNED-SOURCE AUDIT PASS: source hazard assumptions confirmed.")
    print("HAL TIM1/TIM2 bus enable and EXTI callback-add are asserting APIs.")
    print("They do NOT provide an atomic cross-firmware lease + BUSY status.")
    print("E11 FIRMWARE-WIDE OWNERSHIP: OPEN, NOT DEVICE PASS, NO FLASH.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
