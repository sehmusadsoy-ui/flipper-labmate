#!/usr/bin/env python3
"""OFFLINE read-only E11 v1.8 matched-pair operator input preflight.

NO Flipper serial port, qFlipper, flash, install, SD write, restore or upload.
Checks exact independently pinned full CI candidate, existing readback EXITFIX,
rollback candidates, local SD data copy and locally saved settings TGZ.
A PASS is NOT a flash authorization or proof that recovery would succeed.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import tarfile

SOURCE = "ba379f20fb29369501e1057f570a911f71ac83f8"
RUN = 38966248325
ARTIFACTS = {
    "labmate.fap": "2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0",
    "js_gpio.module": "fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a",
    "firmware.dfu": "88d12fee4edb4fa0ec042a1b526ddb41b8db36aeb9554c6a9a8aef1c37e4e1b0",
    "firmware-full-update.tgz": "11ed3cdf4e99c9c7218973695d349cd946be97d21dfc59231113bde15e94c553",
}
ROLLBACK = {
    "flipper-z-f7-update-mntm-012.tgz": "1d9e1e600c8680172ff6f6913ca0b12484e7d45adbc72a66552e534784c8c1a7",
    "labmate-v18-stable.fap": "119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0",
}
INSTALLED_EXITFIX = "7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be"
SETTINGS = "a0487ede35b8cec4cef505faf57363768fc1bc02d5d7c1dd3a8dcfa282c00ef2"


def file_sha(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
        raise ValueError("missing, empty or symlinked local file: " + path.name)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while data := handle.read(1024 * 1024):
            digest.update(data)
    return digest.hexdigest()


def assert_sha(path: Path, expected: str) -> None:
    if file_sha(path) != expected:
        raise ValueError("independently pinned SHA256 mismatch: " + path.name)


def check_data_backup(directory: Path, minimum_files: int = 14) -> int:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("missing or linked local LabMate data backup")
    count = 0
    for item in directory.rglob("*"):
        if item.is_symlink() or not (item.is_file() or item.is_dir()):
            raise ValueError("unsafe data backup entry")
        if item.is_file():
            file_sha(item)
            count += 1
    if count < minimum_files:
        raise ValueError("incomplete local LabMate data backup")
    return count


def check_settings_archive(path: Path, *, expected_sha: str = SETTINGS) -> None:
    assert_sha(path, expected_sha)
    files = directories = total = 0
    seen: set[str] = set()
    with tarfile.open(path, "r:gz") as tf:
        for member in tf:
            name = member.name.rstrip("/")
            parts = name.split("/")
            if (
                not name or name.startswith(("/", "\\"))
                or "\\" in name or ":" in name
                or any(part in ("", ".", "..") for part in parts)
                or name in seen
            ):
                raise ValueError("unsafe/duplicate settings archive path")
            seen.add(name)
            if member.isdir():
                directories += 1
            elif member.isfile():
                files += 1
                total += member.size
                if member.size < 0 or total > 10_000_000:
                    raise ValueError("oversized settings archive")
                stream = tf.extractfile(member)
                if stream is None:
                    raise ValueError("unreadable settings archive file")
                read_bytes = 0
                while chunk := stream.read(65536):
                    read_bytes += len(chunk)
                if read_bytes != member.size:
                    raise ValueError("truncated settings archive file")
            else:
                raise ValueError("unsupported settings archive member")
    if (files, directories) != (14, 1):
        raise ValueError("unexpected settings archive structure")


def preflight(
    candidate: Path,
    rollback: Path,
    installed_copy: Path,
    data_backup: Path,
    settings_archive: Path,
    *,
    artifact_hashes: dict[str, str] = ARTIFACTS,
    rollback_hashes: dict[str, str] = ROLLBACK,
    installed_hash: str = INSTALLED_EXITFIX,
    settings_hash: str = SETTINGS,
    full_verify=None,
) -> int:
    if candidate.is_symlink() or not candidate.is_dir():
        raise ValueError("missing or symlinked full candidate directory")
    if rollback.is_symlink() or not rollback.is_dir():
        raise ValueError("missing or symlinked rollback directory")
    if set(artifact_hashes) != set(ARTIFACTS):
        raise ValueError("incomplete pinned candidate list")
    for name, digest in artifact_hashes.items():
        assert_sha(candidate / name, digest)
    # Full archive/provenance/FAP+firmware+JS audit; fails on extra files
    # and mismatched build source or CI run.
    if full_verify is None:
        from verify_v18_full_review_pair import verify as full_verify
    full_verify(candidate, SOURCE, RUN)
    for name, digest in rollback_hashes.items():
        assert_sha(rollback / name, digest)
    assert_sha(installed_copy, installed_hash)
    count = check_data_backup(data_backup)
    check_settings_archive(settings_archive, expected_sha=settings_hash)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--rollback", type=Path, required=True)
    parser.add_argument("--installed-fap-copy", type=Path, required=True)
    parser.add_argument("--data-backup", type=Path, required=True)
    parser.add_argument("--settings-archive", type=Path, required=True)
    args = parser.parse_args()
    try:
        count = preflight(
            args.candidate, args.rollback, args.installed_fap_copy,
            args.data_backup, args.settings_archive,
        )
    except (OSError, ValueError, UnicodeError, tarfile.TarError) as exc:
        parser.exit(1, "LOCAL E11 PREFLIGHT REFUSED: " + str(exc) + "\n")
    print("E11 full-pair source/run/provenance and local SHA256: PASS")
    print("Current EXITFIX FAP local copy digest: PASS")
    print("Rollback firmware / Stable FAP local digest: PASS")
    print("LabMate local data backup: " + str(count) + " readable files")
    print("Settings TGZ pinned digest / 14 files + 1 dir: PASS")
    print("LOCAL E11 INPUT PREFLIGHT PASS - NO FLASH, NO DEVICE ACCEPTANCE")
    print("RESTORE NOT REHEARSED. Operator consent still required before device write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
