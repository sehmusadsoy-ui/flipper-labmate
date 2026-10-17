#!/usr/bin/env python3
"""Synthetic no-device tests for an optional USB /ext reader and PC copy."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_v18_e11_live_labmate_sd import DeadlineRead
from backup_v18_e11_usb_sd_to_pc import (
    full_inventory, snapshot, name_for_pc, command_path, safe_pc_output,
    _read_exact
)

class FakeSerial:
    """Pinned Momentum device_info already completed; fake CLI only."""
    def __init__(self, data: dict[bytes, bytes], extra_dirs=()):
        self.data = dict(data)
        self.directories = {b"/ext", b"/ext/apps", b"/ext/apps_data",
                            b"/ext/apps_data/labmate", *extra_dirs}
        for path in self.data:
            components = path.split(b"/")
            for i in range(2, len(components)):
                self.directories.add(b"/".join(components[:i]))
        self.pending = bytearray()
        self.trace = []
        self.chunk_data = b""
        self.offset = 0
        self.chunk_size = 0
        self.sabotage_md5 = False
        self.hash_reads = {}
    @property
    def in_waiting(self):
        return len(self.pending)
    def read(self, n):
        result = bytes(self.pending[:n])
        del self.pending[:n]
        return result
    def write(self, raw):
        if raw == b"y":
            self.trace.append(b"read-transfer-handshake")
            part = self.chunk_data[self.offset:self.offset+self.chunk_size]
            self.offset += len(part)
            self.pending.extend(part)
            self.pending.extend(b"\r\nReady?\r\n" if self.offset < len(self.chunk_data) else b"\r\n>: ")
            return len(raw)
        self.trace.append(raw)
        match = re.fullmatch(rb'storage (list|md5|read_chunks) "([^"]+)"(?: ([0-9]+))?\r', raw)
        if not match:
            raise AssertionError("forbidden device command")
        op, path, arg = match.groups()
        self.pending.extend(raw[:-1] + b"\r\n")
        if op == b"list":
            if path not in self.directories:
                self.pending.extend(b"Storage error: not found\r\n>: ")
                return len(raw)
            children = []
            for directory in self.directories:
                if directory != path and directory.startswith(path+b"/"):
                    tail=directory[len(path)+1:]
                    if b"/" not in tail:
                        children.append((b"[D] ",tail,0))
            for file, data in self.data.items():
                if file.startswith(path+b"/"):
                    tail=file[len(path)+1:]
                    if b"/" not in tail:
                        children.append((b"[F] ",tail,len(data)))
            if not children:
                self.pending.extend(b"Empty\r\n>: ")
            else:
                for prefix, n, sz in sorted(children):
                    self.pending.extend(b"\t"+prefix+n+
                        (b"" if prefix==b"[D] " else b" "+str(sz).encode()+b"b")+b"\r\n")
                self.pending.extend(b">: ")
        elif op == b"md5":
            if path not in self.data:
                raise AssertionError("md5 must refer to existing file")
            count=self.hash_reads.get(path,0)
            self.hash_reads[path]=count+1
            md5=hashlib.md5(self.data[path]).hexdigest()
            if self.sabotage_md5 and count >= 1:
                md5="0"*32
            self.pending.extend(md5.encode()+b"\r\n>: ")
        elif op == b"read_chunks":
            self.chunk_data=self.data[path]
            self.offset=0
            self.chunk_size=int(arg)
            self.pending.extend(b"Size: "+str(len(self.chunk_data)).encode()+b"\r\n")
            self.pending.extend(b"\r\nReady?\r\n" if self.chunk_data else b"\r\n>: ")
        return len(raw)


class FakeStorage:
    CLI_EOL = "\r\n"
    CLI_PROMPT = ">: "
    def __init__(self, data, extra_dirs=()):
        self.port=FakeSerial(data,extra_dirs)
        self.read=DeadlineRead(self.port, timeout_seconds=2)


class USBBackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.parent=Path(self.tmp.name)
        self.old=self.parent/"LabMate-old-keep"
        self.old.mkdir()
        (self.old/"log_0041.csv").write_bytes(b"historical data")
        self.out=self.parent/"new-USB-only"
        self.storage=FakeStorage({
            b"/ext/apps/Tools/a.fap": b"real\x00app",
            b"/ext/apps_data/labmate/profiles.bin": b"settings123",
            b"/ext/apps_data/Sensor Tools/caf\xc3\xa9 cfg.ini": b"binaryReady?\r\n>: test",
            b"/ext/.hidden.txt": b"private",
        },extra_dirs=(b"/ext/assets-empty",))

    def test_full_usb_copy_source_md5_pc_sha256_and_incomplete_cleanup(self):
        old=self.old.joinpath("log_0041.csv").read_bytes()
        report=snapshot(self.storage,self.out,(self.old,))
        self.assertEqual(report["usb_snapshot_files_verified"],4)
        self.assertEqual((self.old/"log_0041.csv").read_bytes(),old)
        self.assertEqual((self.out/"apps_data"/"Sensor Tools"/"café cfg.ini").read_bytes(),
                         b"binaryReady?\r\n>: test")
        self.assertTrue((self.out/"assets-empty").is_dir())
        self.assertFalse((self.out/"INCOMPLETE-DO-NOT-RESTORE.txt").exists())
        self.assertTrue((self.out/"READ_ONLY_USB_FILE_CONTENTS_VERIFIED.txt").exists())
        commands=[c for c in self.storage.port.trace if c!=b"read-transfer-handshake"]
        self.assertTrue(all(c.startswith((b"storage list ",b"storage md5 ",
                                          b"storage read_chunks ")) for c in commands))
        self.assertEqual(report["flipper_sd_files_modified"],"NO")
        self.assertEqual(report["firmware_install_authorized"],"NO")

    def test_inventory_only_no_pc_write(self):
        dirs,files=full_inventory(self.storage)
        self.assertEqual(len(files),4)
        self.assertTrue(len(dirs)>=6)
        self.assertFalse(self.out.exists())
        self.assertFalse(any(b"read_chunks" in c for c in self.storage.port.trace))

    def test_non_unicode_remote_component_fails_closed_before_pc_folder(self):
        self.storage=FakeStorage({b"/ext/apps_data/\xff/private.txt": b"bad"})
        with self.assertRaisesRegex(ValueError,"non-UTF8"):
            snapshot(self.storage,self.out,(self.old,))
        self.assertFalse(self.out.exists())

    def test_non_windows_safe_names_refused_before_pc_folder(self):
        for name in (b"CON",b"file?.txt",b"bad.",b"foo\"",b"evil\\child"):
            with self.subTest(name=name),self.assertRaises(ValueError):
                name_for_pc(name)

    def test_casefolded_pc_name_collision_refused(self):
        self.storage=FakeStorage({b"/ext/apps/Tools/A.fap": b"a",
                                  b"/ext/apps/Tools/a.fap": b"b"})
        with self.assertRaisesRegex(ValueError,"collision"):
            snapshot(self.storage,self.out,(self.old,))
        self.assertFalse(self.out.exists())

    def test_existing_output_never_overwritten(self):
        self.out.mkdir()
        (self.out/"keep").write_bytes(b"retain")
        with self.assertRaisesRegex(ValueError,"fresh"):
            snapshot(self.storage,self.out,(self.old,))
        self.assertEqual((self.out/"keep").read_bytes(),b"retain")
        self.assertEqual(self.storage.port.trace,[])

    def test_protected_backup_overlap_never_creates(self):
        with self.assertRaisesRegex(ValueError,"overlaps"):
            safe_pc_output(self.old/"inside",(self.old,))
        self.assertFalse((self.old/"inside").exists())

    def test_md5_drift_marks_partial_snapshot_unverified(self):
        self.storage.port.sabotage_md5=True
        with self.assertRaisesRegex(ValueError,"changed during USB copy"):
            snapshot(self.storage,self.out,(self.old,))
        self.assertTrue((self.out/"INCOMPLETE-DO-NOT-RESTORE.txt").exists())
        self.assertFalse((self.out/"READ_ONLY_USB_FILE_CONTENTS_VERIFIED.txt").exists())

    def test_preflight_file_size_budget_refused_before_output(self):
        import backup_v18_e11_usb_sd_to_pc as mod
        prev=mod.MAX_FILE_BYTES
        try:
            mod.MAX_FILE_BYTES=1
            with self.assertRaisesRegex(ValueError,"limits"):
                snapshot(self.storage,self.out,(self.old,))
        finally:
            mod.MAX_FILE_BYTES=prev
        self.assertFalse(self.out.exists())

    def test_unsafe_raw_cli_name_never_sent(self):
        with self.assertRaisesRegex(ValueError,"Windows"):
            command_path((b"apps_data",b"bad\nname"))

    def test_binary_prefetch_is_consumed_before_serial_read(self):
        serial=FakeSerial({})
        storage=FakeStorage({})
        storage.read.buffer.extend(b"abc")
        self.assertEqual(_read_exact(storage,3),b"abc")

if __name__ == "__main__":
    unittest.main()
