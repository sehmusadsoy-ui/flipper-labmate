#!/usr/bin/env python3
"""LabMate E11 pinned native NFC TIM1+TIM17 transactional lease migration.

Source-only. The native low-power resume interface can return
FuriHalNfcErrorBusy; refuse both timers BEFORE modifying NFC IRQ/GPIO.
Cooperative TIM1+TIM17 lease does not intercept unrelated direct LL.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

HEAD = "d3f89dfe2ef6b01839201598e9be1590cba80322"
HEADER = "targets/f7/furi_hal/furi_hal_resources.h"
RESOURCE = "targets/f7/furi_hal/furi_hal_resources.c"
NFC_TIMER = "targets/f7/furi_hal/furi_hal_nfc_timer.c"
NFC = "targets/f7/furi_hal/furi_hal_nfc.c"
NFC_INTERNAL = "targets/f7/furi_hal/furi_hal_nfc_i.h"
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
    "lib/digital_signal/digital_sequence.c",
    "targets/f7/furi_hal/furi_hal_ibutton.c",
    "targets/f7/furi_hal/furi_hal_ibutton.h",
    "lib/ibutton/protocols/misc/protocol_group_misc.c",
}
MARKER = "/* LabMate E11 native NFC TIM1/TIM17 owner. */"

def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError("Missing or ambiguous NFC exact-source anchor: " + repr(old[:105]))
    return source.replace(old, new, 1)

def patch(h: str, r: str, timer: str, nfc: str, internal: str) -> tuple[str,str,str,str,str]:
    if MARKER in timer or "FURI_HAL_LEASE_NATIVE_NFC_TIMERS" in h:
        raise ValueError("Native NFC lease already applied")
    h = replace_once(h,
        "#define FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1 (FuriHalLeaseTim1)\n",
        "#define FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1 (FuriHalLeaseTim1)\n"
        "/* NFC FWT uses TIM1; block TX uses TIM17. Claim both atomically. */\n"
        "enum { FuriHalLeaseTim17 = (1U << 24) };\n"
        "#define FURI_HAL_LEASE_NATIVE_NFC_TIMERS (FuriHalLeaseTim1 | FuriHalLeaseTim17)\n")
    r = replace_once(r,
        "           mask == FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1 ||\n",
        "           mask == FURI_HAL_LEASE_NATIVE_IBUTTON_TIM1 ||\n"
        "           mask == FURI_HAL_LEASE_NATIVE_NFC_TIMERS ||\n")
    timer = replace_once(timer,
        "#define TAG \"FuriHalNfcTimer\"\n",
        """#define TAG "FuriHalNfcTimer"

/* Optional debug mode uses additional PA7/PA6 connector GPIO which this
 * two-timer claim does NOT own. Reject rather than overwrite that GPIO.
 * Stock Momentum's debug branch also references an undefined timer_config.
 */
#ifdef FURI_HAL_NFC_TIMER_DEBUG
#error "E11 native NFC timer GPIO debug mode requires a separate atomic PA7/PA6 lease"
#endif
""")
    timer = replace_once(timer,
        "static void furi_hal_nfc_timer_irq_callback(void* context) {",
        """/* LabMate E11 native NFC TIM1/TIM17 owner. */
static uint32_t nfc_e11_handle;
static bool nfc_e11_fault;

static bool nfc_e11_ready(void) {
    if(!nfc_e11_handle || nfc_e11_fault) return false;
    if(!furi_hal_bus_is_enabled(FuriHalBusTIM1) ||
       !furi_hal_bus_is_enabled(FuriHalBusTIM17)) {
        nfc_e11_fault = true;
        return false;
    }
    return true;
}

static void furi_hal_nfc_timer_irq_callback(void* context) {""")
    timer = replace_once(timer,
        """    const FuriHalNfcTimerConfig* config = context;
    if(LL_TIM_IsActiveFlag_UPDATE(config->timer)) {""",
        """    const FuriHalNfcTimerConfig* config = context;
    if(!nfc_e11_ready()) return;
    if(LL_TIM_IsActiveFlag_UPDATE(config->timer)) {""")
    timer = replace_once(timer,
        """static inline bool furi_hal_nfc_timer_is_running(FuriHalNfcTimer timer) {
    return LL_TIM_IsEnabledCounter(furi_hal_nfc_timers[timer].timer) != 0;
}""",
        """static inline bool furi_hal_nfc_timer_is_running(FuriHalNfcTimer timer) {
    if(!nfc_e11_ready()) return false;
    return LL_TIM_IsEnabledCounter(furi_hal_nfc_timers[timer].timer) != 0;
}""")
    timer = replace_once(timer,
        """static void furi_hal_nfc_timer_start_core_ticks(FuriHalNfcTimer timer, uint64_t core_ticks) {
    furi_check(!furi_hal_nfc_timer_is_running(timer));""",
        """static void furi_hal_nfc_timer_start_core_ticks(FuriHalNfcTimer timer, uint64_t core_ticks) {
    if(!nfc_e11_ready()) return;
    furi_check(!furi_hal_nfc_timer_is_running(timer));""")
    timer = replace_once(timer,
        """static void furi_hal_nfc_timer_stop(FuriHalNfcTimer timer) {
    const FuriHalNfcTimerConfig* config = &furi_hal_nfc_timers[timer];

    LL_TIM_DisableIT_UPDATE""",
        """static void furi_hal_nfc_timer_stop(FuriHalNfcTimer timer) {
    if(!nfc_e11_ready()) return;
    const FuriHalNfcTimerConfig* config = &furi_hal_nfc_timers[timer];

    LL_TIM_DisableIT_UPDATE""")
    timer = replace_once(timer,
        """void furi_hal_nfc_timers_init(void) {
    for(size_t i = 0; i < FuriHalNfcTimerCount; i++) {
        furi_hal_nfc_timer_init(i);
    }
}

void furi_hal_nfc_timers_deinit(void) {
    for(size_t i = 0; i < FuriHalNfcTimerCount; i++) {
        furi_hal_nfc_timer_deinit(i);
    }
}""",
        """bool furi_hal_nfc_timers_init(void) {
    /* The original NFC internal API was void. The caller now handles
     * BUSY before NFC IRQ/GPIO or oscillator state is changed.
     */
    if(nfc_e11_handle || nfc_e11_fault) return false;
    const uint32_t mask = FURI_HAL_LEASE_NATIVE_NFC_TIMERS;
    const uint32_t lease = furi_hal_resource_lease_try_acquire(mask);
    if(!lease) return false;

    /* Noncooperating legacy timers may already be live. Check BOTH
     * clocks after claiming and before any native bus/IRQ write.
     * Does not eliminate races with direct-register legacy starters.
     */
    if(furi_hal_bus_is_enabled(FuriHalBusTIM1) ||
       furi_hal_bus_is_enabled(FuriHalBusTIM17)) {
        if(!furi_hal_resource_lease_release(lease, mask)) {
            nfc_e11_handle = lease;
            nfc_e11_fault = true;
        }
        return false;
    }
    nfc_e11_handle = lease;
    for(size_t i = 0; i < FuriHalNfcTimerCount; i++) {
        furi_hal_nfc_timer_init(i);
    }
    return true;
}

void furi_hal_nfc_timers_deinit(void) {
    if(!nfc_e11_ready()) return;
    const uint32_t lease = nfc_e11_handle;
    for(size_t i = 0; i < FuriHalNfcTimerCount; i++) {
        furi_hal_nfc_timer_deinit(i);
    }
    if(furi_hal_resource_lease_release(
           lease, FURI_HAL_LEASE_NATIVE_NFC_TIMERS)) {
        nfc_e11_handle = 0U;
    } else {
        /* Sticky error: a failed release is not a reusable timer. */
        nfc_e11_fault = true;
    }
}""")
    internal = replace_once(internal,
        "void furi_hal_nfc_timers_init(void);",
        "/* E11 returns false before touching either timer on cooperative BUSY. */\n"
        "bool furi_hal_nfc_timers_init(void);")
    nfc = replace_once(nfc,
        """    do {
        furi_hal_nfc_init_gpio_isr();
        furi_hal_nfc_timers_init();
        error = furi_hal_nfc_turn_on_osc(handle);
        if(error != FuriHalNfcErrorNone) break;""",
        """    do {
        /* Acquire both native timers FIRST; Busy cannot disturb GPIO/IRQ.
         * NFC low-power resume is already an error-returning API.
         */
        if(!furi_hal_nfc_timers_init()) {
            error = FuriHalNfcErrorBusy;
            break;
        }
        furi_hal_nfc_init_gpio_isr();
        error = furi_hal_nfc_turn_on_osc(handle);
        if(error != FuriHalNfcErrorNone) {
            /* Restore acquired NFC timer IRQ/GPIO state on oscillator error.
             * Leave other owners' TIM1/TIM17 untouched on BUSY.
             */
            furi_hal_nfc_deinit_gpio_isr();
            furi_hal_nfc_timers_deinit();
            break;
        }""")
    return h,r,timer,nfc,internal

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("firmware_root",type=Path)
    ap.add_argument("--apply",action="store_true")
    a=ap.parse_args()
    root=a.firmware_root.resolve()
    try:
        sha=subprocess.check_output(
            ["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        if sha!=HEAD: raise ValueError("Momentum source commit not pinned")
        dirty=set()
        for ln in subprocess.check_output(
            ["git","-C",str(root),"status","--porcelain"],text=True).splitlines():
            if len(ln)<4 or "??" in ln[:2] or "->" in ln:
                raise ValueError("Untracked/renamed Momentum source refused")
            dirty.add(ln[3:])
        if dirty!=EXPECTED_DIRTY:
            raise ValueError("Unapproved prior native source modifications: "+repr(sorted(dirty)))
        original=[(root/path).read_text(encoding="utf-8") for path in
                  (HEADER,RESOURCE,NFC_TIMER,NFC,NFC_INTERNAL)]
        updated=patch(*original)
        print("E11 NATIVE NFC TIM1/TIM17 TRANSACTIONAL SOURCE CHECK PASS")
        if a.apply:
            for path,body in zip((HEADER,RESOURCE,NFC_TIMER,NFC,NFC_INTERNAL),updated):
                (root/path).write_text(body,encoding="utf-8")
                print("SOURCE PATCHED: "+path)
            print("NO DEVICE/USB/FLASH OR STABLE RELEASE")
        else:
            print("READ ONLY; FIRMWARE SOURCES UNMODIFIED")
        return 0
    except (OSError,subprocess.CalledProcessError,ValueError) as ex:
        print("E11 NFC SOURCE REFUSED: "+str(ex),file=sys.stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
