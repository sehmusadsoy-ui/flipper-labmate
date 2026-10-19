#!/usr/bin/env python3
"""Strict read-only Windows PC snapshot/backups verification for v1.9 staging.

This is invoked as a FILE, never through PowerShell's lossy python -c
argument quotation. NO serial imports, COM access, device write, or PC write.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from prepare_v19_e11_pc_only import verify_backups


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active-v18-backup", type=Path, required=True)
    parser.add_argument("--historical-e11-backup", type=Path, required=True)
    parser.add_argument("--data-snapshot", type=Path, required=True)
    args = parser.parse_args()
    try:
        files, size = verify_backups(
            args.active_v18_backup,
            args.historical_e11_backup,
            args.data_snapshot,
        )
        if (files, size) != (12, 2128):
            raise ValueError("snapshot inventory changed from pinned 12 files/2128 bytes")
    except Exception as exc:
        detail = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("V19 E11 WINDOWS PC BACKUPS READ-ONLY NO-GO: " + detail, file=sys.stderr)
        return 1
    print(f"PC_BACKUPS_PASS: {files} files, {size} bytes")
    print("WINDOWS_PC_BACKUPS_RO: PASS | DEVICE_WRITES: ZERO | PC_WRITES: ZERO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
