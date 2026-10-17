"""Offline synthetic positive/negative tests; no GitHub/device write."""
import copy
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_v18_e11_public_release_preservation_ro.py"
spec = importlib.util.spec_from_file_location("preservation", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

HEAD = "b5cb9c6038427e38895e73d575acbcb8d9c941fa"


def fixture():
    tags = []
    releases = []
    for name, meta in module.RELEASES.items():
        tags.append({"ref": "refs/tags/" + name,
                     "object": {"type": "commit", "sha": meta["commit"]}})
        releases.append({
            "tag_name": name,
            "target_commitish": meta["commit"],
            "draft": False,
            "prerelease": False,
            "published_at": "2026-10-14T10:18:36Z",
            "assets": [{"name": n, "size": s, "digest": h}
                       for n, (s, h) in meta["assets"].items()],
        })
    comparison = {
        "base_commit": {"sha": module.FROZEN_SOURCE},
        "head_commit": {"sha": HEAD},
        "status": "ahead",
        "behind_by": 0,
        "total_commits": 98,
        "files": [{"filename": "docs/evidence.md", "status": "added"},
                  {"filename": "tests/test_protection.py", "status": "added"}],
    }
    return [tags[0], releases[0], tags[1], releases[1], comparison]


class PreservationTests(unittest.TestCase):
    def setUp(self):
        self.inputs = fixture()

    def check(self):
        return module.audit(*self.inputs, HEAD)

    def test_good_boundary_is_pass_not_release_approval(self):
        result = self.check()
        self.assertIn("PRESERVATION", result)
        self.assertIn("NEW STABLE NO-GO", result)

    def test_v14_tag_moved(self):
        self.inputs[0]["object"]["sha"] = "0" * 40
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_v18_tag_moved(self):
        self.inputs[2]["object"]["sha"] = "0" * 40
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_v18_public_fap_overwritten(self):
        self.inputs[3]["assets"][0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_v14_assets_overwritten(self):
        self.inputs[1]["assets"][1]["size"] = 1
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_missing_asset(self):
        self.inputs[3]["assets"].pop()
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_duplicate_asset(self):
        self.inputs[3]["assets"].append(copy.deepcopy(self.inputs[3]["assets"][0]))
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_release_unpublished(self):
        self.inputs[3]["draft"] = True
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_changed_production(self):
        self.inputs[4]["files"].append({"filename": "src/labmate.c"})
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_renamed_source_path(self):
        self.inputs[4]["files"].append({
            "filename": "docs/moved.c", "previous_filename": "src/labmate.c"})
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_native_patch_changed(self):
        self.inputs[4]["files"].append({
            "filename": "scripts/patch_momentum_native_signal_reader_e11_lease.py"})
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_wrong_head(self):
        self.inputs[4]["head_commit"]["sha"] = "0" * 40
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_behind_frozen_source(self):
        self.inputs[4]["behind_by"] = 1
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_compare_file_truncation(self):
        self.inputs[4]["files"] = [{"filename": "docs/test.md"}] * 300
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_compare_commit_truncation(self):
        self.inputs[4]["total_commits"] = 250
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_github_api_response_not_release(self):
        self.inputs[3] = {"message": "Not Found"}
        with self.assertRaises(module.PreservationError):
            self.check()

    def test_version_other_than_pinned(self):
        self.inputs[3]["tag_name"] = "v1.8.1"
        with self.assertRaises(module.PreservationError):
            self.check()


if __name__ == "__main__":
    unittest.main()
