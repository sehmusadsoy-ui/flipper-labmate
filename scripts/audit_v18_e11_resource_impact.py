#!/usr/bin/env python3
"""Read-only compare of official Momentum-012 and exact v1.8 E11 review updater.

Do NOT flash or publish based on these results. This verifies static updater
contents and flags SD changes; it cannot predict boot, SD migration or restore.
"""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import tarfile

from check_v18_full_vs_mntm012 import check as compare_radio_and_ob
from preflight_v18_e11_local import ARTIFACTS, SOURCE, RUN, assert_sha
from stage_v18_e11_review_only import inspect_updater
from verify_v18_full_review_pair import verify

MAX_RESOURCES = 90_000_000
MAX_MEMBERS = 20000
JS_PATH = "apps_data/js_app/plugins/js_gpio.fal"
FAP_PATH = "apps/Tools/labmate.fap"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized(name: str, is_dir: bool) -> str:
    if "\\" in name or ":" in name or name.startswith("/"):
        raise ValueError("unsafe resource archive path")
    # Common tar root-style relative prefix is permissible, but never '..'
    while name.startswith("./"):
        name = name[2:]
    name = name.rstrip("/") if is_dir else name
    if name in ("", ".") and is_dir:
        return ""
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("unsafe resource archive segment")
    return name


def inventory_resources(archive_bytes: bytes) -> dict[str, str]:
    """Read TAR payload bytes only for digests; never extract onto local/device SD."""
    if len(archive_bytes) > MAX_RESOURCES:
        raise ValueError("oversized compressed SD resource archive")
    result: dict[str, str] = {}
    total = 0
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as archive:
        for i, member in enumerate(archive):
            if i >= MAX_MEMBERS:
                raise ValueError("excessive SD resource member count")
            if not (member.isfile() or member.isdir()):
                raise ValueError("non-file/non-directory SD resource member")
            name = normalized(member.name, member.isdir())
            if not name:
                continue
            if name in seen:
                raise ValueError("duplicate SD resource member")
            seen.add(name)
            if member.isdir():
                continue
            if member.size <= 0 or member.size > MAX_RESOURCES:
                raise ValueError("empty/oversized SD resource file")
            total += member.size
            if total > MAX_RESOURCES:
                raise ValueError("too much SD resource data")
            f = archive.extractfile(member)
            if f is None:
                raise ValueError("unreadable SD resource file")
            digest = hashlib.sha256()
            read = 0
            while part := f.read(1024 * 1024):
                digest.update(part)
                read += len(part)
            if read != member.size:
                raise ValueError("truncated SD resource entry")
            result[name] = digest.hexdigest()
    if not result:
        raise ValueError("empty SD resource files")
    return result


def resources_from_update(updater_tgz: Path, *, max_tgz_bytes: int = MAX_RESOURCES) -> bytes:
    if updater_tgz.is_symlink() or updater_tgz.stat().st_size > max_tgz_bytes:
        raise ValueError("missing, linked or oversized updater archive")
    found: list[bytes] = []
    with tarfile.open(updater_tgz, mode="r:gz") as archive:
        for m in archive:
            if m.name.endswith("/resources.tar.gz") and m.isfile():
                if m.size <= 0 or m.size > MAX_RESOURCES:
                    raise ValueError("invalid embedded resources size")
                f = archive.extractfile(m)
                if f is None:
                    raise ValueError("invalid resources archive entry")
                buf = f.read(m.size + 1)
                if len(buf) != m.size:
                    raise ValueError("truncated embedded resources")
                found.append(buf)
    if len(found) != 1:
        raise ValueError("expected exactly one embedded resources archive")
    return found[0]


def compare_resource_files(
    old: dict[str, str], new: dict[str, str],
    *, expected_js: str, expected_fap: str,
) -> dict[str, object]:
    if not old or not new:
        raise ValueError("missing SD resources inventory")
    added = sorted(new.keys() - old.keys())
    deleted = sorted(old.keys() - new.keys())
    modified = sorted(k for k in old.keys() & new.keys() if old[k] != new[k])
    changed = added + deleted + modified
    if any(k.lower() == "apps_data/labmate" or k.lower().startswith("apps_data/labmate/")
           for k in new):
        raise ValueError("full updater includes LabMate persistent data paths")
    plugin_paths = [key for key in new if key.lower() == JS_PATH.lower()]
    if len(plugin_paths) != 1:
        raise ValueError("expected exactly one native JS GPIO plugin in SD resources")
    if new[plugin_paths[0]] != expected_js:
        raise ValueError("embedded JS GPIO binary differs from checked exact module")
    fap = [key for key in new if key.lower() == FAP_PATH.lower()]
    if fap and new[fap[0]] != expected_fap:
        raise ValueError("embedded LabMate FAP differs from checked exact app")
    # Other app data paths may be legitimate installed resources, but cannot
    # prove that the user's SD files there will be untouched.
    changed_data = [k for k in changed if k.lower().startswith("apps_data/")
                    and k.lower() != JS_PATH.lower()]
    return {
        "old_file_count": len(old),
        "new_file_count": len(new),
        "added_count": len(added),
        "removed_count": len(deleted),
        "modified_count": len(modified),
        "non_js_app_data_changed_count": len(changed_data),
        "non_js_app_data_changed_preview": changed_data[:20],
        "js_gpio_binary_matches": True,
        "labmate_fap_embedded": bool(fap),
        "labmate_fap_in_earlier_update": any(k.lower() == FAP_PATH.lower() for k in old),
        "bundled_fap_blocks_assumed_firmware_then_fap_separation": bool(fap),
        "other_resource_changes_require_manual_compatibility_review": bool(changed_data or deleted or modified),
        "trial_go_no_go": "NO-GO",
        "device_write_authorized": False,
    }


def audit(old_tgz: Path, candidate: Path) -> dict[str, object]:
    if not candidate.is_dir() or candidate.is_symlink():
        raise ValueError("review candidate folder required")
    for name, digest in ARTIFACTS.items():
        assert_sha(candidate / name, digest)
    verify(candidate, SOURCE, RUN)
    fresh = candidate / "firmware-full-update.tgz"
    compare_radio_and_ob(old_tgz, fresh)  # checks independent official old TGZ SHA.
    expected = inspect_updater(fresh)
    old = inventory_resources(resources_from_update(old_tgz))
    new = inventory_resources(expected["resources.tar.gz"])
    result = compare_resource_files(
        old, new,
        expected_js=ARTIFACTS["js_gpio.module"],
        expected_fap=ARTIFACTS["labmate.fap"],
    )
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--official-rollback", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    args = p.parse_args()
    try:
        r = audit(args.official_rollback, args.candidate)
    except (OSError, ValueError, UnicodeError, tarfile.TarError) as e:
        p.exit(1, "E11 SD IMPACT REVIEW REFUSED: " + str(e) + "\n")
    for field, value in r.items():
        print(field + ": " + str(value))
    print("E11 OFFLINE RESOURCE IMPACT AUDIT PASS - NO FLASH / NO RECOVERY PROOF")
    print("RESOURCE INVENTORY != USER MICROSD SNAPSHOT; HUMAN RELEASE REVIEW REQUIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
