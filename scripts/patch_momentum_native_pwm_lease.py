#!/usr/bin/env python3
"""E11 native Momentum PWM service cooperative lease migration.

Applies ONLY to an exact pinned, already E11-patched firmware source tree.
Patches original native furi_hal_pwm.c (TIM1/PA7 and LPTIM2/PA4).
This makes this one native HAL service cooperate with LabMate lease holders;
it does NOT intercept unrelated direct TIM1/LPTIM2/GPIO register users.
No device, USB, flash, Stable or release operations.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

PINNED = "d3f89dfe2ef6b01839201598e9be1590cba80322"
TARGET = "targets/f7/furi_hal/furi_hal_pwm.c"
RESOURCE = "targets/f7/furi_hal/furi_hal_resources.h"
EXPECTED_DIRTY = {
    "targets/furi_hal_include/furi_hal_i2c.h",
    "targets/f7/furi_hal/furi_hal_i2c.c",
    "targets/f7/furi_hal/furi_hal_resources.h",
    "targets/f7/furi_hal/furi_hal_resources.c",
    "targets/f7/furi_hal/furi_hal_gpio.h",
    "targets/f7/furi_hal/furi_hal_gpio.c",
    "targets/f7/api_symbols.csv",
}
MARKER = "/* LabMate E11 native PWM lease owner: scoped to PWM HAL service."

HELPER = """/* LabMate E11 native PWM lease owner: scoped to PWM HAL service.
 * Legacy direct TIM1/LPTIM2 GPIO/register users remain outside this gate.
 * Firmware public void API has no BUSY result: denied start/stop/params
 * are deliberate no-ops; is_running() advertises only THIS HAL owner.
 */
static uint32_t native_pwm_tim1_pa7_handle;
static uint32_t native_pwm_lptim2_pa4_handle;
static bool native_pwm_tim1_pa7_fault;
static bool native_pwm_lptim2_pa4_fault;

static bool native_pwm_try_claim(FuriHalPwmOutputId channel) {
    uint32_t* owned = NULL;
    bool* fault = NULL;
    uint32_t mask = 0U;
    FuriHalBus bus;
    if(channel == FuriHalPwmOutputIdTim1PA7) {
        owned = &native_pwm_tim1_pa7_handle;
        fault = &native_pwm_tim1_pa7_fault;
        mask = FURI_HAL_LEASE_PWM_PA7;
        bus = FuriHalBusTIM1;
    } else if(channel == FuriHalPwmOutputIdLptim2PA4) {
        owned = &native_pwm_lptim2_pa4_handle;
        fault = &native_pwm_lptim2_pa4_fault;
        /* PA4 is shared with LabMate OneWire/Monitor/IRQ.
         * No LPTIM2 bit in experimental lease schema yet.
         */
        mask = FURI_HAL_LEASE_MONITOR_PA4;
        bus = FuriHalBusLPTIM2;
    } else {
        furi_crash();
        return false;
    }
    if(*owned || *fault) return false;
    const uint32_t handle = furi_hal_resource_lease_try_acquire(mask);
    if(!handle) return false;
    /* Also refuse a bus already enabled by a noncooperating native
     * service; check is not atomic against bypassing register callers.
     */
    if(furi_hal_bus_is_enabled(bus)) {
        if(!furi_hal_resource_lease_release(handle, mask)) {
            *owned = handle;
            *fault = true;
        }
        return false;
    }
    *owned = handle;
    return true;
}

static void native_pwm_release(uint32_t* handle, bool* fault, uint32_t mask) {
    if(!*handle || *fault) return;
    if(furi_hal_resource_lease_release(*handle, mask)) {
        *handle = 0U;
    } else {
        /* Leave the firmware claim held and deny all future operations.
         * Never attempt a second cleanup that might hit another owner.
         */
        *fault = true;
    }
}

"""

def patch_source(original: str) -> str:
    if MARKER in original:
        raise ValueError("Already applied")
    changes = (
        (
            "const uint32_t lptim_psc_table[] = {",
            HELPER + "const uint32_t lptim_psc_table[] = {",
        ),
        (
            "if(channel == FuriHalPwmOutputIdTim1PA7) {\n        furi_hal_gpio_init_ex(",
            "if(channel == FuriHalPwmOutputIdTim1PA7) {\n"
            "        if(!native_pwm_try_claim(channel)) return;\n"
            "        furi_hal_gpio_init_ex(",
        ),
        (
            "else if(channel == FuriHalPwmOutputIdLptim2PA4) {\n        furi_hal_gpio_init_ex(",
            "else if(channel == FuriHalPwmOutputIdLptim2PA4) {\n"
            "        if(!native_pwm_try_claim(channel)) return;\n"
            "        furi_hal_gpio_init_ex(",
        ),
        (
            "if(channel == FuriHalPwmOutputIdTim1PA7) {\n        furi_hal_gpio_init_simple(",
            "if(channel == FuriHalPwmOutputIdTim1PA7) {\n"
            "        if(!native_pwm_tim1_pa7_handle || native_pwm_tim1_pa7_fault) return;\n"
            "        furi_hal_gpio_init_simple(",
        ),
        (
            "furi_hal_bus_disable(FuriHalBusTIM1);",
            "furi_hal_bus_disable(FuriHalBusTIM1);\n"
            "        native_pwm_release(&native_pwm_tim1_pa7_handle,\n"
            "                           &native_pwm_tim1_pa7_fault, FURI_HAL_LEASE_PWM_PA7);",
        ),
        (
            "else if(channel == FuriHalPwmOutputIdLptim2PA4) {\n        furi_hal_gpio_init_simple(",
            "else if(channel == FuriHalPwmOutputIdLptim2PA4) {\n"
            "        if(!native_pwm_lptim2_pa4_handle || native_pwm_lptim2_pa4_fault) return;\n"
            "        furi_hal_gpio_init_simple(",
        ),
        (
            "furi_hal_bus_disable(FuriHalBusLPTIM2);",
            "furi_hal_bus_disable(FuriHalBusLPTIM2);\n"
            "        native_pwm_release(&native_pwm_lptim2_pa4_handle,\n"
            "                           &native_pwm_lptim2_pa4_fault, FURI_HAL_LEASE_MONITOR_PA4);",
        ),
        (
            "return furi_hal_bus_is_enabled(FuriHalBusTIM1);",
            "return native_pwm_tim1_pa7_handle && !native_pwm_tim1_pa7_fault &&\n"
            "               furi_hal_bus_is_enabled(FuriHalBusTIM1);",
        ),
        (
            "return furi_hal_bus_is_enabled(FuriHalBusLPTIM2);",
            "return native_pwm_lptim2_pa4_handle && !native_pwm_lptim2_pa4_fault &&\n"
            "               furi_hal_bus_is_enabled(FuriHalBusLPTIM2);",
        ),
        (
            "void furi_hal_pwm_set_params(FuriHalPwmOutputId channel, uint32_t freq, uint8_t duty) {\n"
            "    furi_assert(freq > 0);",
            "void furi_hal_pwm_set_params(FuriHalPwmOutputId channel, uint32_t freq, uint8_t duty) {\n"
            "    if(channel == FuriHalPwmOutputIdTim1PA7 &&\n"
            "       (!native_pwm_tim1_pa7_handle || native_pwm_tim1_pa7_fault)) return;\n"
            "    if(channel == FuriHalPwmOutputIdLptim2PA4 &&\n"
            "       (!native_pwm_lptim2_pa4_handle || native_pwm_lptim2_pa4_fault)) return;\n"
            "    furi_assert(freq > 0);",
        ),
    )
    out = original
    for old, new in changes:
        if out.count(old) != 1:
            raise ValueError(f"Missing or duplicate exact PWM source anchor: {old[:65]!r}")
        out = out.replace(old, new, 1)
    return out

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).rstrip("\r\n")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("firmware_root", type=Path)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    root = args.firmware_root.resolve()
    try:
        head = git(root, "rev-parse", "HEAD")
        if head != PINNED:
            raise ValueError(f"Unmatched Momentum HEAD: {head}")
        lines = git(root, "status", "--porcelain").splitlines()
        dirty = set()
        for line in lines:
            if len(line) < 4 or line[:2] == "??":
                raise ValueError("Untracked/unknown firmware files refused")
            dirty.add(line[3:])
        if dirty != EXPECTED_DIRTY:
            raise ValueError(f"Unexpected prepatch changes: {sorted(dirty)}")
        resource = (root / RESOURCE).read_text(encoding="utf-8")
        if "FURI_HAL_LEASE_PWM_PA7" not in resource or "FURI_HAL_LEASE_MONITOR_PA4" not in resource:
            raise ValueError("E11 patched firmware masks missing")
        source_file = root / TARGET
        updated = patch_source(source_file.read_text(encoding="utf-8"))
        print("E11 NATIVE PWM EXACT-MOMENTUM SOURCE PATCH APPLICABLE PASS")
        if args.apply:
            source_file.write_text(updated, encoding="utf-8")
            print("PATCHED native PWM HAL: TIM1/PA7 + PA4 LPTIM2; no device writes")
        else:
            print("READ-ONLY PREFLIGHT: no files modified")
        return 0
    except (OSError, subprocess.CalledProcessError, ValueError) as err:
        print(f"REFUSED native PWM patch: {err}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
