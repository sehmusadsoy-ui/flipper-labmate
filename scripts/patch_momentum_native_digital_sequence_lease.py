#!/usr/bin/env python3
"""E11 native DigitalSequence TIM2/DMA1_CH1/CH2 cooperative owner migration.

Pinned Momentum source, prepatched by I2C + E11 resource/EXTI/native PWM,
JS and PulseReader stages. NO device access or firmware flashing.
This protects cooperative timer and external-pin owners; RFID/SubGHz
and other direct-register drivers still need independent migration.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

PINNED = "d3f89dfe2ef6b01839201598e9be1590cba80322"
HEADER = "targets/f7/furi_hal/furi_hal_resources.h"
RESOURCE = "targets/f7/furi_hal/furi_hal_resources.c"
DIGITAL = "lib/digital_signal/digital_sequence.c"
EXPECTED_DIRTY = {
    "targets/furi_hal_include/furi_hal_i2c.h",
    "targets/f7/furi_hal/furi_hal_i2c.c",
    "targets/f7/furi_hal/furi_hal_resources.h",
    "targets/f7/furi_hal/furi_hal_resources.c",
    "targets/f7/furi_hal/furi_hal_gpio.h",
    "targets/f7/furi_hal/furi_hal_gpio.c",
    "targets/f7/furi_hal/furi_hal_pwm.c",
    "targets/f7/api_symbols.csv",
    "applications/system/js_app/modules/js_gpio.c",
    "lib/pulse_reader/pulse_reader.c",
}
MARKER = "/* LabMate E11 native DigitalSequence owner. */"

MASKS = """/* Native digital_sequence outputs DMA1 ch1+2 through TIM2.
 * GPIO alias coverage is limited to the eight external connector pins.
 * DMA1 channels are distinct from native PulseReader's ch4/5.
 */
enum {
    FuriHalLeaseDma1Ch1 = (1U << 22),
    FuriHalLeaseDma1Ch2 = (1U << 23),
};
#define FURI_HAL_LEASE_DIGITAL_CORE (FuriHalLeaseTim2 | FuriHalLeaseDma1Ch1 | FuriHalLeaseDma1Ch2)
#define FURI_HAL_LEASE_DIGITAL_NONCONNECTOR FURI_HAL_LEASE_DIGITAL_CORE
#define FURI_HAL_LEASE_DIGITAL_PC0 (FURI_HAL_LEASE_DIGITAL_CORE | FuriHalLeasePc0)
#define FURI_HAL_LEASE_DIGITAL_PC1 (FURI_HAL_LEASE_DIGITAL_CORE | FuriHalLeasePc1)
#define FURI_HAL_LEASE_DIGITAL_PC3 (FURI_HAL_LEASE_DIGITAL_CORE | FuriHalLeasePc3)
#define FURI_HAL_LEASE_DIGITAL_PB2 (FURI_HAL_LEASE_DIGITAL_CORE | FuriHalLeasePb2)
#define FURI_HAL_LEASE_DIGITAL_PB3 (FURI_HAL_LEASE_DIGITAL_CORE | FuriHalLeasePb3)
#define FURI_HAL_LEASE_DIGITAL_PA4 (FURI_HAL_LEASE_DIGITAL_CORE | FuriHalLeasePa4)
#define FURI_HAL_LEASE_DIGITAL_PA6 (FURI_HAL_LEASE_DIGITAL_CORE | FuriHalLeasePa6)
#define FURI_HAL_LEASE_DIGITAL_PA7 (FURI_HAL_LEASE_DIGITAL_CORE | FuriHalLeasePa7)

"""

ALLOW = """           mask == FURI_HAL_LEASE_DIGITAL_NONCONNECTOR ||
           mask == FURI_HAL_LEASE_DIGITAL_PC0 ||
           mask == FURI_HAL_LEASE_DIGITAL_PC1 ||
           mask == FURI_HAL_LEASE_DIGITAL_PC3 ||
           mask == FURI_HAL_LEASE_DIGITAL_PB2 ||
           mask == FURI_HAL_LEASE_DIGITAL_PB3 ||
           mask == FURI_HAL_LEASE_DIGITAL_PA4 ||
           mask == FURI_HAL_LEASE_DIGITAL_PA6 ||
           mask == FURI_HAL_LEASE_DIGITAL_PA7 ||
"""

HELPER = """/* LabMate E11 native DigitalSequence owner. */
static uint32_t digital_sequence_e11_mask(const GpioPin* pin) {
    if(!pin) return 0U;
    if(pin == &gpio_ext_pc0 || (pin->port == gpio_ext_pc0.port && pin->pin == gpio_ext_pc0.pin))
        return FURI_HAL_LEASE_DIGITAL_PC0;
    if(pin == &gpio_ext_pc1 || (pin->port == gpio_ext_pc1.port && pin->pin == gpio_ext_pc1.pin))
        return FURI_HAL_LEASE_DIGITAL_PC1;
    if(pin == &gpio_ext_pc3 || (pin->port == gpio_ext_pc3.port && pin->pin == gpio_ext_pc3.pin))
        return FURI_HAL_LEASE_DIGITAL_PC3;
    if(pin == &gpio_ext_pb2 || (pin->port == gpio_ext_pb2.port && pin->pin == gpio_ext_pb2.pin))
        return FURI_HAL_LEASE_DIGITAL_PB2;
    if(pin == &gpio_ext_pb3 || (pin->port == gpio_ext_pb3.port && pin->pin == gpio_ext_pb3.pin))
        return FURI_HAL_LEASE_DIGITAL_PB3;
    if(pin == &gpio_ext_pa4 || (pin->port == gpio_ext_pa4.port && pin->pin == gpio_ext_pa4.pin))
        return FURI_HAL_LEASE_DIGITAL_PA4;
    if(pin == &gpio_ext_pa6 || (pin->port == gpio_ext_pa6.port && pin->pin == gpio_ext_pa6.pin))
        return FURI_HAL_LEASE_DIGITAL_PA6;
    if(pin == &gpio_ext_pa7 || (pin->port == gpio_ext_pa7.port && pin->pin == gpio_ext_pa7.pin))
        return FURI_HAL_LEASE_DIGITAL_PA7;
    /* Never pretend that unknown/internal pins have GPIO protection.
     * The shared TIM2/DMA claim still excludes cooperating capture users.
     */
    return FURI_HAL_LEASE_DIGITAL_NONCONNECTOR;
}

static bool digital_sequence_e11_claim(DigitalSequence* sequence) {
    if(sequence->e11_lease_fault || sequence->e11_lease_handle) return false;
    const uint32_t mask = digital_sequence_e11_mask(sequence->gpio);
    if(!mask) return false;
    const uint32_t handle = furi_hal_resource_lease_try_acquire(mask);
    if(!handle) return false;
    /* Legacy direct-register TIM2/DMA users do not consult this lease.
     * Preflight AFTER claim, BEFORE modifying even the GPIO output.
     * It cannot close a concurrent noncooperating start race.
     */
    if(furi_hal_bus_is_enabled(FuriHalBusTIM2) ||
       LL_DMA_IsEnabledChannel(DMA1, LL_DMA_CHANNEL_1) ||
       LL_DMA_IsEnabledChannel(DMA1, LL_DMA_CHANNEL_2)) {
        if(!furi_hal_resource_lease_release(handle, mask)) {
            sequence->e11_lease_handle = handle;
            sequence->e11_lease_mask = mask;
            sequence->e11_lease_fault = true;
        }
        return false;
    }
    sequence->e11_lease_handle = handle;
    sequence->e11_lease_mask = mask;
    return true;
}

static void digital_sequence_e11_release(DigitalSequence* sequence) {
    if(sequence->e11_lease_fault || !sequence->e11_lease_handle) return;
    if(furi_hal_resource_lease_release(
           sequence->e11_lease_handle, sequence->e11_lease_mask)) {
        sequence->e11_lease_handle = 0U;
        sequence->e11_lease_mask = 0U;
    } else {
        /* Sticky fault: never reuse an unresolved firmware owner. */
        sequence->e11_lease_fault = true;
    }
}

"""

def replace_once(s: str, old: str, new: str) -> str:
    if s.count(old) != 1:
        raise ValueError("Missing or ambiguous pinned native source anchor " + repr(old[:100]))
    return s.replace(old, new, 1)


def patch(h: str, r: str, d: str) -> tuple[str, str, str]:
    if MARKER in d or "FURI_HAL_LEASE_DIGITAL_CORE" in h:
        raise ValueError("DigitalSequence patch already applied")
    h = replace_once(h, "#define FURI_HAL_LEASE_PULSE_PA7 (FURI_HAL_LEASE_PULSE_CORE | FuriHalLeasePa7 | FuriHalLeaseExti7)\n",
                     "#define FURI_HAL_LEASE_PULSE_PA7 (FURI_HAL_LEASE_PULSE_CORE | FuriHalLeasePa7 | FuriHalLeaseExti7)\n" + MASKS)
    r = replace_once(r,
        "           mask == FURI_HAL_LEASE_PULSE_PA7 ||\n",
        "           mask == FURI_HAL_LEASE_PULSE_PA7 ||\n" + ALLOW)
    d = replace_once(d, "#include <furi_hal_bus.h>",
                     "#include <furi_hal_bus.h>\n#include <furi_hal_resources.h>")
    d = replace_once(d, "    DigitalSequenceState state;\n",
                     "    DigitalSequenceState state;\n    uint32_t e11_lease_handle;\n    uint32_t e11_lease_mask;\n    bool e11_lease_fault;\n")
    d = replace_once(d, "    sequence->gpio = gpio;\n",
                     "    sequence->gpio = gpio;\n"
                     "    sequence->e11_lease_handle = 0U;\n"
                     "    sequence->e11_lease_mask = 0U;\n"
                     "    sequence->e11_lease_fault = false;\n")
    d = replace_once(d, "static inline void digital_sequence_start_dma(DigitalSequence* sequence) {",
                     HELPER + "static inline void digital_sequence_start_dma(DigitalSequence* sequence) {")
    d = replace_once(d, """static inline void digital_sequence_finish(DigitalSequence* sequence) {
    if(sequence->state == DigitalSequenceStateActive) {""",
                     """static inline void digital_sequence_finish(DigitalSequence* sequence) {
    if(sequence->state != DigitalSequenceStateActive) return;
    /* If a bypassing native service took away TIM2's clock, do NOT touch
     * its registers, DMA or GPIO and do not release our stale claim.
     */
    if(!furi_hal_bus_is_enabled(FuriHalBusTIM2)) {
        sequence->e11_lease_fault = true;
        return;
    }
    if(sequence->state == DigitalSequenceStateActive) {""")
    d = replace_once(d, """    FURI_CRITICAL_ENTER();

    furi_hal_gpio_init(sequence->gpio,""",
                     """    /* Claim BEFORE GPIO configuration, DMA init and TIM2 clock changes.
     * A void transmit API cannot report BUSY, so reject without output.
     */
    if(!digital_sequence_e11_claim(sequence)) {
        FURI_LOG_W(TAG, "E11: DigitalSequence TIM2/DMA/GPIO BUSY or ERR");
        return;
    }

    FURI_CRITICAL_ENTER();

    furi_hal_gpio_init(sequence->gpio,""")
    d = replace_once(d, """    digital_sequence_finish(sequence);
    digital_sequence_timer_buffer_reset(sequence);""",
                     """    digital_sequence_finish(sequence);
    /* STOP hardware before releasing its reservation. Fault stays sticky
     * if a legacy service unexpectedly disabled TIM2 mid-transmission.
     */
    digital_sequence_e11_release(sequence);
    digital_sequence_timer_buffer_reset(sequence);""")
    return h, r, d


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("firmware_root", type=Path)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    root = args.firmware_root.resolve()
    try:
        head = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        if head != PINNED:
            raise ValueError("Wrong pinned Momentum HEAD: " + head)
        dirty = set()
        for line in subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain"], text=True).splitlines():
            if len(line) < 4 or line[:2] == "??" or "->" in line:
                raise ValueError("Untracked/renamed firmware files refused")
            dirty.add(line[3:])
        if dirty != EXPECTED_DIRTY:
            raise ValueError("Unexpected firmware prepatch state: " + repr(sorted(dirty)))
        h = (root / HEADER).read_text(encoding="utf-8")
        r = (root / RESOURCE).read_text(encoding="utf-8")
        d = (root / DIGITAL).read_text(encoding="utf-8")
        if "FURI_HAL_LEASE_PULSE_CORE" not in h or (
            "LabMate E11 native PulseReader single composite-resource claim." not in
            (root / "lib/pulse_reader/pulse_reader.c").read_text()):
            raise ValueError("Native PulseReader prerequisite absent")
        nh, nr, nd = patch(h, r, d)
        print("E11 DIGITAL TIM2 + DMA1 CH1/2 + 8 CONNECTOR GPIO SOURCE CHECK PASS")
        if args.apply:
            for path, content in ((HEADER, nh), (RESOURCE, nr), (DIGITAL, nd)):
                (root / path).write_text(content, encoding="utf-8")
            print("E11 DigitalSequence firmware SOURCE patched; NO flash or install.")
        else:
            print("READ ONLY; no firmware modified.")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("REFUSED E11 native digital sequence: " + str(exc), file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
