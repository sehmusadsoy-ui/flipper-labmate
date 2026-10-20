#!/usr/bin/env python3
"""Read-only, fail-closed review of a v1.9 E11 FAP Actions artifact.

Accepts an extracted 4-file review directory or the Actions artifact ZIP.
Only validates provenance consistency, checksum and ARM ELF header: it does
NOT prove a trusted publisher, matched installed firmware or safe install.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys
import zipfile

MOMENTUM_BASE = "d3f89dfe2ef6b01839201598e9be1590cba80322"
FAP_NAME = "labmate-v1.9DEV-E11-review.fap"
FILES = {FAP_NAME, "SHA256SUMS.txt", "PROVENANCE.txt", "READ_ME_FIRST.txt"}
MAX_FAP_SIZE = 4_000_000


class ReviewError(ValueError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ReviewError(message)


def read_bundle(path: Path) -> dict[str, bytes]:
    if path.is_dir():
        require({p.name for p in path.iterdir()} == FILES,
                "review directory has missing or unexpected items")
        out = {}
        for name in FILES:
            entry = path / name
            require(entry.is_file() and not entry.is_symlink(),
                    f"unsafe or missing review member: {name}")
            maximum = MAX_FAP_SIZE if name == FAP_NAME else 8192
            require(entry.stat().st_size <= maximum, f"oversized member: {name}")
            out[name] = entry.read_bytes()
        return out

    require(path.is_file() and not path.is_symlink(), "review ZIP not found")
    require(zipfile.is_zipfile(path), "review input must be a directory or ZIP")
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            names = [i.filename for i in entries]
            require(len(names) == len(FILES) and set(names) == FILES,
                    "review ZIP has missing, duplicate, nested or unexpected files")
            out = {}
            for info in entries:
                maximum = MAX_FAP_SIZE if info.filename == FAP_NAME else 8192
                require(not info.is_dir() and info.file_size <= maximum,
                        f"unsafe or oversized ZIP member: {info.filename}")
                data = archive.read(info)
                require(len(data) <= maximum, "decompressed review member too large")
                out[info.filename] = data
            return out
    except (zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        raise ReviewError(f"unreadable review ZIP: {exc}") from exc


def verify_bundle(path: Path, source_sha: str) -> tuple[int, str]:
    require(re.fullmatch(r"[a-f0-9]{40}", source_sha) is not None,
            "expected source commit must be a full lowercase SHA-1")
    bundle = read_bundle(path)
    fap = bundle[FAP_NAME]
    require(64 <= len(fap) <= MAX_FAP_SIZE, "invalid FAP payload size")
    require(fap[:4] == b"\x7fELF" and fap[4:6] == b"\x01\x01",
            "not a 32-bit little-endian ELF")
    require(int.from_bytes(fap[18:20], "little") == 40,
            "FAP machine is not ARM")

    digest = hashlib.sha256(fap).hexdigest()
    checksum = bundle["SHA256SUMS.txt"].decode("ascii", errors="strict")
    require(re.fullmatch(rf"{digest}  {re.escape(FAP_NAME)}\r?\n?", checksum)
            is not None, "FAP SHA256SUMS mismatch or unexpected checksum format")

    provenance = bundle["PROVENANCE.txt"].decode("ascii", errors="strict")
    rows = provenance.splitlines()
    require(len(rows) == 3 and all("=" in row for row in rows),
            "invalid build provenance fields")
    kv = dict(row.split("=", 1) for row in rows)
    require(len(kv) == 3 and set(kv) ==
            {"SOURCE_SHA", "MOMENTUM_BASE", "GITHUB_RUN_ID"},
            "unexpected or duplicate provenance fields")
    require(kv["SOURCE_SHA"] == source_sha,
            "review artifact built from a different LabMate commit")
    require(kv["MOMENTUM_BASE"] == MOMENTUM_BASE,
            "review artifact used an unexpected Momentum base")
    require(re.fullmatch(r"[1-9][0-9]*", kv["GITHUB_RUN_ID"]) is not None,
            "review artifact missing positive GitHub run ID")

    readme = bundle["READ_ME_FIRST.txt"].decode("utf-8", errors="strict")
    require("E11 exact patched Momentum ABI ONLY" in readme and
            "NOT authorized for FAP installation" in readme,
            "missing explicit no-install warning")
    return len(fap), digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="review ZIP or extracted review folder")
    parser.add_argument("--source-sha", required=True,
                        help="expected full GitHub commit SHA shown in the PR")
    args = parser.parse_args(argv)
    try:
        size, digest = verify_bundle(args.bundle, args.source_sha)
    except (ReviewError, OSError, UnicodeError) as exc:
        print(f"V19 FAP BUNDLE REVIEW NO-GO: {exc}", file=sys.stderr)
        return 1
    print(f"V19 FAP BUNDLE REVIEW PASS | bytes={size} | sha256={digest}")
    print("METADATA+ELF ONLY; NO DEVICE, FIRMWARE OR SD WRITES")
    print("NOT a cryptographic publisher attestation or matched-device approval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
