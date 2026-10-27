"""Regression for the real no-device E11 review entrypoint Git preflight."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

WRAPPER = Path(__file__).resolve().parents[1] / "scripts" / "prepare-v20-ultimate-github-e11-review.sh"

@unittest.skipUnless(shutil.which("git") and shutil.which("bash"), "git and bash required")
class ReviewProvenanceGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="labmate-preflight-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "checkout"
        (self.repo / "scripts").mkdir(parents=True)
        (self.repo / "src").mkdir()
        shutil.copyfile(WRAPPER, self.repo / "scripts" / WRAPPER.name)
        (self.repo / "scripts" / "build-v20-ultimate-e11-review.sh").write_text(
            'printf "invoked\\n" > "$LABMATE_PROBE_MARKER"\nexit 7\n', encoding="utf-8")
        (self.repo / ".gitignore").write_text("ignored-output/\n", encoding="utf-8")
        (self.repo / "src" / "original.c").write_text("/* tracked */\n", encoding="utf-8")
        self.git("init", "-q")
        self.git("config", "user.email", "labmate-gate@example.invalid")
        self.git("config", "user.name", "LabMate CI")
        self.git("checkout", "-qb", "dev/v2.0-signal-doctor")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, check=True,
                       capture_output=True, text=True)

    def invoke(self):
        marker = self.root / "builder-was-called"
        env = os.environ.copy()
        env.update({
            "LABMATE_E11_WORK": str(self.root / "fresh-review"),
            "LABMATE_REVIEW_LOG": str(self.root / "fresh-review.log"),
            "LABMATE_PROBE_MARKER": str(marker),
        })
        proc = subprocess.run(["bash", str(self.repo / "scripts" / WRAPPER.name)],
                              cwd=self.repo, env=env, capture_output=True, text=True)
        return proc, marker.exists()

    def test_clean_checkout_reaches_isolated_builder(self):
        proc, invoked = self.invoke()
        self.assertTrue(invoked, proc.stderr)
        self.assertEqual(proc.returncode, 1)  # mock builder intentionally refuses

    def test_untracked_source_blocks_before_builder(self):
        (self.repo / "src" / "untracked-extra.c").write_text("/* user source */\n")
        proc, invoked = self.invoke()
        self.assertFalse(invoked)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("tracked or untracked changes", proc.stderr)

    def test_tracked_edit_blocks_before_builder(self):
        (self.repo / "src" / "original.c").write_text("/* local user edit */\n")
        proc, invoked = self.invoke()
        self.assertFalse(invoked)
        self.assertEqual(proc.returncode, 2)

    def test_ignored_build_outputs_do_not_block(self):
        ignored = self.repo / "ignored-output"
        ignored.mkdir()
        (ignored / "output.tmp").write_text("generated\n")
        proc, invoked = self.invoke()
        self.assertTrue(invoked, proc.stderr)
        self.assertEqual(proc.returncode, 1)

    def test_wrong_branch_blocks_before_builder(self):
        self.git("checkout", "-qb", "other-branch")
        proc, invoked = self.invoke()
        self.assertFalse(invoked)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("expected dev/v2.0-signal-doctor", proc.stderr)

    def test_existing_work_path_never_overwritten(self):
        path = self.root / "fresh-review"
        path.mkdir()
        (path / "important-user-data").write_text("KEEP\n")
        proc, invoked = self.invoke()
        self.assertFalse(invoked)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual((path / "important-user-data").read_text(), "KEEP\n")

if __name__ == "__main__":
    unittest.main()
