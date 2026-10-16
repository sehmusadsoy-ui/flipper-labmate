#!/usr/bin/env python3
"""STRICT offline Momentum resource TAR vs embedded Manifest consistency audit.

Tests ORIGINAL full E11 updater and FAP-excluded REVIEW derivative. In normal
Momentum builds, Manifest records contain file MD5, size and path; a tar member
is not valid merely because SHA256 was pinned in a separate review file.

Known real COM7 OLD Manifest lists apps/Tools/labmate.fap for deletion.
The SPLIT derived tar removes the NEW FAP but historically leaves its new
Manifest unchanged; this is at least an independent mismatch risk.
NO USB/device writes. Neither archive may be installed with this tool.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import re
import tarfile

from audit_v18_e11_resource_impact import FAP_PATH, JS_PATH, normalized
from preflight_v18_e11_local import ARTIFACTS
from stage_v18_e11_review_only import inspect_updater

MAX_TAR_BYTES = 90_000_000
MAX_UNPACKED_BYTES = 110_000_000
MAX_MEMBERS = 20000
RECORD = re.compile(rb"F:([a-fA-F0-9]{32}):([0-9]{1,10}):(.+)")
DIRECTORY = re.compile(rb"D:(.+)")
TIME = re.compile(rb"T:[0-9]{1,16}")


def _path(value: bytes) -> str:
    if not value or len(value) > 700 or b"\x00" in value:
        raise ValueError("invalid manifest entry name")
    try:
        decoded = value.decode("utf-8", errors="strict")
    except UnicodeError:
        raise ValueError("manifest name not UTF-8") from None
    return normalized(decoded, False).lower()


def scan_packed_resources(data: bytes) -> tuple[dict[str, tuple[str, int]], dict[str, tuple[str, int]]]:
    """Parse resources.tar.gz in memory; return TAR files vs its Manifest."""
    if len(data) == 0 or len(data) > MAX_TAR_BYTES:
        raise ValueError("missing or oversized resources TAR")
    members: dict[str, tuple[str, int]] = {}
    raw_manifest: bytes | None = None
    total = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for i, info in enumerate(archive):
            if i >= MAX_MEMBERS:
                raise ValueError("too many packed resource nodes")
            if not (info.isfile() or info.isdir()):
                raise ValueError("unsafe packed resource node type")
            name = normalized(info.name, info.isdir())
            if not name:
                continue
            key = name.lower()
            if info.isdir():
                continue
            if key in members or key == "manifest" and raw_manifest is not None:
                raise ValueError("duplicate packed resource file")
            if info.size < 0 or info.size > MAX_TAR_BYTES:
                raise ValueError("unsafe packed resource file size")
            total += info.size
            if total > MAX_UNPACKED_BYTES:
                raise ValueError("unpacked resources exceed bounded limit")
            stream = archive.extractfile(info)
            if stream is None:
                raise ValueError("unreadable resource data")
            body = stream.read(info.size + 1)
            if len(body) != info.size:
                raise ValueError("resource TAR size mismatch")
            if key == "manifest":
                if len(body) > 4_000_000:
                    raise ValueError("packed Manifest oversized")
                raw_manifest = body
            else:
                members[key] = (hashlib.md5(body).hexdigest(), len(body))
    if not members or raw_manifest is None:
        raise ValueError("packaged resources lack data/Manifest")

    declared: dict[str, tuple[str, int]] = {}
    declared_directories: set[str] = set()
    version_seen = False
    timestamp_seen = False
    for line in raw_manifest.splitlines():
        if not line:
            raise ValueError("blank resource Manifest line")
        if line == b"V:0":
            if version_seen:
                raise ValueError("duplicate packed Manifest version")
            version_seen = True
        elif TIME.fullmatch(line):
            if timestamp_seen:
                raise ValueError("duplicate packed Manifest timestamp")
            timestamp_seen = True
        elif (m := RECORD.fullmatch(line)) is not None:
            name = _path(m.group(3))
            size = int(m.group(2))
            if size > 0xFFFFFFFF or name in declared or name == "manifest":
                raise ValueError("invalid/duplicate declared resource")
            declared[name] = (m.group(1).lower().decode("ascii"), size)
        elif (m := DIRECTORY.fullmatch(line)) is not None:
            name = _path(m.group(1).rstrip(b"/"))
            if name in declared_directories or name in declared:
                raise ValueError("duplicate declared directory")
            declared_directories.add(name)
        else:
            raise ValueError("unrecognized packed resource Manifest entry")
    if not version_seen or not timestamp_seen or not declared or not declared_directories:
        raise ValueError("missing packed resource manifest metadata")
    return members, declared


def check_consistency(
    resource_tar: bytes,
    *,
    should_include_fap: bool,
    expected_fap_sha256: str | None = None,
    expected_js_sha256: str | None = None,
) -> dict[str, str | int]:
    actual, declared = scan_packed_resources(resource_tar)
    fap = FAP_PATH.lower()
    js = JS_PATH.lower()
    missing = set(declared) - set(actual)
    unlisted = set(actual) - set(declared)
    mismatched = {
        name for name in set(actual) & set(declared) if actual[name] != declared[name]
    }
    if unlisted or mismatched:
        raise ValueError(
            "packed manifest missing or mismatching resource contents:"
            " unlisted_actual=" + str(len(unlisted)) +
            " wrong_md5_size=" + str(len(mismatched)) +
            " undeclared_labmate=" + str(fap in unlisted) +
            " undeclared_js_gpio=" + str(js in unlisted) +
            " wrong_labmate=" + str(fap in mismatched) +
            " wrong_js_gpio=" + str(js in mismatched) +
            " unlisted_expected_firstboot=" + str("dolphin/firstboot.bin" in unlisted) +
            " unlisted_expected_manifest_autogen=" + str("Manifest".lower() in unlisted)
        )
    if js not in actual or js not in declared:
        raise ValueError("packed native JS GPIO resource not declared")
    if expected_js_sha256 is not None and not re.fullmatch(r"[a-f0-9]{64}",expected_js_sha256):
        raise ValueError("bad independent JS fingerprint")
    if expected_fap_sha256 is not None and not re.fullmatch(r"[a-f0-9]{64}",expected_fap_sha256):
        raise ValueError("bad independent FAP fingerprint")

    if should_include_fap:
        if missing:
            raise ValueError("original full updater Manifest declares absent files")
        if fap not in actual or fap not in declared:
            raise ValueError("full update lacks declared LabMate FAP")
        pair = "FULL_BUNDLE_DECLARED_AND_PRESENT"
    else:
        if fap in actual:
            raise ValueError("FAP-excluded bundle unexpectedly still contains LabMate")
        if missing != {fap}:
            raise ValueError("split archive has unexpected packed Manifest mismatch")
        pair = "SPLIT_MANIFEST_STILL_DECLARES_REMOVED_FAP"
    return {
        "packed_actual_resource_files": len(actual),
        "packed_manifest_declared_files": len(declared),
        "packed_manifest_orphan_references": len(missing),
        "packed_manifest_unlisted_files": len(unlisted),
        "packed_manifest_wrong_file_md5_or_size": len(mismatched),
        "packed_actual_labmate_fap_present": "YES" if fap in actual else "NO",
        "packed_manifest_declares_labmate_fap": "YES" if fap in declared else "NO",
        "labmate_pairing_in_resources": pair,
        "physical_install_approved": "NO",
        "old_device_fap_preserved_by_resource_update": "NO",
    }


def _archive_member_sha(resource_tar: bytes, member_path: str) -> str:
    with tarfile.open(fileobj=io.BytesIO(resource_tar), mode="r:gz") as arc:
        found: list[str] = []
        for item in arc:
            if item.isfile() and normalized(item.name, False).lower() == member_path.lower():
                stream = arc.extractfile(item)
                if stream is None or item.size > 10_000_000:
                    raise ValueError("unreadable oversized paired resource")
                data = stream.read(item.size + 1)
                if len(data) != item.size:
                    raise ValueError("paired resource truncated")
                found.append(hashlib.sha256(data).hexdigest())
        if len(found) != 1:
            raise ValueError("paired resource not unique")
        return found[0]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--full-updater", required=True)
    p.add_argument("--split-updater", required=True)
    args = p.parse_args()
    try:
        full = inspect_updater(__import__("pathlib").Path(args.full_updater))
        split = inspect_updater(__import__("pathlib").Path(args.split_updater))
        original = check_consistency(
            full["resources.tar.gz"], should_include_fap=True,
            expected_fap_sha256=ARTIFACTS["labmate.fap"],
            expected_js_sha256=ARTIFACTS["js_gpio.module"],
        )
        derivation = check_consistency(
            split["resources.tar.gz"], should_include_fap=False,
            expected_fap_sha256=ARTIFACTS["labmate.fap"],
            expected_js_sha256=ARTIFACTS["js_gpio.module"],
        )
        for blob in (full["resources.tar.gz"], split["resources.tar.gz"]):
            if _archive_member_sha(blob, JS_PATH) != ARTIFACTS["js_gpio.module"]:
                raise ValueError("packed native JS SHA256 not exact")
        if _archive_member_sha(full["resources.tar.gz"], FAP_PATH) != ARTIFACTS["labmate.fap"]:
            raise ValueError("full LabMate FAP not exact pinned SHA256")
    except (OSError, ValueError, UnicodeError, tarfile.TarError) as exc:
        p.exit(1, "E11 PACKED RESOURCE MANIFEST AUDIT REFUSED: " + str(exc) + "\n")
    for group, report in (("full", original),("split", derivation)):
        for k, v in report.items():
            print(group + "_" + k + ": " + str(v))
    print("E11 RESOURCE PAIR AUDIT PASS - SPLIT NOT INSTALLABLE / NO FLASH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
