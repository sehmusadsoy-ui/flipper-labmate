#!/usr/bin/env python3
"""Negative and positive tests for the no-install v1.8 review candidate."""
from pathlib import Path
import importlib.util
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "review_stage", ROOT/"scripts/stage_v18_final_label_review_only.py")
assert spec and spec.loader
overlay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overlay)


class ReleaseLabelOverlay(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="v18_label_guard_")
        root = Path(self.temp.name)
        self.repo = root/"labmate"
        self.staged = root/"firmware"/"applications_user"/"labmate"
        for path in (self.repo, self.staged):
            (path/"src").mkdir(parents=True)
            (path/"src"/"labmate_internal.h").write_text(
                '#pragma once\n#define LABMATE_VERSION_TEXT "v1.8DEV"\n')
            (path/"src"/"labmate.c").write_text('int dummy(void){return 0;}\n')
            (path/"application.fam").write_text(
                'App(appid="labmate", fap_version="1.8")\n')
            (path/"labmate_10px.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    def tearDown(self):
        self.temp.cleanup()

    def test_only_header_diff_and_original_unmodified(self):
        old = (self.repo/"src"/"labmate_internal.h").read_bytes()
        other = (self.repo/"src"/"labmate.c").read_bytes()
        result = overlay.stage(self.repo, self.staged)
        self.assertEqual(result["source_file_count"], "2")
        self.assertEqual((self.repo/"src"/"labmate_internal.h").read_bytes(), old)
        self.assertEqual((self.staged/"src"/"labmate.c").read_bytes(), other)
        self.assertIn(b'"v1.8"', (self.staged/"src"/"labmate_internal.h").read_bytes())
        self.assertNotIn(b'v1.8DEV', (self.staged/"src"/"labmate_internal.h").read_bytes())

    def test_refuses_repeated_overlay(self):
        overlay.stage(self.repo, self.staged)
        with self.assertRaises(ValueError):
            overlay.stage(self.repo, self.staged)

    def test_refuses_unreviewed_source_edit(self):
        (self.staged/"src"/"labmate.c").write_text("int changed(void);\n")
        with self.assertRaisesRegex(ValueError, "preexisting"):
            overlay.stage(self.repo, self.staged)

    def test_refuses_missing_extra_or_symlinked_source(self):
        (self.staged/"src"/"extra.c").write_text("extra")
        with self.assertRaisesRegex(ValueError, "differ"):
            overlay.stage(self.repo, self.staged)
        (self.staged/"src"/"extra.c").unlink()
        (self.staged/"src"/"labmate.c").unlink()
        with self.assertRaisesRegex(ValueError, "differ"):
            overlay.stage(self.repo, self.staged)

    def test_refuses_manifest_mismatch_and_wrong_badge(self):
        (self.staged/"application.fam").write_text(
            'App(appid="labmate", fap_version="1.9")\n')
        with self.assertRaisesRegex(ValueError, "manifest"):
            overlay.stage(self.repo, self.staged)
        (self.staged/"application.fam").write_text(
            (self.repo/"application.fam").read_text())
        (self.repo/"src"/"labmate_internal.h").write_text(
            '#define LABMATE_VERSION_TEXT "v1.8"\n')
        (self.staged/"src"/"labmate_internal.h").write_text(
            '#define LABMATE_VERSION_TEXT "v1.8"\n')
        with self.assertRaisesRegex(ValueError, "macro"):
            overlay.stage(self.repo, self.staged)

    def test_provenance_guard_declines_changed_code(self):
        # Local Git fixture: test the exact baseline-compare rule without
        # changing the actual immutable pinned constant in repo source.
        r=self.repo
        def git(*args):
            return subprocess.check_output(["git", "-C", str(r), *args],
                                           stderr=subprocess.PIPE, text=True).strip()
        git("init")
        git("config", "user.email", "host-test@example.invalid")
        git("config", "user.name", "E11 host test")
        git("add", ".")
        git("commit", "-m", "baseline")
        sha=git("rev-parse", "HEAD")
        old=overlay.PINNED_TRIAL_SOURCE
        overlay.PINNED_TRIAL_SOURCE=sha
        try:
            overlay.verify_trial_source(r)
            (r/"src"/"labmate.c").write_text("int changed(void) { return 1; }\n")
            with self.assertRaisesRegex(ValueError, "uncommitted"):
                overlay.verify_trial_source(r)
            git("add", ".")
            git("commit", "-m", "modified")
            with self.assertRaisesRegex(ValueError, "production app"):
                overlay.verify_trial_source(r)
        finally:
            overlay.PINNED_TRIAL_SOURCE=old


if __name__=="__main__":
    unittest.main()
