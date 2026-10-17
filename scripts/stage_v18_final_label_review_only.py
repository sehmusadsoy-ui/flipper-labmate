#!/usr/bin/env python3
"""Stage a v1.8 badge RC only in a disposable, matched Momentum app tree.

No firmware/device interaction, no installation, and no source repo mutation.
This cannot turn a DEV firmware into a Stable release without final review.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import subprocess

PINNED_TRIAL_SOURCE = "ba379f20fb29369501e1057f570a911f71ac83f8"
DEV_LINE = '#define LABMATE_VERSION_TEXT "v1.8DEV"'
FINAL_LINE = '#define LABMATE_VERSION_TEXT "v1.8"'
APP_MANIFEST_LINE = 'fap_version="1.8"'
SOURCES = ("*.c", "*.h")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_map(root: Path) -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for pattern in SOURCES:
        for file in root.glob(pattern):
            if not file.is_file() or file.is_symlink():
                raise ValueError("symlink or invalid source file: " + file.name)
            result[file.name] = file.read_bytes()
    return result


def verify_trial_source(repo: Path) -> None:
    """Compare Git objects, not historical assertions about CI artifacts."""
    command = ["git", "-C", str(repo), "diff", "--name-only",
               PINNED_TRIAL_SOURCE, "HEAD", "--", "src/",
               "application.fam", "labmate_10px.png",
               ":(glob)scripts/patch_momentum_*.py"]
    check = subprocess.run(command, text=True, capture_output=True, check=False)
    if check.returncode:
        raise ValueError("pinned trial git history unavailable/diff failure")
    if check.stdout.strip():
        raise ValueError("production app or pinned firmware patch sources changed")
    head = subprocess.run(["git", "-C", str(repo), "status", "--porcelain",
                           "--untracked-files=no", "--", "src", "application.fam",
                           "labmate_10px.png"], capture_output=True,
                          text=True, check=True)
    if head.stdout.strip():
        raise ValueError("uncommitted production source modification")


def stage(repo: Path, target: Path) -> dict[str, str]:
    """Strict one-macro staged transformation; fails closed on any other diff."""
    if repo.resolve() == target.resolve() or repo.resolve() in target.resolve().parents:
        raise ValueError("staged destination must not be inside LabMate source tree")
    if target.resolve() in repo.resolve().parents:
        raise ValueError("LabMate source must not reside in staged destination")
    original = repo / "src"
    staged = target / "src"
    if not original.is_dir() or not staged.is_dir():
        raise ValueError("missing staged or original src")
    if (repo/"application.fam").read_bytes() != (target/"application.fam").read_bytes():
        raise ValueError("application manifest changed before release overlay")
    if (repo/"labmate_10px.png").read_bytes() != (target/"labmate_10px.png").read_bytes():
        raise ValueError("icon changed before release overlay")
    manifest = (repo/"application.fam").read_text()
    if manifest.count(APP_MANIFEST_LINE) != 1:
        raise ValueError("1.8 FAP manifest identity does not match expected")
    source = file_map(original)
    current = file_map(staged)
    if source.keys() != current.keys() or not source:
        raise ValueError("staged and source compilation units differ")
    if any(source[k] != current[k] for k in source):
        raise ValueError("preexisting staged source edit; refuse overlay")
    if "labmate_internal.h" not in current:
        raise ValueError("version header absent")
    data = current["labmate_internal.h"]
    if data.count(DEV_LINE.encode()) != 1 or data.count(FINAL_LINE.encode()):
        raise ValueError("development version macro absent or ambiguous")
    updated = data.replace(DEV_LINE.encode(), FINAL_LINE.encode())
    if updated == data:
        raise ValueError("version overlay would be no-op")
    header = staged/"labmate_internal.h"
    header.write_bytes(updated)
    after = file_map(staged)
    if source.keys() != after.keys():
        raise ValueError("source inventory changed during staging")
    if any(after[k] != (updated if k == "labmate_internal.h" else source[k])
           for k in source):
        raise ValueError("overlay altered other compiled source files")
    if (repo/"src"/"labmate_internal.h").read_bytes() != data:
        raise ValueError("original source modified")
    if (target/"application.fam").read_bytes() != (repo/"application.fam").read_bytes():
        raise ValueError("staged app manifest was modified")
    return {
        "source_file_count": str(len(source)),
        "original_header_sha256": sha(data),
        "review_header_sha256": sha(updated),
        "overlay": 'one staged macro: v1.8DEV -> v1.8',
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--staged", type=Path, required=True)
    args = ap.parse_args()
    verify_trial_source(args.repo)
    result = stage(args.repo, args.staged)
    for key, value in result.items():
        print("E11 RC " + key + ": " + value)
    print("E11 V1.8 FINAL-LABEL REVIEW OVERLAY PASS - NO DEVICE / NO RELEASE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
