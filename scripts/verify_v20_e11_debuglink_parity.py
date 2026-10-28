#!/usr/bin/env python3
"""Exact GitHub CI FAP identity allowing ONLY .gnu_debuglink CRC variance.

The matched Momentum FBT tool adds --add-gnu-debuglink=labmate_d.elf.
Its 4-byte CRC is calculated from the separate debug ELF, whose paths
and debug notes can vary between GitHub Actions and WSL Ubuntu.

CI reference is the actual 174192-byte artifact from run 40774609065:
raw SHA256 6dbe192ba7d1b0f2b05702c90cf68d791f041f75ed53a6b41135176b6ad4de5b.
We zero ONLY those 4 metadata bytes in memory, compare the SHA256 of
every other byte, and never modify/upload a normalized file.

No hash bypass: differing code, relocations, symbols, .fapmeta, layout,
or any other FAP byte fails the pin. Inspect any failure before retry.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import sys
import zlib

RAW_CI_SHA256 = "6dbe192ba7d1b0f2b05702c90cf68d791f041f75ed53a6b41135176b6ad4de5b"
NORMALIZED_CI_SHA256 = "95d7dee6d1edd37d74c906c476347498e0adc1ae2f20aa408ec26c70bc12f90a"
EXPECTED_BYTES = 174192
DEBUGLINK_PREFIX = b"labmate_d.elf\x00\x00\x00"  # 16-byte name/padding (only CRC differs)


class IdentityFailure(ValueError):
    pass


def normalize_debuglink(data: bytes) -> tuple[bytes, int, list[tuple[str, str]]]:
    """Produce digest input; reject unexpected ELF/debuglink structure.

    Diagnostic section hashes include every real section and are printed on
    mismatch. The normalized bytes differ solely in the 4-byte CRC.
    """
    if len(data) < 52 or data[:6] != b"\x7fELF\x01\x01":
        raise IdentityFailure("Expected ELF32 little-endian binary")
    if struct.unpack_from("<H", data, 18)[0] != 40:
        raise IdentityFailure("Expected ARM ELF architecture")
    shoff = struct.unpack_from("<I", data, 32)[0]
    shentsize, count, shstridx = struct.unpack_from("<HHH", data, 46)
    if shentsize != 40 or count != 17 or shstridx >= count or shoff + count * shentsize > len(data):
        raise IdentityFailure("Unexpected FAP section header layout")
    headers = [struct.unpack_from("<10I", data, shoff + i * shentsize) for i in range(count)]
    nameshdr = headers[shstridx]
    if nameshdr[1] != 3 or nameshdr[4] + nameshdr[5] > len(data):
        raise IdentityFailure("Invalid section name string table")
    names = data[nameshdr[4]:nameshdr[4] + nameshdr[5]]
    target = None
    sections = []
    for sec in headers:
        end = names.find(b"\x00", sec[0])
        if sec[0] >= len(names) or end < 0:
            raise IdentityFailure("Invalid section name offset")
        name = names[sec[0]:end].decode("ascii")
        off, size = sec[4], sec[5]
        if sec[1] != 8 and off + size > len(data):
            raise IdentityFailure("Invalid section data bounds")
        payload = b"" if sec[1] == 8 else data[off:off + size]
        sections.append((name, hashlib.sha256(payload).hexdigest()))
        if name == ".gnu_debuglink":
            if target is not None or sec[1] != 1 or sec[2] != 0 or size != 20:
                raise IdentityFailure("Unexpected .gnu_debuglink section format")
            if payload[:16] != DEBUGLINK_PREFIX:
                raise IdentityFailure("Debuglink name/padding differs from audited CI")
            target = (off + 16, struct.unpack_from("<I", data, off + 16)[0])
    if target is None:
        raise IdentityFailure("The audited .gnu_debuglink section is missing")
    mutable = bytearray(data)
    crc_offset, crc = target
    mutable[crc_offset:crc_offset + 4] = b"\x00\x00\x00\x00"
    return bytes(mutable), crc, sections


def verify_fap(path: Path, require_debug_elf: bool = False) -> str:
    if not path.is_file():
        raise IdentityFailure(f"FAP not found: {path}")
    data = path.read_bytes()
    if len(data) != EXPECTED_BYTES:
        raise IdentityFailure(f"FAP size mismatch: {len(data)} != {EXPECTED_BYTES}")
    raw = hashlib.sha256(data).hexdigest()
    normalized, crc, sections = normalize_debuglink(data)
    canonical = hashlib.sha256(normalized).hexdigest()
    if canonical != NORMALIZED_CI_SHA256:
        print(f"CI raw SHA256:          {RAW_CI_SHA256}", file=sys.stderr)
        print(f"Local raw SHA256:       {raw}", file=sys.stderr)
        print(f"CI normalized SHA256:   {NORMALIZED_CI_SHA256}", file=sys.stderr)
        print(f"Local normalized SHA256:{canonical}", file=sys.stderr)
        for name, digest in sections:
            print(f"SECTION {name:24} {digest}", file=sys.stderr)
        raise IdentityFailure("Other ELF bytes differ, not solely the debuglink CRC; NO USB")
    if require_debug_elf:
        debug_elf = path.with_name("labmate_d.elf")
        if not debug_elf.is_file():
            raise IdentityFailure("Debug ELF required to validate local debuglink CRC")
        calc = 0
        with debug_elf.open("rb") as f:
            while piece := f.read(1024 * 1024):
                calc = zlib.crc32(piece, calc)
        if (calc & 0xFFFFFFFF) != crc:
            raise IdentityFailure("Embedded debuglink CRC does not match the local debug ELF")
    print(f"CI_BYTE_PARITY_EXCEPT_DEBUGLINK_CRC: PASS")
    print(f"CI_NORMALIZED_SHA256={canonical}")
    print(f"VERIFIED_E11_RAW_SHA256={raw}")
    if raw != RAW_CI_SHA256:
        print("ONLY_VARIANT: 4-byte .gnu_debuglink CRC (verified non-runtime metadata)")
    return raw


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("fap", type=Path)
    p.add_argument("--check-local-debug-elf", action="store_true")
    args = p.parse_args()
    try:
        verify_fap(args.fap, args.check_local_debug_elf)
    except (IdentityFailure, OSError, UnicodeDecodeError, struct.error) as exc:
        print(f"V20 E11 CI CONTENT PARITY NO-GO: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
