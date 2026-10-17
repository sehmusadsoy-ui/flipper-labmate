#!/usr/bin/env python3
"""Pinned native direct LL EXTI/timer + native SPI/UART DMA channel audit.

This is a NEGATIVE regression gate. It does not magically lease every
firmware GPIO or certify on-device concurrency. Reserved RTC/clock/comparator
EXTI lines 17/18/20 are independent of user GPIO EXTI0..15.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import subprocess
import sys

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
GPIO="targets/f7/furi_hal/furi_hal_gpio.c"
CLOCK="targets/f7/furi_hal/furi_hal_clock.c"
RTC="targets/f7/furi_hal/furi_hal_rtc.c"
RFID="targets/f7/furi_hal/furi_hal_rfid.c"
INPUT="applications/services/input/input.c"
SPI="targets/f7/furi_hal/furi_hal_spi.c"
SERIAL="targets/f7/furi_hal/furi_hal_serial.c"
EXTI_OWNER={GPIO, CLOCK, RTC, RFID}
RESERVED={CLOCK:"18",RTC:"17",RFID:"20"}
DIRECT_TIMERS={
    "lib/pulse_reader/pulse_reader.c":{"TIM2"},
    "lib/digital_signal/digital_sequence.c":{"TIM2"},
    "targets/f7/furi_hal/furi_hal_subghz.c":{"TIM2"},
    "targets/f7/furi_hal/furi_hal_pwm.c":{"TIM1"},
    "applications/drivers/subghz/cc1101_ext/cc1101_ext.c":{"TIM17"},
}
CALL=re.compile(r"\bLL_EXTI_(EnableIT|DisableIT)_0_31\s*\(\s*([^)]*)\s*\)",re.S)
TIMER_CALL=re.compile(r"\bLL_TIM_EnableCounter\s*\(\s*(TIM1|TIM2|TIM17)\s*\)")

def grep(root:Path,regex:str)->set[str]:
    found=subprocess.run(["git","-C",str(root),"grep","-l","-E",regex,
                          "--","*.c","*.cpp"],text=True,capture_output=True)
    if found.returncode not in (0,1):
        raise ValueError("Native source inventory git grep failed "+found.stderr)
    return set(found.stdout.splitlines())

def check(root:Path):
    head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if head!=PIN: raise ValueError("Unexpected pinned Momentum revision")
    sensitive=(INPUT,CLOCK,RTC,SPI,SERIAL)
    dirty=set(subprocess.check_output(
        ["git","-C",str(root),"diff","--name-only","HEAD"],text=True).splitlines())
    if dirty.intersection(sensitive):
        raise ValueError("Unreviewed reserved input/clock/RTC/native SPI/serial source mutation")
    actual=grep(root,"LL_EXTI_(EnableIT|DisableIT)_0_31")
    if actual!=EXTI_OWNER:
        raise ValueError("Direct EXTI register mutation requires review: "+
                         repr(sorted(actual^EXTI_OWNER)))
    for file in sorted(actual):
        source=(root/file).read_text(encoding="utf-8")
        calls=list(CALL.finditer(source))
        if not calls: raise ValueError("Unparsed direct EXTI calls in "+file)
        if file in RESERVED:
            target="LL_EXTI_LINE_"+RESERVED[file]
            if any(m.group(2).strip()!=target for m in calls):
                raise ValueError("System EXTI source now changes GPIO-shared EXTI: "+file)
            print(file+": RESERVED peripheral EXTI line "+RESERVED[file])
        else:
            if ("bool furi_hal_gpio_try_add_int_callback(" not in source or
                "bool furi_hal_gpio_try_remove_int_callback(" not in source):
                raise ValueError("GPIO EXTI source missing native E11 callback CAS")
            print(file+": GPIO EXTI0..15 callback broker + E11 compare/add/remove")
    direct=grep(root,"LL_TIM_EnableCounter")
    for file in sorted(DIRECT_TIMERS):
        src=(root/file).read_text(encoding="utf-8")
        timers=set(TIMER_CALL.findall(src))
        if timers!=DIRECT_TIMERS[file]:
            raise ValueError("Direct user timer source changed "+file+": "+repr(timers))
        if file not in direct: raise ValueError("Expected direct timer source disappeared: "+file)
        print(file+": reviewed direct timer "+",".join(sorted(timers)))
    for file in sorted(direct-DIRECT_TIMERS.keys()):
        src=(root/file).read_text(encoding="utf-8")
        unknown=set(TIMER_CALL.findall(src))
        if unknown:
            raise ValueError("Unreviewed TIM1/TIM2/TIM17 direct counter: "+file+" "+repr(unknown))
    # Disjoint native infrastructure DMA paths, NOT shared with LabMate's
    # E11 TIM/DMA1 CH1/2 or external CC1101/SignalReader DMA2 CH1..5.
    spi=(root/SPI).read_text(encoding="utf-8")
    serial=(root/SERIAL).read_text(encoding="utf-8")
    for marker in ("#define SPI_DMA            DMA2",
                   "#define SPI_DMA_RX_CHANNEL LL_DMA_CHANNEL_6",
                   "#define SPI_DMA_TX_CHANNEL LL_DMA_CHANNEL_7"):
        if marker not in spi: raise ValueError("Native SPI DMA channel mapping changed")
    for marker in ("#define FURI_HAL_SERIAL_USART_DMA_INSTANCE (DMA1)",
                   "#define FURI_HAL_SERIAL_USART_DMA_CHANNEL  (LL_DMA_CHANNEL_6)",
                   "#define FURI_HAL_SERIAL_LPUART_DMA_INSTANCE (DMA1)",
                   "#define FURI_HAL_SERIAL_LPUART_DMA_CHANNEL  (LL_DMA_CHANNEL_7)"):
        if marker not in serial:
            raise ValueError("Native serial DMA channel mapping changed")
    if "furi_hal_gpio_add_int_callback(input_pins[i].gpio, input_isr, thread_id);" not in (
        root/INPUT).read_text(encoding="utf-8"):
        raise ValueError("Reserved Momentum STOP/BACK input IRQ registration changed")
    print("Native SPI DMA2 CH6/7, USART/LPUART DMA1 CH6/7 DISJOINT mapping PASS")
    print("System input and RTC/clock/comparator EXTI 17/18/20 unchanged PASS")
    print("E11 direct EXTI broker and enumerated TIM1/TIM2/TIM17 source audit PASS")
    print("OPEN: unknown dynamic LL aliases, optional mirror GPIO, external v1 old plugin uncertainty and physical recovery")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("firmware_root",type=Path)
    opts=ap.parse_args()
    try:
        check(opts.firmware_root.resolve())
    except (OSError,ValueError,subprocess.CalledProcessError) as e:
        print("E11 direct LL boundary refused: "+str(e),file=sys.stderr)
        raise SystemExit(1)

if __name__=="__main__":
    main()
