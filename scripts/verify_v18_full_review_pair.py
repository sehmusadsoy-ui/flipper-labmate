#!/usr/bin/env python3
"""Read-only verification of the actual FULL v1.8DEV Momentum/FAP/JS pair.

This is intentionally NOT the old minimal-updater PowerShell verifier.
Requires exact CI run and LabMate source from a *separately trusted* source.
No USB/COM, install, firmware writes, SD access, or release mutations.
"""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import re
import tarfile
import tempfile

from check_v18_full_update_bundle import audit

PIN = "d3f89dfe2ef6b01839201598e9be1590cba80322"
MNTM012 = "e1784e7418d8b074e971983ceb6fef0f37e52ae4"
# This fingerprint was independently compared with the official MNTM-012
# radio binary by the full no-flash CI. It is not itself an authenticity proof.
OFFICIAL_RADIO_SHA256 = "134a9af448d2bc35995600c9e95723a387c144c2d1adea671086f16f95d327df"
BINARIES = ("labmate.fap", "js_gpio.module", "firmware.dfu", "firmware-full-update.tgz")
REQUIRED = set(BINARIES) | {"SHA256SUMS.txt", "PROVENANCE.txt", "READ_ME_FIRST.txt"}
SHA_LINE = re.compile(r"^([a-fA-F0-9]{64})  \*?([a-z0-9_.-]+)$")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _meta(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        # Provenance also contains narrative notes, not just key/value lines.
        if ": " not in line:
            continue
        key, value = line.split(": ", 1)
        if not key or key in out:
            raise ValueError("duplicate or empty provenance key")
        out[key] = value
    return out


def verify(
    directory: Path,
    expected_source: str,
    expected_run: int,
    *,
    expected_radio_sha256: str = OFFICIAL_RADIO_SHA256,
) -> dict[str, str]:
    if not re.fullmatch(r"[0-9a-f]{40}", expected_source):
        raise ValueError("exact lower-case 40-hex LabMate commit required")
    if expected_run <= 0:
        raise ValueError("positive, independently sourced Actions run ID required")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_radio_sha256):
        raise ValueError("bad independent radio SHA256")
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("extracted full candidate folder required")
    present = set()
    for entry in directory.iterdir():
        if entry.is_symlink() or not entry.is_file() or entry.name in present:
            raise ValueError("unsafe/non-regular or duplicated extracted entry")
        present.add(entry.name)
    if present != REQUIRED:
        raise ValueError("missing/extra files: " + repr(sorted(present ^ REQUIRED)))

    checksums: dict[str, str] = {}
    for line in (directory / "SHA256SUMS.txt").read_text("utf-8").splitlines():
        match = SHA_LINE.fullmatch(line)
        if not match:
            raise ValueError("bad checksum manifest syntax")
        sha, name = match.groups()
        if name not in BINARIES or name in checksums:
            raise ValueError("unknown or duplicate manifest binary")
        checksums[name] = sha.lower()
    if set(checksums) != set(BINARIES):
        raise ValueError("missing manifest binary entry")
    for name in BINARIES:
        target = directory / name
        if not target.stat().st_size:
            raise ValueError("empty candidate binary: " + name)
        if _sha(target.read_bytes()) != checksums[name]:
            raise ValueError("SHA256 mismatch: " + name)

    meta = _meta((directory / "PROVENANCE.txt").read_text("utf-8"))
    required_fields = {
        "LabMate commit": expected_source,
        "Momentum base": PIN,
        "Installed Momentum012 source": MNTM012,
        "Actions run": str(expected_run),
    }
    for field, value in required_fields.items():
        if meta.get(field) != value:
            raise ValueError("provenance mismatch: " + field)
    if not re.fullmatch(r"[0-9a-f]{64}", meta.get("E11 firmware diff SHA256", "")):
        raise ValueError("missing exact E11 firmware source diff fingerprint")
    note = (directory / "READ_ME_FIRST.txt").read_text("utf-8")
    for phrase in ("NOT A RELEASE", "DO NOT FLASH", "NO PHYSICAL ACCEPTANCE",
                   "Never mix this matched FAP with unpatched Momentum firmware"):
        if phrase not in note:
            raise ValueError("safety warning missing: " + phrase)

    # Existing actual full TGZ audit handles archive path safety, DFU,
    # manifest, option-byte structure and resources. Supply ONLY the radio
    # bytes in the archive and compare their digest to the separately known
    # MNTM-012 fingerprint, never accept a self-attested radio digest.
    tgz = directory / "firmware-full-update.tgz"
    with tarfile.open(tgz, "r:gz") as outer:
        radio_entries = [m for m in outer.getmembers()
                         if m.name.endswith("/radio.bin") and m.isfile()]
        if len(radio_entries) != 1 or radio_entries[0].size > 2_000_000:
            raise ValueError("exactly one bounded embedded radio required")
        fp = outer.extractfile(radio_entries[0])
        if fp is None:
            raise ValueError("unreadable embedded radio")
        radio = fp.read()
    if _sha(radio) != expected_radio_sha256:
        raise ValueError("embedded radio differs from independently trusted MNTM-012 SHA")
    with tempfile.TemporaryDirectory(prefix="labmate_full_pair_check_") as temp:
        radio_file = Path(temp) / "radio.bin"
        radio_file.write_bytes(radio)
        result = audit(tgz, directory / "firmware.dfu", radio_file)
    if result["dfu_sha256"] != checksums["firmware.dfu"]:
        raise ValueError("full TGZ does not embed checked DFU")
    return {
        "LabMate commit": expected_source,
        "Actions run": str(expected_run),
        "E11 firmware diff SHA256": meta["E11 firmware diff SHA256"],
        **{name: checksums[name] for name in BINARIES},
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    p.add_argument("--expected-source", required=True)
    p.add_argument("--expected-run", type=int, required=True)
    args = p.parse_args()
    try:
        found = verify(args.directory, args.expected_source, args.expected_run)
    except (OSError, ValueError, UnicodeError, tarfile.TarError) as exc:
        p.exit(1, "FULL v1.8 REVIEW PAIR REFUSED: " + str(exc) + "\n")
    for key, value in found.items():
        print(key + ": " + value)
    print("FULL DEV PAIR READ-ONLY VERIFICATION PASS. NOT APPROVED FOR FLASH/RELEASE.")
    print("SHA256 self-consistency does NOT authenticate an untrusted download.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
