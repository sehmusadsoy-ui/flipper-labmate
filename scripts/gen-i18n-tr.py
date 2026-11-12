#!/usr/bin/env python3
"""Build files/i18n_tr.bin from i18n/tr.tsv (LabMate Turkish UI table).

Layout (little endian), loaded into RAM only while Turkish is selected:
  "LMT1" | u16 count | u16 reserved
  count x { u32 fnv1a(english) | u16 offset | u16 reserved }   sorted by hash
  UTF-8 Turkish strings, NUL-terminated; offsets are relative to this blob.
"""
import struct, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent

def fnv1a(data: bytes) -> int:
    h = 0x811C9DC5
    for b in data:
        h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
    return h

def main() -> int:
    rows = []
    for line in (root / "i18n/tr.tsv").read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        en, tr = line.split("\t")
        rows.append((fnv1a(en.encode()), en, tr))
    hashes = [r[0] for r in rows]
    if len(set(hashes)) != len(hashes):
        raise SystemExit("hash collision in table")
    rows.sort()
    blob = bytearray()
    entries = bytearray()
    for h, _, tr in rows:
        entries += struct.pack("<IHH", h, len(blob), 0)
        blob += tr.encode() + b"\0"
    if len(blob) > 0xFFFF:
        raise SystemExit("blob too large")
    out = b"LMT1" + struct.pack("<HH", len(rows), 0) + entries + blob
    path = root / "files/i18n_tr.bin"
    path.write_bytes(out)
    print(f"{path.relative_to(root)}: {len(rows)} strings, {len(out)} bytes")
    return 0

if __name__ == "__main__":
    sys.exit(main())
