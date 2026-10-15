#!/usr/bin/env python3
"""E11.1a: add a *dormant* firmware-owned atomic resource lease API.

ONLY modifies an exact pinned Momentum source checkout, never builds or
flashes a Flipper. This is deliberately a firmware primitive, NOT proof
that legacy TIM/EXTI/GPIO owners honor it. The first stage adds no FAP
callers and changes no existing HAL driver behavior.

Default: read-only applicability check. --apply: source files only.
Allows exactly the three changes from LabMate's verified timed-I2C patch
when --allow-timed-i2c is explicitly supplied (for combined CI builds).
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

EXPECTED_HEAD = "d3f89dfe2ef6b01839201598e9be1590cba80322"
HEADER = "targets/f7/furi_hal/furi_hal_resources.h"
SOURCE = "targets/f7/furi_hal/furi_hal_resources.c"
API = "targets/f7/api_symbols.csv"
I2C_DIRTY = {
    "targets/furi_hal_include/furi_hal_i2c.h",
    "targets/f7/furi_hal/furi_hal_i2c.c",
    API,
}
SYMBOL = "furi_hal_resource_lease_try_acquire"
HEADER_NEEDLE = "#define INPUT_DEBOUNCE_TICKS 4"
HEADER_INSERT = """/* Experimental firmware-owned E11 lease API. Not active for legacy HAL
 * owners unless all participating services explicitly acquire/release.
 * Fixed resource-mask types make partial/bypass pin claims invalid.
 */
#define FURI_HAL_RESOURCE_LEASE_API_V1 1
enum {
    FuriHalLeaseTim1 = (1U << 0),
    FuriHalLeasePa7 = (1U << 1),
    FuriHalLeaseTim2 = (1U << 2),
    FuriHalLeasePb3 = (1U << 3),
    FuriHalLeaseExti0 = (1U << 4),
    FuriHalLeasePc0 = (1U << 5),
    FuriHalLeaseExti1 = (1U << 6),
    FuriHalLeasePc1 = (1U << 7),
    FuriHalLeaseExti2 = (1U << 8),
    FuriHalLeasePb2 = (1U << 9),
    FuriHalLeaseExti4 = (1U << 10),
    FuriHalLeasePa4 = (1U << 11),
    FuriHalLeaseUsart1 = (1U << 12),
    FuriHalLeaseI2c3 = (1U << 13),
};
#define FURI_HAL_LEASE_PWM_PA7 (FuriHalLeaseTim1 | FuriHalLeasePa7)
#define FURI_HAL_LEASE_COUNTER_PB3 (FuriHalLeaseTim2 | FuriHalLeasePb3)
#define FURI_HAL_LEASE_IRQ_PC0 (FuriHalLeaseExti0 | FuriHalLeasePc0)
#define FURI_HAL_LEASE_IRQ_PC1 (FuriHalLeaseExti1 | FuriHalLeasePc1)
#define FURI_HAL_LEASE_IRQ_PB2 (FuriHalLeaseExti2 | FuriHalLeasePb2)
#define FURI_HAL_LEASE_IRQ_PA4 (FuriHalLeaseExti4 | FuriHalLeasePa4)
#define FURI_HAL_LEASE_ONEWIRE_PA4 (FuriHalLeasePa4)
#define FURI_HAL_LEASE_I2C3_EXT (FuriHalLeaseI2c3 | FuriHalLeasePc0 | FuriHalLeasePc1)
#define FURI_HAL_LEASE_USART1 (FuriHalLeaseUsart1)

/* Returns unique nonzero handle after an atomic claim, zero on BUSY/error.
 * No register or pin state is changed by claim/release. Each handle is
 * valid for ONE exact mask; no partial release. Handle wrap fails closed.
 */
uint32_t furi_hal_resource_lease_try_acquire(uint32_t resources);
bool furi_hal_resource_lease_release(uint32_t handle, uint32_t resources);

""" + HEADER_NEEDLE

SOURCE_NEEDLE = "const GpioPinRecord* furi_hal_resources_pin_by_number(uint8_t number) {"
SOURCE_INSERT = """/* Firmware-owned E11 lease primitive (not a complete HAL integration).
 * FURI critical sections atomically guard state across firmware threads.
 * Legacy HAL users are NOT intercepted by this table yet. Never claim
 * this function detects independent TIM/EXTI owners that bypass the API.
 */
#define FURI_HAL_LEASE_MAX_CLAIMS 16U
typedef struct {
    uint32_t handle;
    uint32_t mask;
} FuriHalLeaseClaim;

static FuriHalLeaseClaim furi_hal_lease_claims[FURI_HAL_LEASE_MAX_CLAIMS];
static uint32_t furi_hal_lease_used;
static uint32_t furi_hal_lease_last_handle;

/* Reject incomplete combinations like TIM1 without PA7: all callers must
 * claim exactly one supported composite resource set, not subsets. */
static bool furi_hal_lease_mask_allowed(uint32_t mask) {
    return mask == FURI_HAL_LEASE_PWM_PA7 ||
           mask == FURI_HAL_LEASE_COUNTER_PB3 ||
           mask == FURI_HAL_LEASE_IRQ_PC0 ||
           mask == FURI_HAL_LEASE_IRQ_PC1 ||
           mask == FURI_HAL_LEASE_IRQ_PB2 ||
           mask == FURI_HAL_LEASE_IRQ_PA4 ||
           mask == FURI_HAL_LEASE_ONEWIRE_PA4 ||
           mask == FURI_HAL_LEASE_I2C3_EXT ||
           mask == FURI_HAL_LEASE_USART1;
}

uint32_t furi_hal_resource_lease_try_acquire(uint32_t resources) {
    if(!furi_hal_lease_mask_allowed(resources)) return 0U;
    uint32_t handle = 0U;
    FURI_CRITICAL_ENTER();
    if((furi_hal_lease_used & resources) == 0U &&
       furi_hal_lease_last_handle != UINT32_MAX) {
        for(size_t i = 0U; i < FURI_HAL_LEASE_MAX_CLAIMS; ++i) {
            if(furi_hal_lease_claims[i].handle == 0U) {
                handle = ++furi_hal_lease_last_handle;
                furi_hal_lease_claims[i].handle = handle;
                furi_hal_lease_claims[i].mask = resources;
                furi_hal_lease_used |= resources;
                break;
            }
        }
    }
    FURI_CRITICAL_EXIT();
    return handle;
}

bool furi_hal_resource_lease_release(uint32_t handle, uint32_t resources) {
    if(handle == 0U || !furi_hal_lease_mask_allowed(resources)) return false;
    bool released = false;
    FURI_CRITICAL_ENTER();
    for(size_t i = 0U; i < FURI_HAL_LEASE_MAX_CLAIMS; ++i) {
        if(furi_hal_lease_claims[i].handle == handle &&
           furi_hal_lease_claims[i].mask == resources) {
            furi_hal_lease_used &= ~resources;
            furi_hal_lease_claims[i].handle = 0U;
            furi_hal_lease_claims[i].mask = 0U;
            released = true;
            break;
        }
    }
    FURI_CRITICAL_EXIT();
    return released;
}

""" + SOURCE_NEEDLE

API_NEEDLE = "Function,+,furi_hal_resources_get_ext_pin_number,int32_t,const GpioPin*"
API_INSERT = """Function,+,furi_hal_resource_lease_release,_Bool,"uint32_t, uint32_t"
Function,+,furi_hal_resource_lease_try_acquire,uint32_t,uint32_t
""" + API_NEEDLE


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True).strip()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("firmware_root", type=Path)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--allow-timed-i2c", action="store_true")
    a = p.parse_args()
    root = a.firmware_root.resolve()
    try:
        head = git(root, "rev-parse", "HEAD")
        if head != EXPECTED_HEAD:
            raise ValueError(f"Momentum HEAD must be exact: {head}")
        dirty_lines = git(root, "status", "--porcelain").splitlines()
        dirty = set()
        for line in dirty_lines:
            if not line:
                continue
            if len(line) < 4 or "??" in line[:2]:
                raise ValueError("Untracked/unknown checkout changes refused")
            dirty.add(line[3:])
        if dirty:
            if not a.allow_timed_i2c or dirty != I2C_DIRTY:
                raise ValueError(f"Unapproved tracked firmware edits: {sorted(dirty)}")
            if "furi_hal_i2c_external_acquire_timeout" not in (
                root / "targets/f7/furi_hal/furi_hal_i2c.c"
            ).read_text(encoding="utf-8"):
                raise ValueError("Expected timed-I2C symbol missing")

        writes = []
        for relative, old, new in (
            (HEADER, HEADER_NEEDLE, HEADER_INSERT),
            (SOURCE, SOURCE_NEEDLE, SOURCE_INSERT),
            (API, API_NEEDLE, API_INSERT),
        ):
            path = root / relative
            before = path.read_text(encoding="utf-8")
            if SYMBOL in before:
                raise ValueError(f"Already applied/incompatible: {relative}")
            if before.count(old) != 1:
                raise ValueError(f"Source anchor missing or ambiguous: {relative}")
            writes.append((path, before.replace(old, new, 1)))

        print("E11.1a EXACT FIRMWARE CONTRACT SOURCE CHECK PASS")
        if not a.apply:
            print("READ ONLY; NO FIRMWARE FILES MODIFIED")
            return 0
        for file, changed in writes:
            file.write_text(changed, encoding="utf-8")
            print(f"PATCHED SOURCE ONLY: {file.relative_to(root)}")
        print("Dormant lease API only; old HAL service paths NOT covered.")
        print("NO COMPILE, NO FAP INSTALL, NO USB, NO FLASH, NO STABLE RELEASE")
        return 0
    except (OSError, subprocess.CalledProcessError, ValueError) as ex:
        print(f"REFUSED E11.1a: {ex}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
