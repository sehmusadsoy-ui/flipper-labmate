#!/usr/bin/env python3
"""Reject independently corrupted ELF/relocation copies of a native LabMate FAP.

Usage: python3 scripts/test-v20-e11-section-layout.py /path/to/labmate.fap
Only temporary .bin files are written. The input FAP is never changed.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fap", type=Path)
    args = parser.parse_args()
    verifier_path = Path(__file__).with_name("verify-labmate-e11-sections.py")
    spec = importlib.util.spec_from_file_location("section_verifier", verifier_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = args.fap.read_bytes()
    baseline = module.verify(args.fap)
    table = struct.unpack_from("<I", original, 32)[0]
    stride, count, names_index = struct.unpack_from("<HHH", original, 46)
    headers = [struct.unpack_from("<10I", original, table + i * stride) for i in range(count)]
    names_header = headers[names_index]
    names = original[names_header[4]:names_header[4] + names_header[5]]
    labels = [names[h[0]:names.index(0, h[0])].decode("ascii") for h in headers]
    index = {name: i for i, name in enumerate(labels)}
    text = headers[index[".text"]]
    rel_index = index[".rel.text.ui"]
    rel_header = headers[rel_index]
    symbols = headers[index[".symtab"]]
    first_info = struct.unpack_from("<I", original, rel_header[4] + 4)[0]
    ordinary = original[rel_header[4]:rel_header[4] + rel_header[5]]
    internal_symbol = None
    for _, info in struct.iter_unpack("<II", ordinary):
        symbol_offset = symbols[4] + 16 * (info >> 8)
        owner = struct.unpack_from("<H", original, symbol_offset + 14)[0]
        if owner:
            internal_symbol = (symbol_offset, owner)
            break
    if internal_symbol is None:
        raise RuntimeError("Native fixture has no internal relocation symbol")
    symbol_offset, owner = internal_symbol

    fast_index = index[".fast.rel.text.ui"]
    fast = headers[fast_index]
    fast_records = []
    cursor = fast[4] + 5
    for _ in range(struct.unpack_from("<I", original, fast[4] + 1)[0]):
        internal = bool(original[cursor] & 0x80)
        offset_count = struct.unpack_from("<I", original, cursor + (9 if internal else 5))[0]
        offsets_start = cursor + (13 if internal else 9)
        fast_records.append((internal, cursor, offsets_start))
        cursor = offsets_start + 3 * offset_count
    internal_fast_record = next(record for internal, record, _ in fast_records if internal)
    external_fast_record = next(record for internal, record, _ in fast_records if not internal)
    first_fast_write = fast_records[0][2]
    external_hash = struct.unpack_from("<I", original, external_fast_record + 1)[0]

    def changed(offset, value, width=4):
        data = bytearray(original)
        data[offset:offset + width] = value.to_bytes(width, "little")
        return data

    cases = {
        "entry_outside_primary_text": (changed(24, text[5] + 1), "Entry must remain"),
        "allocation_over_64k": (
            changed(table + index[".bss"] * stride + 20, 65537), "allocation exceeds"),
        "relocation_symbol_out_of_range": (
            changed(rel_header[4] + 4, ((symbols[5] // 16) << 8) | (first_info & 255)),
            "symbol index out of range"),
        "relocation_target_section_out_of_range": (
            changed(table + rel_index * stride + 28, count), "invalid ordinary relocation table"),
        "relocation_offset_out_of_bounds": (
            changed(rel_header[4], headers[rel_header[7]][5]), "relocation write out of bounds"),
        "truncated_section_table": (
            original[:table + stride * count - 1], "truncated section header table"),
        "unsupported_ordinary_relocation_type": (
            changed(rel_header[4] + 4, (first_info & ~255) | 127), "unsupported E11 relocation type"),
        "ordinary_symbol_in_unloaded_section": (
            changed(symbol_offset + 14, index[".strtab"], width=2), "section E11 does not load"),
        "ordinary_symbol_value_out_of_bounds": (
            changed(symbol_offset + 4, headers[owner][5] + 4), "symbol address out of bounds"),
        "fast_unknown_version": (changed(fast[4], 2, width=1), "fast relocation parity mismatch"),
        "fast_bad_record_count": (changed(fast[4] + 1, 0), "fast relocation parity mismatch"),
        "fast_internal_target_unloaded": (
            changed(internal_fast_record + 1, index[".strtab"]), "fast relocation parity mismatch"),
        "fast_external_symbol_hash_changed": (
            changed(external_fast_record + 1, external_hash ^ 1), "fast relocation parity mismatch"),
        "fast_relocation_offset_out_of_bounds": (
            changed(first_fast_write, headers[rel_header[7]][5], width=3), "fast relocation parity mismatch"),
        "fast_record_truncated": (
            changed(table + fast_index * stride + 20, fast[5] - 1), "fast relocation parity mismatch"),
    }
    rejected = []
    with tempfile.TemporaryDirectory(prefix="labmate-section-negative-") as directory:
        for name, (malformed, reason) in cases.items():
            target = Path(directory) / (name + ".bin")
            target.write_bytes(malformed)
            try:
                module.verify(target)
            except ValueError as error:
                if reason not in str(error):
                    raise RuntimeError(f"Wrong rejection for {name}: {error}") from error
                rejected.append(name)
            else:
                raise RuntimeError("Verifier accepted corrupted native artifact: " + name)
    if args.fap.read_bytes() != original:
        raise RuntimeError("Input artifact changed while testing")
    print(json.dumps({
        "result": "PASS", "positive_native_artifact": True,
        "sha256": hashlib.sha256(original).hexdigest(),
        "ordinary_relocations_checked": baseline["ordinary_relocations_checked"],
        "fast_relocation_sections_checked": baseline["fast_relocation_sections_checked"],
        "negative_cases_rejected": rejected,
    }, indent=2))


if __name__ == "__main__":
    main()
