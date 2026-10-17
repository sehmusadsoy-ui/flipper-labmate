#!/usr/bin/env python3
"""Host-only negative tests for strict historic vs final E11 bundle comparison."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("delta",ROOT/"scripts/audit_v18_e11_final_binary_delta_ro.py")
assert spec and spec.loader
delta=importlib.util.module_from_spec(spec)
spec.loader.exec_module(delta)


class BinaryPairAuditTests(unittest.TestCase):
    def setUp(self):
        self.work=tempfile.TemporaryDirectory(prefix="e11_candidate_compare_")
        self.trial=Path(self.work.name)/"trial"
        self.final=Path(self.work.name)/"final"
        self.trial.mkdir()
        self.final.mkdir()
        self.one=self.make(self.trial,"a","1",{
            "labmate.fap":b"old-fap",
            "firmware.dfu":b"old-dfu",
            "js_gpio.module":b"identical-native-js",
            "firmware-full-update.tgz":b"old-review-archive",
        })
        self.two=self.make(self.final,"b","2",{
            "labmate.fap":b"new-fap",
            "firmware.dfu":b"new-dfu",
            "js_gpio.module":b"identical-native-js",
            "firmware-full-update.tgz":b"new-review-archive",
        })

    def tearDown(self):
        self.work.cleanup()

    @staticmethod
    def make(root, source, run, data):
        for name,content in data.items():
            (root/name).write_bytes(content)
        expected={name:delta.digest(root/name) for name in delta.FILES}
        expected.update(source=source,run=run)
        (root/"SHA256SUMS.txt").write_text(
            "".join(f"{expected[n]}  {n}\n" for n in delta.FILES))
        (root/"PROVENANCE.txt").write_text(
            f"LabMate commit: {source}\nActions run: {run}\n"
            f"Momentum base: {delta.MOMENTUM}\n"
            f"E11 firmware diff SHA256: {delta.PATCH_SHA}\n")
        (root/"READ_ME_FIRST.txt").write_text(
            "NOT A RELEASE. DO NOT FLASH. Never mix this matched FAP with unpatched Momentum firmware.\n")
        return expected

    def test_reports_true_identical_module_and_distinct_other_binaries(self):
        result=delta.audit(self.trial,self.final,self.one,self.two)
        self.assertEqual(result["js_gpio.module"][0],0)
        self.assertGreater(result["firmware.dfu"][0],0)
        self.assertGreater(result["labmate.fap"][0],0)

    def test_rejects_identity_tamper(self):
        (self.final/"firmware.dfu").write_bytes(b"unreviewed-firmware")
        with self.assertRaisesRegex(ValueError,"SHA mismatch"):
            delta.audit(self.trial,self.final,self.one,self.two)

    def test_rejects_mismatched_provenance_even_if_self_hash_valid(self):
        p=self.final/"PROVENANCE.txt"
        p.write_text(p.read_text().replace("Actions run: 2","Actions run: 99"))
        with self.assertRaisesRegex(ValueError,"provenance mismatch"):
            delta.audit(self.trial,self.final,self.one,self.two)

    def test_rejects_bad_manifest(self):
        p=self.trial/"SHA256SUMS.txt"
        p.write_text(p.read_text().replace(self.one["labmate.fap"],"0"*64))
        with self.assertRaisesRegex(ValueError,"SHA mismatch"):
            delta.audit(self.trial,self.final,self.one,self.two)

    def test_rejects_extra_file_or_symlink(self):
        (self.trial/"readme2.txt").write_text("x")
        with self.assertRaisesRegex(ValueError,"inventory"):
            delta.audit(self.trial,self.final,self.one,self.two)
        (self.trial/"readme2.txt").unlink()
        (self.trial/"labmate.fap").unlink()
        (self.trial/"labmate.fap").symlink_to(self.final/"labmate.fap")
        with self.assertRaisesRegex(ValueError,"symbolic link"):
            delta.audit(self.trial,self.final,self.one,self.two)

    def test_rejects_native_plugin_binary_change_even_with_matching_new_hash(self):
        (self.final/"js_gpio.module").write_bytes(b"other-compiled-module")
        self.two=self.make(self.final,"b","2",{
            "labmate.fap":b"new-fap",
            "firmware.dfu":b"new-dfu",
            "js_gpio.module":b"other-compiled-module",
            "firmware-full-update.tgz":b"new-review-archive",
        })
        with self.assertRaisesRegex(ValueError,"native JS module drift"):
            delta.audit(self.trial,self.final,self.one,self.two)

    def test_rejects_same_directory(self):
        with self.assertRaisesRegex(ValueError,"independent"):
            delta.audit(self.trial,self.trial,self.one,self.one)

    def test_reports_difference_count_with_trailing_bytes(self):
        (self.trial/"test.bin").write_bytes(b"abcd")
        (self.final/"test.bin").write_bytes(b"abzdxy")
        self.assertEqual(delta.difference_count(self.trial/"test.bin",self.final/"test.bin"),(3,4,6))


    def test_bounded_offsets_identifies_dfu_payload_delta(self):
        (self.trial/"offset.dfu").write_bytes(b"abcdef")
        (self.final/"offset.dfu").write_bytes(b"abcXef")
        self.assertEqual(
            delta.bounded_changed_offsets(self.trial/"offset.dfu",self.final/"offset.dfu"),[3])

    def test_bounded_offsets_rejects_mutated_length_or_large_change(self):
        (self.trial/"offset.dfu").write_bytes(b"abcdef")
        (self.final/"offset.dfu").write_bytes(b"abcd")
        with self.assertRaisesRegex(ValueError,"lengths differ"):
            delta.bounded_changed_offsets(self.trial/"offset.dfu",self.final/"offset.dfu")
        (self.final/"offset.dfu").write_bytes(b"ZZZZZZ")
        with self.assertRaisesRegex(ValueError,"too many"):
            delta.bounded_changed_offsets(self.trial/"offset.dfu",self.final/"offset.dfu",limit=2)


    @staticmethod
    def dfu_fixture(date: bytes, extra: bytes=b"safe"):
        import zlib
        data=b"DfuSe" + (b"\\x00"*40) + b"HEAD\\x00" + date + b"\\x00" + extra
        suffix=b"\\x00"*12
        crc=(~zlib.crc32(data+suffix)) & 0xFFFFFFFF
        return data+suffix+crc.to_bytes(4,"little")

    def test_strict_dfu_date_and_dfu_suffix_crc_accepts_only_expected_change(self):
        old=self.dfu_fixture(b"16-10-2026")
        new=self.dfu_fixture(b"17-10-2026")
        pos=delta.check_dfu_date_only_difference(old,new)
        self.assertEqual(old[pos:pos+1],b"6")
        self.assertEqual(new[pos:pos+1],b"7")

    def test_strict_dfu_rejects_additional_payload_difference_with_valid_crc(self):
        old=self.dfu_fixture(b"16-10-2026")
        new=self.dfu_fixture(b"17-10-2026",extra=b"code")
        with self.assertRaisesRegex(ValueError,"unexpected DFU payload"):
            delta.check_dfu_date_only_difference(old,new)

    def test_strict_dfu_rejects_corrupt_suffix_crc_and_missing_stamp(self):
        old=self.dfu_fixture(b"16-10-2026")
        new=self.dfu_fixture(b"17-10-2026")
        damaged=new[:-1]+bytes([new[-1] ^ 0x01])
        with self.assertRaisesRegex(ValueError,"invalid DFU CRC"):
            delta.check_dfu_date_only_difference(old,damaged)
        with self.assertRaisesRegex(ValueError,"build-date"):
            delta.check_dfu_date_only_difference(old,self.dfu_fixture(b"18-10-2026"))


if __name__=="__main__":
    unittest.main()
