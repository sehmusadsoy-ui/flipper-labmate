#!/usr/bin/env python3
"""E11.1c pinned Momentum GPIO EXTI non-asserting TRY-ADD API.

Dormant additive API. Does not reconfigure GPIO or claim the pin, and
does not change existing void-return callback add/remove semantics.
It prevents callback-slot takeover by callers opting into this API,
but is NOT a firmware-wide GPIO/EXTI/legacy-service lease.

Read-only check by default. --apply edits an exact Git checkout in
CI source only. --allow-prepatched accepts exactly the already-reviewed
timed-I2C + E11.1a dormant lease changes, nothing else.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

EXPECTED_HEAD = "d3f89dfe2ef6b01839201598e9be1590cba80322"
HEADER = "targets/f7/furi_hal/furi_hal_gpio.h"
SOURCE = "targets/f7/furi_hal/furi_hal_gpio.c"
API = "targets/f7/api_symbols.csv"
PREPATCHED = {
    "targets/furi_hal_include/furi_hal_i2c.h",
    "targets/f7/furi_hal/furi_hal_i2c.c",
    "targets/f7/furi_hal/furi_hal_resources.h",
    "targets/f7/furi_hal/furi_hal_resources.c",
    API,
}
SYMBOL = "furi_hal_gpio_try_add_int_callback"

HEADER_NEEDLE = "void furi_hal_gpio_add_int_callback(const GpioPin* gpio, GpioExtiCallback cb, void* ctx);"
HEADER_INSERT = HEADER_NEEDLE + """

/** Nonasserting attempt to register an EXTI callback.
 * Returns false if this EXTI line already has a callback or args are invalid;
 * does not alter callback, EXTI enable, or GPIO on failure. Registration
 * does NOT acquire a GPIO pin or protect other HAL users; caller must own
 * a compatible pin/line and configure it safely before invoking this.
 * Existing furi_hal_gpio_add_int_callback() remains unchanged.
 */
#define FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK 1
bool furi_hal_gpio_try_add_int_callback(
    const GpioPin* gpio, GpioExtiCallback cb, void* ctx);
"""

SOURCE_NEEDLE = "void furi_hal_gpio_add_int_callback(const GpioPin* gpio, GpioExtiCallback cb, void* ctx) {"
SOURCE_INSERT = """/* Atomically refuse a full EXTI line without stealing its callback.
 * This additive API leaves the old assertion-based entry point alone,
 * so legacy services are NOT made safe or coordinated by this change.
 * The GPIO pin's mode/port ownership is outside this function.
 */
bool furi_hal_gpio_try_add_int_callback(
    const GpioPin* gpio, GpioExtiCallback cb, void* ctx) {
    if(gpio == NULL || cb == NULL) return false;

    bool acquired = false;
    FURI_CRITICAL_ENTER();
    const uint8_t pin_num = furi_hal_gpio_get_pin_num(gpio);
    if(gpio_interrupt[pin_num].callback == NULL) {
        gpio_interrupt[pin_num].callback = cb;
        gpio_interrupt[pin_num].context = ctx;
        const uint32_t exti_line = GET_EXTI_LINE(gpio->pin);
        LL_EXTI_EnableIT_0_31(exti_line);
        acquired = true;
    }
    FURI_CRITICAL_EXIT();
    return acquired;
}

""" + SOURCE_NEEDLE

API_NEEDLE = 'Function,+,furi_hal_gpio_add_int_callback,void,"const GpioPin*, GpioExtiCallback, void*"'
API_INSERT = API_NEEDLE + (
    '\nFunction,+,furi_hal_gpio_try_add_int_callback,_Bool,'
    '"const GpioPin*, GpioExtiCallback, void*"'
)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True).rstrip("\r\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware_root", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--allow-prepatched", action="store_true")
    args = parser.parse_args()
    root = args.firmware_root.resolve()
    try:
        if git(root, "rev-parse", "HEAD") != EXPECTED_HEAD:
            raise ValueError("incorrect pinned Momentum HEAD")
        lines = git(root, "status", "--porcelain").splitlines()
        dirty = set()
        for line in lines:
            if len(line) < 4 or "??" in line[:2] or "->" in line:
                raise ValueError("untracked or renamed firmware input")
            dirty.add(line[3:])
        if dirty:
            if not args.allow_prepatched or dirty != PREPATCHED:
                raise ValueError(f"unapproved source changes: {sorted(dirty)}")
            check = {
                "targets/f7/furi_hal/furi_hal_i2c.c":
                    "furi_hal_i2c_external_acquire_timeout",
                "targets/f7/furi_hal/furi_hal_resources.c":
                    "furi_hal_resource_lease_try_acquire",
            }
            for path, marker in check.items():
                if marker not in (root / path).read_text(encoding="utf-8"):
                    raise ValueError(f"expected prepatch not found: {path}")
        elif args.allow_prepatched:
            raise ValueError("combined mode required exact prepatched source")

        writes = []
        for name, old, new in [
            (HEADER, HEADER_NEEDLE, HEADER_INSERT),
            (SOURCE, SOURCE_NEEDLE, SOURCE_INSERT),
            (API, API_NEEDLE, API_INSERT),
        ]:
            path = root / name
            before = path.read_text(encoding="utf-8")
            if SYMBOL in before:
                raise ValueError(f"already patched: {name}")
            if before.count(old) != 1:
                raise ValueError(f"ambiguous/changed source anchor: {name}")
            writes.append((path, before.replace(old, new, 1)))

        print("E11.1c GPIO TRY-ADD SOURCE PRECONDITIONS PASS")
        if not args.apply:
            print("READ ONLY: no source changed")
            return 0
        for path, updated in writes:
            path.write_text(updated, encoding="utf-8")
            print("PATCHED SOURCE ONLY:", path.relative_to(root))
        print("NONASSERTING EXTI CALLBACK API ADDED; NOT A PIN/RESOURCE LEASE.")
        print("NO USB, NO FLASH, NO FAP INSTALL.")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("REFUSED E11.1c:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
