#!/usr/bin/env python3
"""Static verification of EXACT pinned Momentum updater cleanup semantics.

This is a source-code consistency check only, NOT proof of the current
on-device old /ext/Manifest contents, preservation or firmware boot.
The updater's old manifest file entries are removed before new resources
are unpacked. The FAP-excluded NEW resource bundle cannot, by itself,
guarantee the currently installed LabMate app survives old cleanup.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

BASE = "d3f89dfe2ef6b01839201598e9be1590cba80322"


def _function(src: str, signature: str) -> str:
    idx = src.find(signature)
    if idx < 0 or src.find(signature, idx + 1) >= 0:
        raise ValueError("missing or ambiguous required updater function")
    start = src.find("{", idx)
    if start < 0:
        raise ValueError("updater function opening brace missing")
    depth = 0
    for index in range(start, len(src)):
        if src[index] == "{":
            depth += 1
        elif src[index] == "}":
            depth -= 1
            if depth == 0:
                return src[start:index + 1]
    raise ValueError("unbalanced updater function body")


def audit(backup_worker: str, flasher_worker: str) -> dict[str, str]:
    cleanup = re.sub(r"\s+", " ", _function(backup_worker, "static void update_task_cleanup_resources("))
    post = re.sub(r"\s+", " ", _function(backup_worker, "static bool update_task_post_update("))
    flash = re.sub(r"\s+", " ", _function(flasher_worker, "int32_t update_task_worker_flash_writer("))
    before = re.sub(r"\s+", " ", _function(backup_worker, "static bool update_task_pre_update("))

    for text in (
        'resource_manifest_reader_open(manifest_reader, EXT_PATH("Manifest"))',
        "ResourceManifestEntryTypeFile",
        "storage_common_remove(update_task->storage, furi_string_get_cstr(file_path))",
        "ResourceManifestEntryTypeDirectory",
        "storage_common_remove(",
    ):
        if text not in cleanup:
            raise ValueError("old-resource cleanup semantics changed: missing " + text)
    for text in (
        "int_backup_unpack(",
        "UpdateTaskStageGroupResources",
        "update_task_cleanup_resources(update_task);",
        "tar_archive_unpack_to(archive, STORAGE_EXT_PATH_PREFIX, NULL)",
    ):
        if text not in post:
            raise ValueError("resource restoration/unpack semantics changed: missing " + text)
    if not (post.index("int_backup_unpack(")
            < post.index("update_task_cleanup_resources(update_task);")
            < post.index("tar_archive_unpack_to(archive, STORAGE_EXT_PATH_PREFIX, NULL)")):
        raise ValueError("old-resource removal order changed")
    if "int_backup_create(" not in before:
        raise ValueError("internal backup creation not found in pre-update")
    for text in (
        "update_task_manage_radiostack(update_task)",
        "update_task_validate_optionbytes(update_task)",
        "update_task_write_dfu(update_task)",
        "FuriHalRtcFlagStorageFormatInternal",
    ):
        if text not in flash:
            raise ValueError("native update operation missing or changed: " + text)
    # Confirm that the *old* manifest is consulted, not the *new* archive.
    if "resource_manifest_reader_open(" not in cleanup or "tar_archive_unpack_to(" in cleanup:
        raise ValueError("resource cleanup source scope changed unexpectedly")

    return {
        "pinned_momentum_source": BASE,
        "cleanup_source_reads": "/ext/Manifest (CURRENT/OLD)",
        "cleanup_files_listed_in_old_manifest": "YES",
        "cleanup_old_directories_in_reverse": "YES",
        "backup_int_state_before_native_update": "SOURCE_CONFIRMED",
        "internal_restore_precedes_sd_resource_cleanup": "YES",
        "old_resource_cleanup_before_new_unpack": "YES",
        "radio_optionbyte_firmware_programming_paths_exist": "YES",
        "internal_storage_format_flag_in_native_update": "YES",
        "split_bundle_prevents_old_installed_fap_removal": "NOT_PROVEN",
        "actual_device_manifest_seen": "NO",
        "native_flash_or_restore_authorized": "NO",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-worker", type=Path, required=True)
    parser.add_argument("--flasher-worker", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(
            args.backup_worker.read_text(encoding="utf-8"),
            args.flasher_worker.read_text(encoding="utf-8"),
        )
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(1, "E11 UPDATER SOURCE AUDIT REFUSED: " + str(exc) + "\n")
    for key, value in report.items():
        print(f"{key}: {value}")
    print("E11 UPDATER CLEANUP SOURCE AUDIT PASS - NO FLASH / NO RECOVERY PROOF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
