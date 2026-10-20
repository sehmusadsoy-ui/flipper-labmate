#!/usr/bin/env python3
"""Prepare verified v1.9 E11 FAP as a NEW PC-only trial candidate (NO USB).

Default = verify-only; --prepare writes only a new local PC directory.
Never connects to Flipper, opens COM, writes to microSD, reflashes firmware,
performs restoration, launches LabMate or approves installation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

FAP = "labmate-v1.9DEV-E11-review.fap"
REQUIRED = frozenset((FAP, "SHA256SUMS.txt", "PROVENANCE.txt", "READ_ME_FIRST.txt"))
SOURCE_SHA = "3d66658dad6e09df9c011a91a78881bcc16eb25b"
MOMENTUM_BASE = "d3f89dfe2ef6b01839201598e9be1590cba80322"
FAP_SHA = "e1f43390c4078fbaad7e13124331926e0d6667294f2815e8b63762bd16f3ff90"
FAP_BYTES = 97540
ZIP_SHA = "2161804ab0939110d79db861106569ea6f20262a20d0578491c40f513b4926f3"
LOCAL_DIFF_SHA = "a0cc3040a9ef41897f3c3d1cd9414e1d7aeb8dfae69244d3d782c88a5cb7ea90"
V18_SHA = "393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61"
E11_OLD_SHA = "2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0"
V18_BACKUP_FILE = "installed_LabMate_v18_FINAL_E11_before_v19.fap"
OLD_BACKUP_FILE = "installed_E11_v18DEV_before_final_label.fap"
HEX = re.compile(r"[0-9a-f]{64}\Z")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(path: Path, *, max_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= max_bytes:
        raise ValueError("missing/unsafe/oversized PC input: " + path.name)
    return path.read_bytes()


def json_object(path: Path) -> dict:
    value = json.loads(regular(path, max_bytes=1_000_000).decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected JSON object: " + path.name)
    return value


def safe_backup_directory(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise ValueError("missing backup directory: " + path.name)
    if any(p.name.startswith("INCOMPLETE") for p in path.iterdir()):
        raise ValueError("backup incomplete: " + path.name)


def verify_zip(archive: Path) -> dict[str, bytes]:
    content = regular(archive, max_bytes=400_000)
    if digest(content) != ZIP_SHA:
        raise ValueError("local v1.9 review ZIP SHA256 mismatch")
    files = {}
    prefix = set()
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            name = info.filename
            parts = PurePosixPath(name).parts
            if (not parts or len(parts) > 2 or
                    any(v in (".", "..", "") for v in parts) or
                    name.startswith("/") or "\\" in name):
                raise ValueError("unsafe review ZIP member")
            kind = stat.S_IFMT(info.external_attr >> 16)
            if kind == stat.S_IFLNK:
                raise ValueError("symlink member in review ZIP")
            if info.is_dir():
                if len(parts) != 1:
                    raise ValueError("unexpected review ZIP directory")
                continue
            if info.file_size > 150_000 or parts[-1] not in REQUIRED:
                raise ValueError("unrecognized/oversized review ZIP file")
            if parts[-1] in files:
                raise ValueError("duplicate review ZIP member")
            prefix.add(parts[0] if len(parts) == 2 else "")
            files[parts[-1]] = zf.read(info)
    if set(files) != REQUIRED or len(prefix) != 1:
        raise ValueError("unexpected review ZIP file inventory")
    return files


def verify_review(archive: Path, directory: Path) -> bytes:
    files = verify_zip(archive)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("missing extracted local v1.9 review directory")
    entries = tuple(directory.iterdir())
    if {p.name for p in entries} != REQUIRED:
        raise ValueError("extracted review files changed")
    for name, saved in files.items():
        if regular(directory / name, max_bytes=150_000) != saved:
            raise ValueError("local FAP review folder differs from ZIP: " + name)
    candidate = files[FAP]
    if len(candidate) != FAP_BYTES or digest(candidate) != FAP_SHA:
        raise ValueError("v1.9 FAP size/SHA256 mismatch")
    sums = files["SHA256SUMS.txt"].decode("ascii").strip().splitlines()
    if len(sums) != 1 or sums[0] != FAP_SHA + "  " + FAP:
        raise ValueError("FAP SHA256SUMS is not the exact reviewed value")
    kv = {}
    for line in files["PROVENANCE.txt"].decode("utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if key in kv:
                raise ValueError("duplicated provenance key: " + key)
            kv[key] = value
    expected = {
        "SOURCE_SHA": SOURCE_SHA, "MOMENTUM_BASE": MOMENTUM_BASE,
        "PATCH_DIFF_SHA256": LOCAL_DIFF_SHA, "BUILD_MODE": "LOCAL_WSL2",
        "GITHUB_ACTIONS_RUN": "NONE",
    }
    for key, value in expected.items():
        if kv.get(key) != value:
            raise ValueError("local review provenance mismatch: " + key)
    return candidate


def verify_backups(active: Path, old: Path, snapshot: Path) -> tuple[int, int]:
    for directory in (active, old, snapshot):
        safe_backup_directory(directory)
    active_bytes = regular(active / V18_BACKUP_FILE, max_bytes=100_000)
    if len(active_bytes) != 81528 or digest(active_bytes) != V18_SHA:
        raise ValueError("real device-backed v1.8 final FAP differs")
    active_report = json_object(active / "LIVE_V18_FAP_READBACK_REPORT.json")
    if ((active_report.get("on_device_fap_sha256") != V18_SHA) or
            (active_report.get("device_state_before_and_after_read") != "AFTER_PROMOTION") or
            (active_report.get("device_writes") is not False) or
            (active_report.get("v19_installed") is not False) or
            not (active / "READ_ONLY_PC_V18_FAP_BACKUP_VERIFIED.txt").is_file()):
        raise ValueError("final v1.8 real-device PC readback report invalid")

    previous = regular(old / OLD_BACKUP_FILE, max_bytes=100_000)
    if len(previous) != 81532 or digest(previous) != E11_OLD_SHA:
        raise ValueError("historical E11 v1.8DEV PC backup changed")
    old_report = json_object(old / "PREWRITE_READONLY_REPORT.json")
    if (old_report.get("installed_old_fap_sha256") != E11_OLD_SHA or
            old_report.get("device_write") is not False or
            not (old / "READ_ONLY_PC_FAP_BACKUP_VERIFIED.txt").is_file()):
        raise ValueError("historical E11 backup report invalid")

    report = json_object(snapshot / "PC_SNAPSHOT_MANIFEST.json")
    if (report.get("snapshot_scope") != "ONLY /ext/apps_data/labmate" or
            report.get("snapshot_complete") is not True or
            report.get("device_write") is not False or
            report.get("full_microSD_backup") is not False or
            not (snapshot / "READ_ONLY_SNAPSHOT_VERIFIED.txt").is_file()):
        raise ValueError("current LabMate CSV/Profile snapshot report invalid")
    entries = report.get("files")
    if not isinstance(entries, dict) or not 1 <= len(entries) <= 512:
        raise ValueError("current LabMate snapshot inventory absent/oversized")
    total = 0
    observed = set()
    for name, item in entries.items():
        if (not isinstance(name, str) or not isinstance(item, dict) or
                any(part in ("", ".", "..") for part in name.split("/")) or
                "\\" in name or name.startswith("/")):
            raise ValueError("unsafe snapshot path")
        p = snapshot.joinpath(*name.split("/"))
        if p.resolve(strict=True).parent != snapshot.resolve() and snapshot.resolve() not in p.resolve().parents:
            raise ValueError("snapshot path escapes backup directory")
        size = item.get("size_bytes")
        expected_md5 = item.get("md5_device_screen")
        expected_sha = item.get("sha256_of_pc_readback")
        if (not isinstance(size, int) or isinstance(size, bool) or size < 0 or size > 10_000_000 or
                not isinstance(expected_md5, str) or not re.fullmatch(r"[0-9a-f]{32}", expected_md5) or
                not isinstance(expected_sha, str) or not HEX.fullmatch(expected_sha)):
            raise ValueError("invalid snapshot file fingerprint")
        if p.is_symlink() or not p.is_file() or p.stat().st_size != size:
            raise ValueError("missing/changed snapshot file")
        content = p.read_bytes()
        if hashlib.md5(content).hexdigest() != expected_md5 or digest(content) != expected_sha:
            raise ValueError("LabMate snapshot file MD5/SHA256 mismatch")
        total += size
        observed.add(name)
    disk_files = {
        p.relative_to(snapshot).as_posix()
        for p in snapshot.rglob("*") if p.is_file() and not p.is_symlink()
    }
    if any(p.is_symlink() for p in snapshot.rglob("*")):
        raise ValueError("unsafe symlink in LabMate snapshot")
    if disk_files != observed | {"PC_SNAPSHOT_MANIFEST.json", "READ_ONLY_SNAPSHOT_VERIFIED.txt"}:
        raise ValueError("LabMate snapshot inventory mismatch")
    if total != 2128:
        raise ValueError("current LabMate 2026-10-19 snapshot size not 2128 bytes")
    return len(entries), total


def check_destination(target: Path, sources: tuple[Path, ...]) -> None:
    if not target.is_absolute() or target.exists() or target.is_symlink():
        raise ValueError("PC staging target must be a NEW absolute folder")
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise ValueError("PC staging parent folder missing/symlink")
    dest = target.resolve(strict=False)
    for source in sources:
        origin = source.resolve(strict=True)
        if origin == dest or origin in dest.parents or dest in origin.parents:
            raise ValueError("PC staging target overlaps protected original or backup")


def stage_pc_only(target: Path, candidate: bytes, count: int, total: int) -> None:
    if len(candidate) != FAP_BYTES or digest(candidate) != FAP_SHA:
        raise ValueError("PC staging requested for unverified FAP")
    target.mkdir(mode=0o700)
    incomplete = target / "INCOMPLETE_DO_NOT_INSTALL_OR_RESTORE.txt"
    incomplete.write_text("PC-only preparation interrupted. No device installation authorized.\n")
    output = target / "labmate-v1.9DEV-E11-PC-ONLY.fap"
    with output.open("xb") as f:
        f.write(candidate)
        f.flush()
        os.fsync(f.fileno())
    if output.stat().st_size != FAP_BYTES or digest(output.read_bytes()) != FAP_SHA:
        raise ValueError("PC staged FAP disk readback mismatch")
    report = {
        "status": "PC_ONLY_PREPARED_NOT_INSTALLED",
        "source_commit": SOURCE_SHA, "momentum_base": MOMENTUM_BASE,
        "candidate_sha256": FAP_SHA, "candidate_bytes": FAP_BYTES,
        "prior_installed_v18_sha256": V18_SHA,
        "older_e11_v18dev_sha256": E11_OLD_SHA,
        "labmate_snapshot_files_verified": count, "labmate_snapshot_bytes": total,
        "historical_e11_patch_parity": "OPERATOR_REPORTED_PASS_WITH_CORE_ABBREV_7",
        "full_firmware_hash_readback": "NOT_PERFORMED",
        "device_write": False, "firmware_flash": False,
        "installation_authorized": False, "rollback_rehearsed": False,
    }
    with (target / "PC_PREPARATION_PROVENANCE.json").open("x", encoding="utf-8") as out:
        json.dump(report, out, sort_keys=True, indent=2)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())
    (target / "SHA256SUMS.txt").write_text(FAP_SHA + "  " + output.name + "\n")
    (target / "READ_ME_NO_DEVICE_WRITE.txt").write_text(
        "REVIEW ONLY. PC STAGING IS NOT DEVICE INSTALLATION APPROVAL.\n"
        "Preserve live v1.8 FAP backup, old E11 backup and LabMate data snapshot.\n"
        "Do not flash firmware, replace labmate.fap, overwrite old backup or retry a\n"
        "partially written SD sidecar. Actual device staging and manual rollback\n"
        "require a separate reviewed procedure and explicit new operator consent.\n"
    )
    (target / "PC_ONLY_PREPARATION_VERIFIED.txt").write_text(
        "Local reviewed v1.9 FAP bytes, both E11/v1.8 FAP backups and live\n"
        "LabMate data snapshot passed PC-only integrity screening. NO DEVICE WRITES.\n"
    )
    incomplete.unlink()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--review-zip", required=True, type=Path)
    p.add_argument("--review-directory", required=True, type=Path)
    p.add_argument("--active-v18-backup", required=True, type=Path)
    p.add_argument("--historical-e11-backup", required=True, type=Path)
    p.add_argument("--data-snapshot", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--prepare", action="store_true", help="create ONLY a fresh PC local review folder")
    args = p.parse_args()
    print("V19 E11 PC-ONLY REVIEW PREPARATION; NO USB/SD/FLASH")
    try:
        sources = (args.review_zip, args.review_directory, args.active_v18_backup,
                   args.historical_e11_backup, args.data_snapshot)
        check_destination(args.output, sources)
        candidate = verify_review(args.review_zip, args.review_directory)
        count, total = verify_backups(
            args.active_v18_backup, args.historical_e11_backup, args.data_snapshot
        )
        if args.prepare:
            stage_pc_only(args.output, candidate, count, total)
    except Exception as exc:
        why = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("V19 E11 PC PREPARATION NO-GO: " + why, file=sys.stderr)
        print("STOP: no device writes authorized; do not install or retry blindly.", file=sys.stderr)
        return 1
    print("V19 FAP SHA256:", FAP_SHA)
    print("LIVE V18 + HISTORICAL E11 PC BACKUPS: PASS")
    print("LABMATE DATA SNAPSHOT: PASS | files:", count, "| bytes:", total)
    print("PC_ONLY_PREPARATION:", "PASS" if args.prepare else "VERIFICATION_PASS_NO_COPY")
    if args.prepare:
        print("PC_OUTPUT:", args.output)
    print("DEVICE_WRITES: NONE | FIRMWARE_FLASH: NONE | V19 INSTALL: NOT AUTHORIZED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
