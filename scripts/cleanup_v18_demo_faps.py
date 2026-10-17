#!/usr/bin/env python3
"""Remove ONLY reviewed LabMate stand-alone demo/probe FAPs from Tools.

Default is read-only listing. --apply first backs up exact device FAP
bytes to a NEW PC directory, checks live device MD5, then requires typed
confirmation and removes only these explicitly printed FAP files.
Never removes main LabMate FAP, KeyCopier, any data or a directory.
The full E11 firmware resource updater is not invoked.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from backup_v18_e11_usb_sd_to_pc import _cmd, _line, _md5, _read_to_pc
from survey_v18_e11_external_sd_ro import parse_scope_listing

SOURCE = "d3f89dfe"
BASE = "/ext/apps/Tools"
MAIN = "labmate.fap"
EXPECTED_E11_SHA256 = "2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0"
FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,110}\.fap\Z", re.I)
MAX_DEMOS = 3
MAX_FAP_BYTES = 4 * 1024 * 1024


def classify(name: str) -> bool:
    """Only obvious standalone LabMate demo/probe names are candidates."""
    lower = name.lower()
    return bool(
        FILENAME.fullmatch(name) and lower.startswith("labmate")
        and lower != MAIN
        and any(label in lower for label in ("demo", "probe", "busydiag"))
        and "/" not in name and "\\" not in name
    )


def shortlist(files: dict[str, int]) -> dict[str, int]:
    result = {name: size for name, size in files.items() if classify(name)}
    if len(result) > MAX_DEMOS:
        raise ValueError("more than three candidate LabMate demos: manual review required")
    if any(not 0 < size <= MAX_FAP_BYTES for size in result.values()):
        raise ValueError("demo size unexpectedly empty or large")
    return dict(sorted(result.items(), key=lambda item: item[0].casefold()))


def list_tools(storage) -> dict[str, int]:
    storage.send_and_wait_eol('storage list "' + BASE + '"\r')
    payload = storage.read.until(storage.CLI_PROMPT)
    entries = parse_scope_listing(payload)
    files: dict[str, int] = {}
    for typ, raw, size in entries:
        if typ != "file":
            continue
        try:
            name = raw.decode("ascii", "strict")
        except UnicodeError:
            continue
        if name.lower().endswith(".fap"):
            if name.casefold() in {x.casefold() for x in files}:
                raise ValueError("case-colliding installed FAP")
            files[name] = size
    return files


def device_guard(storage, candidate: Path) -> str:
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError("expected verified E11 main LabMate PC FAP is missing")
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != EXPECTED_E11_SHA256:
        raise ValueError("E11 main LabMate independent SHA256 mismatch")
    storage.send_and_wait_eol("device_info\r")
    status = storage.read.until(storage.CLI_PROMPT).decode("utf-8", "strict").lower()
    if SOURCE not in status or "mntm-dev" not in status:
        raise ValueError("unexpected firmware identity; do not delete demo FAPs")
    expected_md5 = hashlib.md5(candidate.read_bytes()).hexdigest()
    live = storage.hash_flipper(BASE + "/" + MAIN).strip().lower()
    if live != expected_md5:
        raise ValueError("installed production E11 LabMate differs from checked PC FAP")
    return expected_md5


def apply(storage, selected: dict[str, int], before: dict[str, int], backup: Path,
          main_md5: str, confirm=input) -> list[str]:
    if not selected:
        print("NO SAFE DEMO CANDIDATES. NOTHING DELETED.")
        return []
    if backup.exists() or backup.is_symlink() or not backup.parent.is_dir():
        raise ValueError("backup output must be a new PC directory in an existing parent")
    backup.mkdir(mode=0o700)
    preserved: dict[str, dict[str, str | int]] = {}
    # All backups must be validated before ANY device deletion.
    for filename, expected_size in selected.items():
        path = (BASE + "/" + filename).encode("ascii")
        md5_before = _md5(storage, path)
        target = backup / filename
        read_md5, read_sha = _read_to_pc(
            storage, tuple([b"apps", b"Tools", filename.encode("ascii")]),
            expected_size, target,
        )
        md5_after = _md5(storage, path)
        if read_md5 != md5_before or md5_after != md5_before:
            raise ValueError("source demo changed during readback: " + filename)
        preserved[filename] = {
            "size_bytes": expected_size, "md5_device_screen": read_md5,
            "sha256_pc_backup": read_sha,
        }
        print("DEMO BACKUP SHA256 VERIFIED: " + filename)
    if list_tools(storage) != before:
        raise ValueError("installed Tools FAP inventory changed before deletion")
    manifest = backup / "DEMO_BACKUP_MANIFEST.json"
    manifest.write_text(json.dumps(preserved, sort_keys=True, indent=2) + "\n",
                        encoding="utf-8")
    phrase = "SIL-DEMO-" + str(len(selected))
    print("This removes ONLY these device FAPs (not any apps_data files):")
    for name in selected:
        print("  " + BASE + "/" + name)
    entered = confirm("TYPE " + phrase + " to delete the above test FAPs: ")
    if entered != phrase:
        print("DECLINED: demo backups remain on PC, NO DEVICE FILE DELETED.")
        return []
    removed = []
    for name in selected:
        # _md5 is the raw Flipper CLI helper: its path MUST be bytes.
        # The earlier str path caused TypeError immediately after typed
        # consent, before storage.remove(). Keep storage.remove() str.
        path = BASE + "/" + name
        if _md5(storage, path.encode("ascii")) != preserved[name]["md5_device_screen"]:
            raise ValueError("demo changed immediately before removal: " + name)
        if storage.hash_flipper(BASE + "/" + MAIN).strip().lower() != main_md5:
            raise ValueError("main E11 LabMate changed: refusing deletion")
        storage.remove(path)
        removed.append(name)
        print("DEMO FAP REMOVED: " + name)
    after = list_tools(storage)
    expected = {name: size for name, size in before.items() if name not in selected}
    if after != expected:
        raise ValueError("post-delete FAP inventory unexpected: inspect manually; no auto-retry")
    if storage.hash_flipper(BASE + "/" + MAIN).strip().lower() != main_md5:
        raise ValueError("main E11 LabMate digest changed: inspect manually")
    print("DEMO CLEANUP PASS: " + str(len(removed)) + " exact FAP files deleted.")
    print("MAIN E11 LABMATE PRESERVED; NO APP DATA OR SYSTEM FIRMWARE WRITTEN.")
    return removed


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--momentum-scripts", type=Path, required=True)
    p.add_argument("--labmate-fap", type=Path, required=True)
    p.add_argument("--backup-dir", type=Path)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    try:
        if not re.fullmatch(r"COM[1-9][0-9]{0,2}", args.port):
            raise ValueError("valid, explicit COMn port required")
        if args.apply and args.backup_dir is None:
            raise ValueError("a fresh PC backup destination required for deletion")
        transport = args.momentum_scripts / "flipper" / "storage.py"
        if (args.momentum_scripts.is_symlink() or transport.is_symlink() or
                not transport.is_file()):
            raise ValueError("pinned Momentum transport unavailable")
        sys.path.insert(0, str(args.momentum_scripts.resolve()))
        import flipper.storage as mntm
        verify_transport_origin(mntm.__file__, args.momentum_scripts)
        remote = mntm.FlipperStorage(args.port)
        remote.read = DeadlineRead(remote.port, timeout_seconds=25.0)
        with remote as storage:
            main_md5 = device_guard(storage, args.labmate_fap)
            all_files = list_tools(storage)
            candidates = shortlist(all_files)
            print("TOOLS FAP INVENTORY (name and size; not UI titles):")
            for name, size in sorted(all_files.items(), key=lambda x: x[0].casefold()):
                print("  " + name + "  " + str(size) + " bytes")
            print("SAFELY RECOGNIZED DEMO/PROBE FAP CANDIDATES: " + str(len(candidates)))
            for name in candidates:
                print("  " + BASE + "/" + name)
            if not args.apply:
                print("READ-ONLY DEMO INVENTORY COMPLETE - NO DEVICE WRITE.")
                return 0
            apply(storage, candidates, all_files, args.backup_dir, main_md5)
    except Exception as error:
        reason = str(error) if type(error) is ValueError else type(error).__name__
        print("DEMO CLEANUP STOPPED: " + reason, file=sys.stderr)
        print("If deletion began, do not retry blindly; inspect output and device.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
