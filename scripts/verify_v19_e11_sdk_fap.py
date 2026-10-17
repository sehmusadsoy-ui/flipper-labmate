#!/usr/bin/env python3
"""Read-only gate: refuse a v1.9DEV FAP with unexported E11 native APIs.

This is an additional build-time assertion, NEVER an installation routine.
Run only against a source tree staged from the exact pinned Momentum base.
"""
from __future__ import annotations

import csv
import hashlib
import subprocess
import sys
from pathlib import Path

MOMENTUM_BASE = "d3f89dfe2ef6b01839201598e9be1590cba80322"
EXPORTS = {
    "furi_hal_resource_lease_try_acquire",
    "furi_hal_resource_lease_release",
    "furi_hal_gpio_try_add_int_callback",
}


class VerificationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def verify_sources(root: Path) -> None:
    sdk_csv = root / "targets/f7/api_symbols.csv"
    require(sdk_csv.is_file(), "E11 SDK API symbols file missing")
    with sdk_csv.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    exported = {row[2] for row in rows if len(row) >= 3 and row[0] == "Function" and row[1] == "+"}
    require(EXPORTS <= exported, "E11 SDK required exports absent: " + ", ".join(sorted(EXPORTS - exported)))

    res_h = (root / "targets/f7/furi_hal/furi_hal_resources.h")
    gpio_h = (root / "targets/f7/furi_hal/furi_hal_gpio.h")
    if not gpio_h.is_file():
        gpio_h = root / "targets/furi_hal_include/furi_hal_gpio.h"
    require(res_h.is_file() and gpio_h.is_file(), "E11 native HAL headers missing")
    resource_txt = res_h.read_text(encoding="utf-8")
    gpio_txt = gpio_h.read_text(encoding="utf-8")
    require("#define FURI_HAL_RESOURCE_LEASE_API_V1 1" in resource_txt, "patched lease ABI macro missing")
    require("FURI_HAL_LEASE_IRQ_PC1" in resource_txt, "PC1 native firmware lease mask missing")
    require("#define FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK 1" in gpio_txt, "nonasserting callback ABI macro missing")

    app = root / "applications_user/labmate"
    fam = (app / "application.fam").read_text(encoding="utf-8")
    internal = (app / "src/labmate_internal.h").read_text(encoding="utf-8")
    native = (app / "src/labmate_scope_native.c").read_text(encoding="utf-8")
    require('fap_version="1.9"' in fam, "staged FAP is not v1.9DEV")
    require('#define LABMATE_VERSION_TEXT "v1.9DEV"' in internal, "staged app does not display v1.9DEV")
    require("furi_hal_resource_lease_try_acquire(" in native and
            "furi_hal_gpio_try_add_int_callback(" in native,
            "staged driver does not call patched native ABI")
    require("furi_hal_gpio_add_int_callback(" not in native,
            "unapproved legacy asserting callback fallback detected")


def verify_fap(fap: Path) -> tuple[int, str]:
    require(fap.is_file(), "FAP review binary missing")
    size = fap.stat().st_size
    require(64 <= size <= 4_000_000, "invalid or unexpectedly large FAP")
    with fap.open("rb") as fh:
        elf_header = fh.read(20)
    require(elf_header[:4] == b"\x7fELF", "FAP is not an ELF executable")
    require(elf_header[4] == 1 and elf_header[5] == 1, "FAP is not 32-bit little-endian ELF")
    require(int.from_bytes(elf_header[18:20], "little") == 40, "FAP architecture is not ARM")
    with fap.open("rb") as fh:
        digest = hashlib.file_digest(fh, "sha256").hexdigest()
    return size, digest


def verify_git_base(root: Path) -> None:
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            capture_output=True, check=True, text=True)
    require(result.stdout.strip() == MOMENTUM_BASE, "Momentum base commit mismatch")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: verify_v19_e11_sdk_fap.py <momentum-src> <labmate.fap>", file=sys.stderr)
        return 2
    root, fap = Path(argv[1]), Path(argv[2])
    try:
        verify_git_base(root)
        verify_sources(root)
        size, digest = verify_fap(fap)
    except (OSError, VerificationError, subprocess.CalledProcessError) as exc:
        print(f"V19 E11 SDK/FAP REVIEW NO-GO: {exc}", file=sys.stderr)
        return 1
    print(f"V19 E11 SDK EXPORTED-API/FAP REVIEW PASS | bytes={size} | sha256={digest}")
    print("REVIEW ONLY — NO DEVICE WRITES OR FIRMWARE INSTALLATION")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
