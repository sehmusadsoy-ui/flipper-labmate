#!/usr/bin/env python3
"""Proposed Momentum SDK API enhancement for a bounded external I2C lock.

Works only on the exact Momentum development SDK source snapshot d3f89dfe
validated by LabMate v1.8 CI. Default mode is READ-ONLY --check.
--apply edits tracked firmware source locally; DOES NOT compile, flash,
install or alter the user's existing firmware/release. Requiring a clean
matching Git checkout makes an accidental wrong-firmware edit fail closed.

The stock furi_hal_i2c_acquire() is left unchanged. This adds a separate
bounded external I2C3 acquire that uses the SAME existing firmware mutex and
the existing release callback, so no unsynchronized private GPIO takeover.
Firmware compile/API-ABI/physical tests are separate, necessary gates.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
import sys

EXPECTED_HEAD = "d3f89dfe"
SYMBOL = "furi_hal_i2c_external_acquire_timeout"
HEADER_PATH = "targets/furi_hal_include/furi_hal_i2c.h"
SOURCE_PATH = "targets/f7/furi_hal/furi_hal_i2c.c"
API_PATH = "targets/f7/api_symbols.csv"

HEADER_NEEDLE = "void furi_hal_i2c_acquire(const FuriHalI2cBusHandle* handle);"
HEADER_INSERT = HEADER_NEEDLE + """

/** Try acquiring the external I2C3 bus within a finite lock wait.
 * Uses the exact same external mutex and the normal release path.
 * @param timeout_ms 0 = immediate attempt; otherwise maximum lock wait.
 * @return true only after the bus and handle were fully activated.
 * @note Only for the external PC0(SCL)/PC1(SDA) bus.
 * @note Must be paired with furi_hal_i2c_release(&furi_hal_i2c_handle_external).
 */
bool furi_hal_i2c_external_acquire_timeout(uint32_t timeout_ms);
"""

SOURCE_NEEDLE = "void furi_hal_i2c_release(const FuriHalI2cBusHandle* handle) {"
SOURCE_INSERT = """/* Bounded external-bus ownership used by an external instrument FAP.
 * Unlike furi_hal_i2c_acquire this NEVER invokes the FuriWaitForever Lock
 * callback. It acquires exactly the same firmware external mutex with a
 * finite wait, then follows the original activate/handle lifecycle.
 * furi_hal_i2c_release() remains the only matching unlock.
 */
bool furi_hal_i2c_external_acquire_timeout(uint32_t timeout_ms) {
    extern FuriMutex* furi_hal_i2c_bus_external_mutex;
    const FuriHalI2cBusHandle* handle = &furi_hal_i2c_handle_external;
    if(!furi_hal_i2c_bus_external_mutex) return false;

    const uint32_t hz = furi_kernel_get_tick_frequency();
    uint64_t ticks64 = ((uint64_t)timeout_ms * hz + 999U) / 1000U;
    if(timeout_ms > 0U && ticks64 == 0U) ticks64 = 1U;
    if(ticks64 >= FuriWaitForever) ticks64 = FuriWaitForever - 1U;

    furi_hal_power_insomnia_enter();
    if(furi_mutex_acquire(furi_hal_i2c_bus_external_mutex, (uint32_t)ticks64) !=
       FuriStatusOk) {
        furi_hal_power_insomnia_exit();
        return false;
    }

    /* Any leftover current_handle would be inconsistent: fail closed.
     * Never activate GPIO/I2C3 while the current owner is still set.
     */
    if(handle->bus->current_handle != NULL) {
        (void)furi_mutex_release(furi_hal_i2c_bus_external_mutex);
        furi_hal_power_insomnia_exit();
        return false;
    }

    handle->bus->current_handle = handle;
    handle->bus->callback(handle->bus, FuriHalI2cBusEventActivate);
    handle->callback(handle, FuriHalI2cBusHandleEventActivate);
    return true;
}

""" + SOURCE_NEEDLE

API_NEEDLE = "Function,+,furi_hal_i2c_acquire,void,const FuriHalI2cBusHandle*"
API_INSERT = API_NEEDLE + "\nFunction,+," + SYMBOL + ",_Bool,uint32_t"


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware_root", type=Path)
    parser.add_argument("--apply", action="store_true",
                        help="Modify exact clean Momentum checkout only; no flash")
    args = parser.parse_args()
    root = args.firmware_root.resolve()

    try:
        head = git(root, "rev-parse", "HEAD")
        if not head.startswith(EXPECTED_HEAD):
            raise ValueError(f"Unsupported firmware SHA {head}; expected {EXPECTED_HEAD}...")
        if git(root, "status", "--porcelain"):
            raise ValueError("Firmware checkout must be clean before any patch")
        mutations = []
        for relative, before, after in (
            (HEADER_PATH, HEADER_NEEDLE, HEADER_INSERT),
            (SOURCE_PATH, SOURCE_NEEDLE, SOURCE_INSERT),
            (API_PATH, API_NEEDLE, API_INSERT),
        ):
            target = root / relative
            content = target.read_text(encoding="utf-8")
            if SYMBOL in content:
                raise ValueError(f"Patch already applied or incompatible: {relative}")
            if content.count(before) != 1:
                raise ValueError(f"Exact source anchor mismatch: {relative}")
            mutations.append((target, content.replace(before, after, 1)))

        print(f"Exact Momentum source {head[:12]} matches. All 3 patch anchors PASS.")
        if not args.apply:
            print("CHECK ONLY: source left UNMODIFIED. Use --apply to make tracked edits.")
            return 0

        for target, modified in mutations:
            target.write_text(modified, encoding="utf-8")
            print(f"PATCHED {target.relative_to(root)}")
        print("SOURCE PATCHED ONLY. Compile firmware and FAP against matching")
        print("API before any controlled device test. NO FLASH WAS PERFORMED.")
        return 0
    except (subprocess.CalledProcessError, OSError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
