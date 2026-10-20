#!/usr/bin/env python3
"""Build-only v1.9 Logic Scope UI polish on native Windows.

NO Flipper COM/USB, upload, install, runfap, firmware flash or data writes.
Reuses only the existing isolated, already-patched E11 SDK after verifying
the exact source baseline and backing up its previous, known-good FAP to PC.
All four strict host tests run before any SDK app source file is changed.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from zipfile import ZipFile, is_zipfile

SOURCE = "3f2f132a178bec725f21e7994a775dbb2f3d2426"
MOMENTUM = "d3f89dfe2ef6b01839201598e9be1590cba80322"
OLD_FAP_BYTES = 97724
OLD_FAP_SHA = "b5a4e3dc4a8b03f89f115180ba335963b2bb7a0d42713bbc25e056d07abe55b8"
OLD_APP_FAM = "a7b6623fd1b118e9b76034e070ed202246eb4251"
UI = {
    # application_user/labmate/src filenames: (previous source blob, new source blob)
    "labmate_scope_display.c": ("5ef5665a39540d3d7ee99c5fa9b3c8ec77ff1d5e",
                                 "1d7012b2a3176aa4035db4ac2a6dbb3faa715fb4"),
    "labmate_scope_pair_view.c": ("79282673085a09e4bc88b79fa400c4ff62122f0a",
                                   "1395ff12e833830f3527a2eca8f1d2b259b8f915"),
    "labmate_scope_pair_view.h": ("6820b39eaeccb7c744dfecb5f773c2ad316f9009",
                                   "616713f3b278f6dfde9122911fa1cc0957213419"),
    "labmate_scope_reference_view.c": ("a76d86128e7aeef325b7a57d6ea70ad8f5b8ef72",
                                        "76171fcf86818520488ccaa041ff42c3dc8a23ed"),
    "labmate_internal.h": ("0262efdaa5662e61ee7156045f6b6f86b9cb339f",
                            "afca584528de85788df0589f3e22ac3fbe1a98ff"),
    "labmate_view.c": ("d39f2a71b6233fef38fa9af84871da9950f0a933",
                       "e5f95321c5fc8f1423cbce2974da46d582f19907"),
    "labmate_scope_bridge.c": ("9c6fc49628e193ca5a0ca2f84fb4b22a74d53102",
                                "0211fa9852ae72cc50d67c5b32dad9b1110a6d7e"),
}
HOST_TESTS = {
    "test_labmate_scope_display.c": "85b979c8c4c3813d4b2929671ffcca6ad5bfd897",
    "test_labmate_scope_pair_view.c": "b880791fada9fc8c690911cf20805b65898ead1c",
    "test_scope_reference_view.c": "46e2f70183250381d530c0298efe6e1e766092c6",
    "test_labmate_scope_focus.c": "7530cfee04c230eca3a705a346e8bd6d219b00c3",
}
REVIEW = "841eb5f982e5c2e951cc98278060eedac078941b"


def need(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def blob(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


def hash_sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        text=True, stderr=subprocess.PIPE, timeout=30).strip()


def run(args, *, cwd=None, env=None, timeout=180) -> None:
    print("COMMAND:", " ".join(map(str, args)), flush=True)
    completed = subprocess.run(
        list(map(str, args)), cwd=cwd, env=env, timeout=timeout)
    need(completed.returncode == 0,
         f"command exit {completed.returncode}; no further actions")


def source_checkout(folder: Path) -> Path:
    need(not folder.exists(), "UI review source folder already exists; preserve it and STOP")
    folder.mkdir(parents=True)
    archive = folder / "github-source.zip"
    endpoint = "repos/sehmusadsoy-ui/flipper-labmate/zipball/" + SOURCE
    print("AUTHENTICATED_PINNED_UI_SOURCE:", SOURCE, flush=True)
    with archive.open("xb") as output:
        # Binary stdout must never pass through Windows PowerShell redirection.
        rc = subprocess.run(["gh", "api", endpoint],
                            stdout=output, timeout=180).returncode
        need(rc == 0, "authenticated GitHub API ZIP retrieval failed")
    need(archive.stat().st_size <= 50_000_000 and is_zipfile(archive),
         "unrecognized/oversized GitHub source ZIP")
    extracted = folder / "source"
    extracted.mkdir()
    with ZipFile(archive) as zipped:
        entries = zipped.infolist()
        need(entries and sum(e.file_size for e in entries) <= 100_000_000,
             "invalid GitHub expanded archive size")
        roots = {e.filename.split("/")[0] for e in entries if e.filename}
        need(len(roots) == 1, "archive has multiple roots")
        root = roots.pop()
        need(root.startswith("sehmusadsoy-ui-flipper-labmate-" + SOURCE[:7]),
             "GitHub archive root does not match pinned commit")
        for e in entries:
            name = e.filename
            need("\\" not in name and not name.startswith("/") and
                 all(part not in ("", ".", "..") for part in name.rstrip("/").split("/")),
                 "untrusted ZIP path")
            mode = e.external_attr >> 16
            need(not stat.S_ISLNK(mode), "ZIP symlink refused")
            parts = name.rstrip("/").split("/")[1:]
            if not parts:
                continue
            dst = extracted.joinpath(*parts)
            if e.is_dir():
                dst.mkdir(parents=True, exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                need(e.file_size <= 20_000_000, "oversized ZIP file")
                with zipped.open(e) as src, dst.open("xb") as out:
                    shutil.copyfileobj(src, out)
    for name, (_, current) in UI.items():
        need(blob(extracted / "src" / name) == current,
             "UI source Git blob differs from pinned version: " + name)
    for name, current in HOST_TESTS.items():
        need(blob(extracted / "tests" / name) == current,
             "host test Git blob differs from pinned version: " + name)
    need(blob(extracted / "scripts/verify_v19_e11_sdk_fap.py") == REVIEW,
         "pinned E11 ABI FAP verifier changed")
    need(blob(extracted / "application.fam") == OLD_APP_FAM,
         "LabMate manifest no longer matches prior application")
    print("PINNED_UI_SOURCE_AND_HOST_TEST_BLOBS: PASS", flush=True)
    return extracted


def check_host_tests(src: Path, workspace: Path) -> None:
    cc = Path(r"C:\msys64\ucrt64\bin\cc.exe")
    need(cc.is_file(), "native MSYS2 UCRT64 cc.exe absent")
    run([cc, "--version"])
    env = dict(os.environ)
    env["PATH"] = str(cc.parent) + os.pathsep + env.get("PATH", "")
    target = workspace / "host-tests"
    target.mkdir()
    matrix = (
        ("display", ("tests/test_labmate_scope_display.c",
                     "src/labmate_scope_display.c", "src/labmate_scope_plot.c")),
        ("ab_compare", ("tests/test_labmate_scope_pair_view.c",
                        "src/labmate_scope_pair_view.c", "src/labmate_scope_pair.c",
                        "src/labmate_scope_compare.c")),
        ("reference", ("tests/test_scope_reference_view.c",
                       "src/labmate_scope_reference_view.c",
                       "src/labmate_scope_tolerance.c", "src/labmate_scope_compare.c")),
        ("focus", ("tests/test_labmate_scope_focus.c", "src/labmate_scope_plot.c")),
    )
    for title, names in matrix:
        exe = target / (title + ".exe")
        command = [
            cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
            "-Itests/host_stubs", "-Isrc", *(n for n in names),
            "-o", exe,
        ]
        run(command, cwd=src, env=env, timeout=120)
        run([exe], cwd=src, env=env, timeout=45)
        print("UI HOST " + title + ": PASS", flush=True)
    print("V19 UI POLISH HOST C REGRESSIONS: 4/4 PASS", flush=True)


def check_existing(sdk: Path, firmware: Path) -> tuple[Path, Path]:
    need(git_head(firmware) == MOMENTUM and git_head(sdk) == MOMENTUM,
         "original/isolated Momentum baseline changed")
    need((sdk / "fbt.cmd").is_file(), "isolated native FBT runner absent")
    target = sdk / "applications_user/labmate"
    need(blob(target / "application.fam") == OLD_APP_FAM,
         "existing app manifest differs")
    for name, (old, _) in UI.items():
        stage = target / "src" / name
        need(stage.is_file() and blob(stage) == old,
             "prior SDK app UI source has changed: " + name)
    api = (sdk / "targets/f7/api_symbols.csv").read_text(encoding="utf-8")
    for name in ("furi_hal_resource_lease_try_acquire",
                 "furi_hal_resource_lease_release",
                 "furi_hal_gpio_try_add_int_callback"):
        need(f"Function,+,{name}," in api, "isolated E11 API export missing: " + name)
    fap = sdk / "build/f7-firmware-C/.extapps/labmate.fap"
    need(fap.is_file() and fap.stat().st_size == OLD_FAP_BYTES and
         hash_sha256(fap) == OLD_FAP_SHA,
         "previous UI FAP changed; refuse partial overwrite")
    print("ISOLATED_E11_SDK_AND_PRIOR_FAP: PASS", flush=True)
    return target, fap


def backup_previous(old_fap: Path, folder: Path) -> Path:
    # Created only after host PASS and exact SDK/source input audit.
    need(not folder.exists(), "PC candidate backup path already occupied")
    folder.mkdir(parents=True)
    backed = folder / "labmate-v19-before-ui-polish-97724.fap"
    with old_fap.open("rb") as from_file, backed.open("xb") as to_file:
        shutil.copyfileobj(from_file, to_file)
    need(backed.stat().st_size == OLD_FAP_BYTES and
         hash_sha256(backed) == OLD_FAP_SHA,
         "new immutable previous FAP PC backup failed readback")
    print("PREVIOUS_V19_FAP_PC_BACKUP: PASS", flush=True)
    return backed


def main() -> None:
    need(os.name == "nt", "Windows PowerShell/Windows Python only; no WSL")
    home = Path.home()
    sdk = home / "LabMate-v19-WinSDK-050ec62"
    firmware = home / "Momentum-Firmware"
    root = home / ("LabMate-v19-UIPolish-" + SOURCE[:7])
    backup = home / "Documents" / "LabMate-FAP-PC-Backups" / (
        "V19-UI-POLISH-PREBUILD-" + SOURCE[:7])
    need(firmware.is_dir() and sdk.is_dir(), "expected old and isolated SDK absent")
    need(not root.exists() and not backup.exists(),
         "UI trial/workspace already exists; refuse automatic retry")
    old_target, old_fap = check_existing(sdk, firmware)
    source = source_checkout(root)
    check_host_tests(source, root)
    saved = backup_previous(old_fap, backup)
    # All allowed local FAP UI sources are attested before any are copied.
    for name, (_, new_blob) in UI.items():
        from_file = source / "src" / name
        to_file = old_target / "src" / name
        need(blob(from_file) == new_blob, "source drift before copying " + name)
        shutil.copyfile(from_file, to_file)
        need(blob(to_file) == new_blob, "SDK UI file copy/readback failed " + name)
    print("ISOLATED_E11_SDK_UI_SOURCE_UPDATE: 7/7 PASS", flush=True)
    env = dict(os.environ)
    for var in ("FBT_ROOT", "FBT_NOENV", "FBT_TOOLCHAIN_PATH", "FBT_TOOLCHAIN_ROOT"):
        env.pop(var, None)
    env["GIT_PAGER"] = "cat"
    run(["cmd.exe", "/d", "/c", "fbt.cmd", "fap_labmate"],
        cwd=sdk, env=env, timeout=1500)
    need(old_fap.is_file() and hash_sha256(old_fap) != OLD_FAP_SHA,
         "new UI FAP was not generated")
    run([sys.executable, source / "scripts/verify_v19_e11_sdk_fap.py",
         sdk, old_fap], timeout=120)
    print("V19 UI POLISH WINDOWS FAP BUILD ONLY PASS", flush=True)
    print("UI_SOURCE_COMMIT:", SOURCE)
    print("FAP_PATH:", old_fap)
    print("FAP_BYTES:", old_fap.stat().st_size)
    print("FAP_SHA256:", hash_sha256(old_fap))
    print("PREVIOUS_FAP_PC_BACKUP:", saved)
    print("DEVICE_WRITES: ZERO | FIRMWARE_FLASH: NO | AUTO_INSTALL: NO")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("V19 UI POLISH BUILD NO-GO:", e, file=sys.stderr)
        print("NO DEVICE WRITES/FLASH. DO NOT USE AN UNVERIFIED PARTIAL FAP.",
              file=sys.stderr)
        raise SystemExit(1)
