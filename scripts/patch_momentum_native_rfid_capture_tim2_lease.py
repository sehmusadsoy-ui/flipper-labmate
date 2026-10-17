#!/usr/bin/env python3
"""E11 pinned native RFID capture TIM2 cooperative owner (source only).

This stage does NOT migrate RFID DMA emulation, field detection, upstream
callers, or Sub-GHz. Neither firmware flashing nor stable changes occur.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

PIN = "d3f89dfe2ef6b01839201598e9be1590cba80322"
H = "targets/f7/furi_hal/furi_hal_resources.h"
R = "targets/f7/furi_hal/furi_hal_resources.c"
RFID = "targets/f7/furi_hal/furi_hal_rfid.c"
RFID_H = "targets/f7/furi_hal/furi_hal_rfid.h"
API = "targets/f7/api_symbols.csv"
MARK = "/* E11 native RFID capture TIM2 owner. */"
# Pinned E11 stages are applied in a fixed order. Refuse any extra native
# edits (including an attempt to mix this patch into a different SDK).
FROM_READ_STAGE = {
    "targets/furi_hal_include/furi_hal_i2c.h",
    "targets/f7/furi_hal/furi_hal_i2c.c",
    H, R,
    "targets/f7/furi_hal/furi_hal_gpio.h",
    "targets/f7/furi_hal/furi_hal_gpio.c",
    "targets/f7/furi_hal/furi_hal_pwm.c",
    API,
    "applications/system/js_app/modules/js_gpio.c",
    "lib/pulse_reader/pulse_reader.c",
    "lib/digital_signal/digital_sequence.c",
    "targets/f7/furi_hal/furi_hal_ibutton.c",
    "targets/f7/furi_hal/furi_hal_ibutton.h",
    "lib/ibutton/protocols/misc/protocol_group_misc.c",
    "targets/f7/furi_hal/furi_hal_nfc_timer.c",
    "targets/f7/furi_hal/furi_hal_nfc_i.h",
    "targets/f7/furi_hal/furi_hal_nfc.c",
    "targets/f7/furi_hal/furi_hal_infrared.c",
    "targets/furi_hal_include/furi_hal_infrared.h",
    "lib/infrared/worker/infrared_worker.c",
    "lib/infrared/worker/infrared_worker.h",
    RFID, RFID_H,
}

def once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError("Pinned native RFID capture anchor missing/ambiguous: " + repr(old[:110]))
    return text.replace(old, new, 1)

def patch(h: str, resources: str, source: str, header: str, api: str):
    if MARK in source or "FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2" in h:
        raise ValueError("RFID capture patch already present")
    if "/* E11 native RFID read TIM1 owner. */" not in source:
        raise ValueError("RFID READ predecessor missing")
    h = once(h,
        "#define FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1 (FuriHalLeaseTim1)\n",
        "#define FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1 (FuriHalLeaseTim1)\n"
        "/* Internal RFID comparator capture: TIM2 (not connector PB3). */\n"
        "#define FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2 (FuriHalLeaseTim2)\n")
    resources = once(resources,
        "           mask == FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1 ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_RFID_READ_TIM1 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2 ||\n")
    source = once(source,
        "static void furi_hal_capture_dma_isr(void* context) {\n"
        "    UNUSED(context);\n",
        """/* E11 native RFID capture TIM2 owner. */
static uint32_t e11_rfid_capture_handle;
static bool e11_rfid_capture_fault;

static bool e11_rfid_capture_ready(void) {
    if(!e11_rfid_capture_handle || e11_rfid_capture_fault) return false;
    if(!furi_hal_bus_is_enabled(RFID_CAPTURE_TIM_BUS)) {
        e11_rfid_capture_fault = true; /* Never reuse after lost bus. */
        return false;
    }
    return true;
}

static void furi_hal_capture_dma_isr(void* context) {
    UNUSED(context);
    /* Never inspect or clear a foreign TIM2's flags after BUSY/loss. */
    if(!e11_rfid_capture_ready()) return;
""")
    source = once(source,
        """void furi_hal_rfid_tim_read_capture_start(FuriHalRfidReadCaptureCallback callback, void* context) {
    furi_check(furi_hal_rfid);

    furi_hal_rfid->read_capture_callback = callback;""",
        """bool furi_hal_rfid_tim_read_capture_try_start(
    FuriHalRfidReadCaptureCallback callback, void* context) {
    furi_check(furi_hal_rfid);
    if(!callback || e11_rfid_capture_handle || e11_rfid_capture_fault) return false;
    const uint32_t lease =
        furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2);
    if(!lease) return false;
    /* An uncoordinated native Sub-GHz/IR/RFID TIM2 service may be live. */
    if(furi_hal_bus_is_enabled(RFID_CAPTURE_TIM_BUS)) {
        if(!furi_hal_resource_lease_release(
               lease, FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2)) {
            e11_rfid_capture_handle = lease;
            e11_rfid_capture_fault = true;
        }
        return false;
    }
    e11_rfid_capture_handle = lease;
    furi_hal_rfid->read_capture_callback = callback;""")
    source = once(source,
        """    furi_hal_rfid_comp_start();
}

void furi_hal_rfid_tim_read_capture_stop(void) {
    furi_hal_rfid_comp_stop();

    furi_hal_interrupt_set_isr(FURI_HAL_RFID_EMULATE_TIMER_IRQ, NULL, NULL);
    furi_hal_bus_disable(RFID_CAPTURE_TIM_BUS);
}""",
        """    furi_hal_rfid_comp_start();
    return true;
}

/* Backward-compatible ABI. New callers MUST use the bool BUSY result. */
void furi_hal_rfid_tim_read_capture_start(
    FuriHalRfidReadCaptureCallback callback, void* context) {
    (void)furi_hal_rfid_tim_read_capture_try_start(callback, context);
}

void furi_hal_rfid_tim_read_capture_stop(void) {
    /* A denied START + STOP cannot shut down another TIM2/IRQ/comparator. */
    if(!e11_rfid_capture_ready()) return;
    furi_hal_rfid_comp_stop();
    furi_hal_interrupt_set_isr(FURI_HAL_RFID_EMULATE_TIMER_IRQ, NULL, NULL);
    furi_hal_bus_disable(RFID_CAPTURE_TIM_BUS);
    furi_hal_rfid->read_capture_callback = NULL;
    const uint32_t owner = e11_rfid_capture_handle;
    if(furi_hal_resource_lease_release(
           owner, FURI_HAL_LEASE_NATIVE_RFID_CAPTURE_TIM2)) {
        e11_rfid_capture_handle = 0U;
    } else {
        e11_rfid_capture_fault = true; /* Sticky nonreusable owner. */
    }
}""")
    header = once(header,
        "void furi_hal_rfid_tim_read_capture_start(FuriHalRfidReadCaptureCallback callback, void* context);",
        "void furi_hal_rfid_tim_read_capture_start(FuriHalRfidReadCaptureCallback callback, void* context);\n"
        "/* E11: false if TIM2 is BUSY; no GPIO/IRQ/timer writes on denial. */\n"
        "bool furi_hal_rfid_tim_read_capture_try_start(FuriHalRfidReadCaptureCallback callback, void* context);")
    api = once(api,
        'Function,+,furi_hal_rfid_tim_read_capture_start,void,"FuriHalRfidReadCaptureCallback, void*"\n',
        'Function,+,furi_hal_rfid_tim_read_capture_start,void,"FuriHalRfidReadCaptureCallback, void*"\n'
        'Function,+,furi_hal_rfid_tim_read_capture_try_start,_Bool,"FuriHalRfidReadCaptureCallback, void*"\n')
    return h, resources, source, header, api

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("firmware_root", type=Path)
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    root = a.firmware_root.resolve()
    try:
        head = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        if head != PIN:
            raise ValueError("Not the pinned Momentum source")
        seen = set()
        for line in subprocess.check_output(
                ["git", "-C", str(root), "status", "--porcelain"], text=True).splitlines():
            if len(line) < 4 or line[:2] == "??" or "->" in line:
                raise ValueError("Untracked/renamed native source refused")
            seen.add(line[3:])
        if seen != FROM_READ_STAGE:
            raise ValueError("Unexpected native source changes: " + repr(sorted(seen ^ FROM_READ_STAGE)))
        paths = (H, R, RFID, RFID_H, API)
        originals = [(root / name).read_text(encoding="utf-8") for name in paths]
        changed = patch(*originals)
        print("RFID CAPTURE TIM2 EXACT SOURCE PREFLIGHT PASS")
        if a.apply:
            for name, data in zip(paths, changed):
                (root / name).write_text(data, encoding="utf-8")
            print("PATCHED SOURCE ONLY — NO FLASH, NO DEVICE, NO RELEASE")
        else:
            print("READ-ONLY PREFLIGHT — no files written")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("RFID CAPTURE PATCH REFUSED: " + str(exc), file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
