#!/usr/bin/env python3
"""Only synthetic Momentum resource TAR files: no device, install or writes."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from derive_v18_e11_split_review import tarball
from audit_v18_e11_resource_impact import FAP_PATH, JS_PATH
from audit_v18_e11_packed_manifest_integrity import check_consistency, scan_packed_resources


class SyntheticPackedManifest(unittest.TestCase):
    def setUp(self):
        self.paths = {
            FAP_PATH: b"new-paired-E11-fap-not-an-actual-app",
            JS_PATH: b"new-E11-JS-fal-bytes",
            "assets/example.dat": b"some bytes",
        }
        self.dirs = ["apps", "apps/Tools", "apps_data", "apps_data/js_app",
                     "apps_data/js_app/plugins", "assets"]
        self.declared = {
            k: (hashlib.md5(v).hexdigest(), len(v))
            for k,v in self.paths.items()
        }

    def resource(self, *, omit_fap=False, declared=None, extra=None, version=b"V:0"):
        declarations = self.declared if declared is None else declared
        lines = [version,b"T:1760000000"]
        lines += [b"D:"+p.encode() for p in self.dirs]
        lines += [
            b"F:"+h.encode()+b":"+str(size).encode()+b":"+p.encode()
            for p,(h,size) in declarations.items()
        ]
        if extra:
            lines.extend(extra)
        file_items = {k:v for k,v in self.paths.items()
                      if not (omit_fap and k==FAP_PATH)}
        return tarball(
            [(p,None) for p in self.dirs] +
            [(k,v) for k,v in file_items.items()] +
            [("Manifest",b"\n".join(lines)+b"\n")]
        )

    def test_full_updater_requires_matching_new_fap_and_manifest(self):
        d=check_consistency(self.resource(),should_include_fap=True)
        self.assertEqual(d["packed_actual_resource_files"],3)
        self.assertEqual(d["packed_manifest_declared_files"],3)
        self.assertEqual(d["packed_manifest_orphan_references"],0)
        self.assertEqual(d["labmate_pairing_in_resources"],"FULL_BUNDLE_DECLARED_AND_PRESENT")
        self.assertEqual(d["physical_install_approved"],"NO")

    def test_one_pinned_generated_firstboot_outside_manifest_is_reported(self):
        # Exact Momentum scripts/update.py outputs this generated Slideshow
        # after the resources Manifest was built; no generic allowance.
        self.paths["dolphin/firstboot.bin"] = b"fake generated firstboot"
        self.dirs.append("dolphin")
        report=check_consistency(self.resource(),should_include_fap=True)
        self.assertEqual(report["packed_manifest_unlisted_files"],1)
        self.assertEqual(report["packed_generated_firstboot_not_in_manifest"],"YES")
        self.assertEqual(report["packed_manifest_other_unlisted_files"],0)

    def test_any_other_extra_unlisted_file_still_fails(self):
        self.paths["dolphin/other-unlisted.bin"] = b"private bytes"
        self.dirs.append("dolphin")
        with self.assertRaisesRegex(ValueError,"mismatching resource contents"):
            check_consistency(self.resource(),should_include_fap=True)

    def test_split_tgz_keeps_stale_fap_reference(self):
        d=check_consistency(self.resource(omit_fap=True),should_include_fap=False)
        self.assertEqual(d["packed_actual_resource_files"],2)
        self.assertEqual(d["packed_manifest_declared_files"],3)
        self.assertEqual(d["packed_manifest_orphan_references"],1)
        self.assertEqual(d["packed_actual_labmate_fap_present"],"NO")
        self.assertEqual(d["packed_manifest_declares_labmate_fap"],"YES")
        self.assertEqual(d["labmate_pairing_in_resources"],"SPLIT_MANIFEST_STILL_DECLARES_REMOVED_FAP")
        self.assertEqual(d["old_device_fap_preserved_by_resource_update"],"NO")

    def test_split_only_accepts_exact_known_single_orphan_fap(self):
        changed=dict(self.declared)
        changed["assets/unlisted.dat"]=("a"*32,1)
        with self.assertRaisesRegex(ValueError,"unexpected packed Manifest mismatch"):
            check_consistency(self.resource(omit_fap=True,declared=changed),
                              should_include_fap=False)

    def test_split_is_not_misclassified_as_complete_full_pair(self):
        with self.assertRaisesRegex(ValueError,"absent files"):
            check_consistency(self.resource(omit_fap=True),should_include_fap=True)

    def test_split_with_fap_restored_is_not_still_a_split(self):
        with self.assertRaisesRegex(ValueError,"unexpectedly still contains"):
            check_consistency(self.resource(),should_include_fap=False)

    def test_corrupted_manifest_md5_detected_even_if_fap_sha_matches(self):
        changed=dict(self.declared)
        changed[JS_PATH]=("a"*32, len(self.paths[JS_PATH]))
        with self.assertRaisesRegex(ValueError,"mismatching resource contents"):
            check_consistency(self.resource(declared=changed),should_include_fap=True)

    def test_manifest_wrong_size_is_refused(self):
        changed=dict(self.declared)
        old_hash,old_size=changed[FAP_PATH]
        changed[FAP_PATH]=(old_hash,old_size+1)
        with self.assertRaisesRegex(ValueError,"mismatching resource contents"):
            check_consistency(self.resource(declared=changed),should_include_fap=True)

    def test_unlisted_archive_resource_refused(self):
        changed={k:v for k,v in self.declared.items() if k!="assets/example.dat"}
        with self.assertRaisesRegex(ValueError,"missing or mismatching resource"):
            check_consistency(self.resource(declared=changed),should_include_fap=True)

    def test_duplicate_manifest_path_rejected(self):
        v=self.declared[FAP_PATH]
        extra=[b"F:"+v[0].encode()+b":"+str(v[1]).encode()+b":"+FAP_PATH.encode()]
        with self.assertRaisesRegex(ValueError,"duplicate"):
            scan_packed_resources(self.resource(extra=extra))

    def test_manifest_traversal_refused(self):
        with self.assertRaisesRegex(ValueError,"unsafe"):
            scan_packed_resources(self.resource(extra=[b"F:"+b"a"*32+b":1:../bad"]))

    def test_manifest_version_refused(self):
        with self.assertRaisesRegex(ValueError,"unrecognized"):
            scan_packed_resources(self.resource(version=b"V:42"))

    def test_missing_manifest_refused(self):
        body=tarball([(k,v) for k,v in self.paths.items()])
        with self.assertRaisesRegex(ValueError,"lack data/Manifest"):
            scan_packed_resources(body)

    def test_exact_sha256_argument_validation(self):
        with self.assertRaisesRegex(ValueError,"fingerprint"):
            check_consistency(self.resource(),should_include_fap=True,
                              expected_fap_sha256="BAD")
        with self.assertRaisesRegex(ValueError,"fingerprint"):
            check_consistency(self.resource(),should_include_fap=True,
                              expected_js_sha256="BAD")

if __name__=="__main__":
    unittest.main()
