#!/usr/bin/env python3
"""Verify split-section FAP layout and pinned Momentum E11 relocation parity."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
from typing import NamedTuple


SHF_ALLOC = 0x02
SHF_EXECINSTR = 0x04
SHF_INFO_LINK = 0x40
SHT_PROGBITS = 1
SHT_SYMTAB = 2
SHT_STRTAB = 3
SHT_RELA = 4
SHT_NOBITS = 8
SHT_REL = 9
STT_FUNC = 2
MAX_ALLOCATION = 64 * 1024
CODE_SECTIONS = (".text", ".text.ui", ".text.core")
ARM_SKIPPED = (".ARM.", ".rel.ARM.", ".fast.rel.ARM.")

# elf_relocate_symbol in the pinned E11 elf_file.c. All supported writes
# touch four bytes, either one 32-bit value or two Thumb halfwords.
RELOCATION_WIDTHS = {
    2: 4,   # R_ARM_ABS32
    3: 4,   # R_ARM_REL32
    10: 4,  # R_ARM_THM_PC22
    28: 4,  # R_ARM_CALL
    30: 4,  # R_ARM_THM_JUMP24
    38: 4,  # R_ARM_TARGET1
    47: 4,  # R_ARM_THM_MOVW_ABS_NC
    48: 4,  # R_ARM_THM_MOVT_ABS
}


class Section(NamedTuple):
    name_offset: int
    kind: int
    flags: int
    address: int
    offset: int
    size: int
    link: int
    info: int
    alignment: int
    entry_size: int


class Symbol(NamedTuple):
    name_offset: int
    value: int
    size: int
    info: int
    other: int
    section_index: int


def require(condition, message):
    if not condition:
        raise ValueError(message)


def string_at(table, offset):
    require(offset < len(table), "ELF string offset out of bounds")
    end = table.find(b"\0", offset)
    require(end >= 0, "Unterminated ELF string")
    return table[offset:end].decode("ascii")


def gnu_symbol_hash(name):
    value = 0x1505
    for char in name:
        value = (33 * value + ord(char)) & 0xFFFFFFFF
    return value


def encode_fast_relocations(groups):
    # Canonical format/order from the pinned SDK scripts/fastfap.py.
    payload = bytearray(struct.pack("<BI", 1, len(groups)))
    for (section_index, value, kind, name), offsets in groups.items():
        if section_index:
            payload.extend(struct.pack("<BII", 0x80 | kind, section_index, value))
        else:
            payload.extend(struct.pack("<BI", kind, gnu_symbol_hash(name)))
        payload.extend(struct.pack("<I", len(offsets)))
        for offset in offsets:
            payload.extend(offset.to_bytes(3, "little"))
    return payload


def verify(path):
    data = path.read_bytes()
    require(len(data) >= 52 and data[:7] == b"\x7fELF\x01\x01\x01",
            "Expected a complete ELF32 little-endian header")
    require(struct.unpack_from("<HHI", data, 16) == (1, 40, 1),
            "Expected ARM32 ET_REL version 1")
    entry = struct.unpack_from("<I", data, 24)[0]
    table_offset = struct.unpack_from("<I", data, 32)[0]
    header_size, _, _, stride, count, names_index = struct.unpack_from("<6H", data, 40)
    require(header_size == 52 and stride == 40 and 0 < names_index < count
            and table_offset >= header_size and table_offset + stride * count <= len(data),
            "Invalid or truncated section header table")
    headers = [Section(*struct.unpack_from("<10I", data, table_offset + i * stride))
               for i in range(count)]

    def section_bytes(section):
        return data[section.offset:section.offset + section.size]

    for section in headers:
        if section.kind != SHT_NOBITS:
            require(section.offset + section.size <= len(data), "Section payload out of bounds")
    require(headers[names_index].kind == SHT_STRTAB, "Invalid section name table")
    names = section_bytes(headers[names_index])
    labels = [string_at(names, section.name_offset) for section in headers]
    require(labels[0] == "" and headers[0].kind == 0 and len(set(labels)) == count,
            "Invalid null section or duplicate section names")
    sections = dict(zip(labels, headers))
    loaded = {index for index, (name, section) in enumerate(zip(labels, headers))
              if section.flags & SHF_ALLOC and not name.startswith(ARM_SKIPPED)}
    for index in loaded:
        require(headers[index].size <= MAX_ALLOCATION, f"{labels[index]}: allocation exceeds 64 KiB")
    for name in CODE_SECTIONS:
        section = sections.get(name)
        require(section is not None and section.kind == SHT_PROGBITS and section.size > 0
                and section.flags & (SHF_ALLOC | SHF_EXECINSTR) == (SHF_ALLOC | SHF_EXECINSTR),
                f"{name}: native executable section missing")
        require(".rel" + name in sections and ".fast.rel" + name in sections,
                f"{name}: relocation tables missing")
    require(sections[".text"].address == 0, "Primary .text must start at address zero")
    require(not any(name.startswith(".gnu.lto") for name in labels), "Unexpected LTO data")

    symtab = sections.get(".symtab")
    require(symtab is not None and symtab.kind == SHT_SYMTAB and symtab.entry_size == 16
            and symtab.size % 16 == 0 and 0 < symtab.link < count
            and headers[symtab.link].kind == SHT_STRTAB and labels[symtab.link] == ".strtab",
            "Invalid symbol/string table structure")
    strings = section_bytes(headers[symtab.link])
    symbols = [Symbol(*values) for values in struct.iter_unpack("<IIIBBH", section_bytes(symtab))]
    symbol_names = [string_at(strings, symbol.name_offset) for symbol in symbols]
    entries = [symbol for name, symbol in zip(symbol_names, symbols) if name == "labmate_app"]
    require(len(entries) == 1, "Expected one labmate_app entry symbol")
    app = entries[0]
    require(0 < app.section_index < count and labels[app.section_index] == ".text"
            and app.info & 0xF == STT_FUNC and entry == app.value and entry & 1
            and app.size > 0 and (entry & ~1) + app.size <= sections[".text"].size,
            "Entry must remain in primary .text")

    ordinary_count = 0
    active_count = 0
    expected_fast = {}
    for name, section in sections.items():
        require(section.kind != SHT_RELA, "E11 FAP does not support RELA relocations")
        if section.kind != SHT_REL:
            require(not name.startswith(".rel."), f"{name}: expected an ordinary REL table")
            continue
        require(section.entry_size == 8 and section.size % 8 == 0 and section.size > 0
                and 0 < section.info < count and 0 < section.link < count
                and headers[section.link] is symtab and section.flags & SHF_INFO_LINK
                and not section.flags & SHF_ALLOC,
                f"{name}: invalid ordinary relocation table")
        target = headers[section.info]
        require(name == ".rel" + labels[section.info], f"{name}: relocation target name/index mismatch")
        ignored = name.startswith(ARM_SKIPPED)
        require(ignored or section.info in loaded, f"{name}: relocation target is not loaded")
        groups = {}
        for position, info in struct.iter_unpack("<II", section_bytes(section)):
            symbol_index, kind = info >> 8, info & 0xFF
            require(symbol_index < len(symbols), f"{name}: relocation symbol index out of range")
            require(kind < 128 and (ignored or kind in RELOCATION_WIDTHS),
                    f"{name}: unsupported E11 relocation type {kind}")
            require(position < (1 << 24) and position + RELOCATION_WIDTHS.get(kind, 4) <= target.size,
                    f"{name}: relocation write out of bounds")
            symbol = symbols[symbol_index]
            symbol_name = symbol_names[symbol_index]
            owner = symbol.section_index
            if owner == 0:
                require(bool(symbol_name) and symbol.value == 0, f"{name}: invalid external symbol")
            else:
                require(owner < count and (ignored or owner in loaded),
                        f"{name}: relocation symbol points to a section E11 does not load")
                if not ignored:
                    symbol_start = symbol.value & ~1 if symbol.info & 0xF == STT_FUNC else symbol.value
                    require(headers[owner].size > 0 and symbol_start + symbol.size <= headers[owner].size
                            and (symbol.info & 0xF != STT_FUNC or symbol_start < headers[owner].size),
                            f"{name}: relocation symbol address out of bounds")
            groups.setdefault((owner, symbol.value, kind, symbol_name), []).append(position)
            ordinary_count += 1
            active_count += not ignored
        expected_fast[".fast" + name] = encode_fast_relocations(groups)

    actual_fast = {name for name in labels if name.startswith(".fast.rel")}
    require(actual_fast == expected_fast.keys(), "Ordinary and fast relocation section sets differ")
    for name, expected in expected_fast.items():
        section = sections[name]
        require(section.kind == SHT_PROGBITS and not section.flags & (SHF_ALLOC | SHF_INFO_LINK),
                f"{name}: invalid fast relocation section header")
        require(section_bytes(section) == expected, f"{name}: fast relocation parity mismatch")

    alloc = {labels[index]: headers[index].size for index in sorted(loaded)}
    transient = sum(sections[name].size for name in actual_fast if not name.startswith(ARM_SKIPPED))
    debug_link = sections.get(".gnu_debuglink")
    require(debug_link is not None and debug_link.kind == SHT_PROGBITS
            and not debug_link.flags & (SHF_ALLOC | SHF_INFO_LINK), "Invalid debug link section")
    return {
        "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "entry": entry,
        "allocations": alloc, "largest_allocation": max(alloc.values()),
        "ordinary_relocations_checked": ordinary_count,
        "fast_relocation_sections_checked": len(actual_fast),
        "loader_relocations_checked": active_count,
        "preload_payload_lower_bound": sum(alloc.values()) + transient + debug_link.size,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fap", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    try:
        result = verify(args.fap)
        if args.json:
            require(args.json.resolve() != args.fap.resolve(), "JSON output must not overwrite the FAP")
            args.json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.exit(1, f"E11 FAP verification failed: {error}\n")
    print(json.dumps(result, indent=2))
