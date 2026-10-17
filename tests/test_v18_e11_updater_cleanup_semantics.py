#!/usr/bin/env python3
"""Synthetic updater ordering and fail-closed safety checks, NO DEVICE."""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_v18_e11_updater_cleanup_semantics import audit

OLD = r'''
static void update_task_cleanup_resources(UpdateTask* task) {
    if(!resource_manifest_reader_open(manifest_reader, EXT_PATH("Manifest"))) {
        break;
    }
    if(entry_ptr->type == ResourceManifestEntryTypeFile) {
        storage_common_remove(task->storage, furi_string_get_cstr(file_path));
    }
    if(entry_ptr->type == ResourceManifestEntryTypeDirectory) {
        storage_common_remove(task->storage, furi_string_get_cstr(folder_path));
    }
}
static bool update_task_pre_update(UpdateTask* task) {
    int_backup_create(task->storage, backup_file);
    return true;
}
static bool update_task_post_update(UpdateTask* task) {
    int_backup_unpack(task->storage, old_backup);
    if(task->state.groups & UpdateTaskStageGroupResources) {
        update_task_cleanup_resources(task);
        tar_archive_unpack_to(archive, STORAGE_EXT_PATH_PREFIX, NULL);
    }
    return true;
}
'''
FLASH = r'''
int32_t update_task_worker_flash_writer(void* context) {
    update_task_manage_radiostack(update_task);
    update_task_validate_optionbytes(update_task);
    update_task_write_dfu(update_task);
    furi_hal_rtc_set_flag(FuriHalRtcFlagStorageFormatInternal);
    return 0;
}
'''
# The pinned real source has update_task variable, not task.
OLD = OLD.replace("task->", "update_task->").replace(
    "resources(task);", "resources(update_task);"
)


class OldManifestCleanupSemantics(unittest.TestCase):
    def test_expected_order_and_side_effects(self):
        result = audit(OLD, FLASH)
        self.assertEqual(result["old_resource_cleanup_before_new_unpack"], "YES")
        self.assertEqual(result["cleanup_source_reads"], "/ext/Manifest (CURRENT/OLD)")
        self.assertEqual(result["split_bundle_prevents_old_installed_fap_removal"], "NOT_PROVEN")
        self.assertEqual(result["native_flash_or_restore_authorized"], "NO")

    def test_old_manifest_read_missing_must_refuse(self):
        with self.assertRaisesRegex(ValueError, "old-resource cleanup"):
            audit(OLD.replace('EXT_PATH("Manifest")', 'EXT_PATH("Other")'), FLASH)

    def test_remove_file_missing_must_refuse(self):
        with self.assertRaisesRegex(ValueError, "cleanup"):
            audit(OLD.replace(
                "storage_common_remove(update_task->storage, furi_string_get_cstr(file_path))",
                "no_resource_remove(file_path)"), FLASH)

    def test_resource_cleanup_after_unpack_refused(self):
        s = OLD.replace(
            "update_task_cleanup_resources(update_task);\n        tar_archive_unpack_to",
            "tar_archive_unpack_to(archive, STORAGE_EXT_PATH_PREFIX, NULL);\n"
            "        update_task_cleanup_resources(update_task);\n        tar_archive_unpack_to"
        )
        with self.assertRaisesRegex(ValueError, "order"):
            audit(s, FLASH)

    def test_internal_restore_missing_refused(self):
        with self.assertRaisesRegex(ValueError, "restoration"):
            audit(OLD.replace("int_backup_unpack(", "not_an_unwrap("), FLASH)

    def test_internal_backup_creation_missing_refused(self):
        with self.assertRaisesRegex(ValueError, "backup creation"):
            audit(OLD.replace("int_backup_create(", "ignored_backup("), FLASH)

    def test_no_optionbyte_path_refused(self):
        with self.assertRaisesRegex(ValueError, "optionbytes"):
            audit(OLD, FLASH.replace("update_task_validate_optionbytes", "skip_optionbytes"))

    def test_no_internal_format_flag_refused(self):
        with self.assertRaisesRegex(ValueError, "StorageFormatInternal"):
            audit(OLD, FLASH.replace("FuriHalRtcFlagStorageFormatInternal", "FlagUnused"))

    def test_incomplete_source_cannot_satisfy_static_audit(self):
        with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
            audit("", FLASH)

    def test_duplicated_function_refused(self):
        repeated = OLD + OLD[:OLD.index("static bool update_task_pre_update")]
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            audit(repeated, FLASH)


if __name__ == "__main__":
    unittest.main()
