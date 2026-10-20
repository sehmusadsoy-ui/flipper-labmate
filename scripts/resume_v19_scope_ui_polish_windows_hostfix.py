#!/usr/bin/env python3
"""Resume 2026-10-20 Windows UI polish after strict GCC 16 host-test failure.

Build-only. Leaves the pinned downloaded source and prior known-good FAP
unchanged until all four host tests pass and PC FAP backup is verified.
Uses TWO exact Git-blob-attested test overlays (comment and signedness).
No COM, USB, runfap, installer, firmware flash, data edits, or retries.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

SOURCE = "6d258bff2f2f0473d24aea0d9fc563ba3ef6293b"
MOMENTUM = "d3f89dfe2ef6b01839201598e9be1590cba80322"
OLD_FAP_BYTES = 97724
OLD_FAP_SHA = "b5a4e3dc4a8b03f89f115180ba335963b2bb7a0d42713bbc25e056d07abe55b8"
FAM = "a7b6623fd1b118e9b76034e070ed202246eb4251"
REVIEW = "841eb5f982e5c2e951cc98278060eedac078941b"
UI = {
    "labmate_scope_display.c": ("5ef5665a39540d3d7ee99c5fa9b3c8ec77ff1d5e", "1d7012b2a3176aa4035db4ac2a6dbb3faa715fb4"),
    "labmate_scope_pair_view.c": ("79282673085a09e4bc88b79fa400c4ff62122f0a", "1395ff12e833830f3527a2eca8f1d2b259b8f915"),
    "labmate_scope_pair_view.h": ("6820b39eaeccb7c744dfecb5f773c2ad316f9009", "616713f3b278f6dfde9122911fa1cc0957213419"),
    "labmate_scope_reference_view.c": ("a76d86128e7aeef325b7a57d6ea70ad8f5b8ef72", "41734b19cf5ed15129aa5fdf670a725e70bb24c7"),
    "labmate_internal.h": ("0262efdaa5662e61ee7156045f6b6f86b9cb339f", "afca584528de85788df0589f3e22ac3fbe1a98ff"),
    "labmate_view.c": ("d39f2a71b6233fef38fa9af84871da9950f0a933", "e5f95321c5fc8f1423cbce2974da46d582f19907"),
    "labmate_scope_bridge.c": ("9c6fc49628e193ca5a0ca2f84fb4b22a74d53102", "0211fa9852ae72cc50d67c5b32dad9b1110a6d7e"),
}
TESTS_OLD = {
    "test_labmate_scope_display.c": "85b979c8c4c3813d4b2929671ffcca6ad5bfd897",
    "test_labmate_scope_pair_view.c": "b880791fada9fc8c690911cf20805b65898ead1c",
    "test_scope_reference_view.c": "ad176aa87484df5803d401909dc15fa1395a513c",
    "test_labmate_scope_focus.c": "7530cfee04c230eca3a705a346e8bd6d219b00c3",
}
STUB_OLD = "84659bd11079c560b43520b10f1626e2e3cec7e1"
STUB_FIXED = "1a21d1315a098425a4282285417ad2908f041c27"
DISPLAY_FIXED = "4a91c0b6404a0926eb4cce676a217c06e2958e85"

def require(ok: bool, why: str) -> None:
    if not ok:
        raise RuntimeError(why)

def git_blob_bytes(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def git_blob(path: Path) -> str:
    return git_blob_bytes(path.read_bytes())

def sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()

def run(args, *, cwd=None, env=None, timeout=180) -> None:
    command = list(map(str, args))
    print("COMMAND:", " ".join(command), flush=True)
    result = subprocess.run(command, cwd=cwd, env=env, timeout=timeout)
    require(result.returncode == 0, f"process exit {result.returncode}; STOP")

def git_head(path: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        text=True, stderr=subprocess.PIPE, timeout=30).strip()

def check_inputs(src: Path, original: Path, sdk: Path) -> tuple[Path, Path]:
    require(os.name == "nt", "native Windows only; no WSL")
    require(src.is_dir() and original.is_dir() and sdk.is_dir(), "previous isolated build inputs absent")
    require(not src.is_symlink() and not sdk.is_symlink(), "source/SDK symlinks rejected")
    require(git_head(original) == MOMENTUM and git_head(sdk) == MOMENTUM,
            "Momentum exact E11 SDK provenance mismatch")
    require((sdk / "fbt.cmd").is_file(), "native FBT missing")
    for name, (_, current) in UI.items():
        require(git_blob(src / "src" / name) == current,
                "pinned UI source altered: " + name)
    for name, current in TESTS_OLD.items():
        require(git_blob(src / "tests" / name) == current,
                "prior host test source altered: " + name)
    require(git_blob(src / "tests/host_stubs/gui/gui.h") == STUB_OLD,
            "previous host Canvas stub altered")
    require(git_blob(src / "application.fam") == FAM,
            "pinned application.fam mismatch")
    require(git_blob(src / "scripts/verify_v19_e11_sdk_fap.py") == REVIEW,
            "pinned E11 native FAP verifier mismatch")
    dest = sdk / "applications_user/labmate"
    require(git_blob(dest / "application.fam") == FAM,
            "isolated SDK application.fam mismatch")
    for name, (old, _) in UI.items():
        require(git_blob(dest / "src" / name) == old,
                "isolated SDK old UI file changed: " + name)
    api = (sdk / "targets/f7/api_symbols.csv").read_text(encoding="utf-8")
    for symbol in ("furi_hal_resource_lease_try_acquire",
                   "furi_hal_resource_lease_release",
                   "furi_hal_gpio_try_add_int_callback"):
        require(f"Function,+,{symbol}," in api,
                "isolated firmware API export missing: " + symbol)
    fap = sdk / "build/f7-firmware-C/.extapps/labmate.fap"
    require(fap.is_file() and fap.stat().st_size == OLD_FAP_BYTES and
            sha256(fap) == OLD_FAP_SHA,
            "old working 97,724-byte FAP changed; refuse to overwrite")
    print("PINNED_SOURCE_7_7_AND_PRIOR_FAP: PASS", flush=True)
    return dest, fap

def patch_exact(src: bytes, anchor: bytes, replacement: bytes,
                before: str, after: str) -> bytes:
    require(git_blob_bytes(src) == before, "original host test input mismatch")
    require(src.count(anchor) == 1, "host test change anchor ambiguous")
    updated = src.replace(anchor, replacement, 1)
    require(git_blob_bytes(updated) == after,
            "host-only overlay Git blob differs from GitHub reviewed fix")
    return updated

def prepare_test_overlays(src: Path, workspace: Path) -> tuple[Path, Path]:
    overlay = workspace / "host-fix-gcc16"
    require(not overlay.exists(), "host-fix overlay already exists; do not re-run")
    overlays = overlay / "tests"
    stub_dir = overlays / "host_stubs/gui"
    stub_dir.mkdir(parents=True)
    old = (src / "tests/host_stubs/gui/gui.h").read_bytes()
    old_comment = b" * This is NEVER included by application.fam (src/*.c)."
    new_comment = b" * This stub is used ONLY by native host unit tests, not firmware."
    fixed_stub = patch_exact(old, old_comment, new_comment, STUB_OLD, STUB_FIXED)
    (stub_dir / "gui.h").write_bytes(fixed_stub)
    original_test = (src / "tests/test_labmate_scope_display.c").read_bytes()
    old_check = (
        b"        assert(x0 >= LABMATE_SCOPE_PLOT_X_LEFT && x0 <= LABMATE_SCOPE_PLOT_X_RIGHT);\n"
        b"        assert(x1 >= LABMATE_SCOPE_PLOT_X_LEFT && x1 <= LABMATE_SCOPE_PLOT_X_RIGHT);")
    new_check = (
        b"        assert(x0 >= (int32_t)LABMATE_SCOPE_PLOT_X_LEFT &&\n"
        b"               x0 <= (int32_t)LABMATE_SCOPE_PLOT_X_RIGHT);\n"
        b"        assert(x1 >= (int32_t)LABMATE_SCOPE_PLOT_X_LEFT &&\n"
        b"               x1 <= (int32_t)LABMATE_SCOPE_PLOT_X_RIGHT);")
    fixed_test = patch_exact(
        original_test, old_check, new_check,
        TESTS_OLD["test_labmate_scope_display.c"], DISPLAY_FIXED)
    display_test = overlays / "test_labmate_scope_display.c"
    display_test.write_bytes(fixed_test)
    print("EXACT_GITHUB_GCC16_HOST_TEST_OVERLAYS: 2/2 PASS", flush=True)
    return overlay, display_test

def host_tests(src: Path, workspace: Path) -> None:
    cc = Path(r"C:\msys64\ucrt64\bin\cc.exe")
    require(cc.is_file(), "MSYS2 UCRT64 cc.exe missing")
    run([cc, "--version"])
    env = dict(os.environ)
    env["PATH"] = str(cc.parent) + os.pathsep + env.get("PATH", "")
    overlay, test_display = prepare_test_overlays(src, workspace)
    target = workspace / "host-tests-gcc16"
    require(not target.exists(), "host-tests-gcc16 already exists; preserve and STOP")
    target.mkdir()
    matrix = (
        ("display", (test_display, "src/labmate_scope_display.c", "src/labmate_scope_plot.c")),
        ("ab_compare", ("tests/test_labmate_scope_pair_view.c",
                        "src/labmate_scope_pair_view.c", "src/labmate_scope_pair.c",
                        "src/labmate_scope_compare.c")),
        ("reference", ("tests/test_scope_reference_view.c",
                       "src/labmate_scope_reference_view.c",
                       "src/labmate_scope_tolerance.c", "src/labmate_scope_compare.c")),
        ("focus", ("tests/test_labmate_scope_focus.c", "src/labmate_scope_plot.c")),
    )
    for title, source_files in matrix:
        exe = target / (title + ".exe")
        args = [
            cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
            "-I" + str(overlay / "tests/host_stubs"),
            "-Itests/host_stubs", "-Isrc",
            *source_files, "-o", exe,
        ]
        run(args, cwd=src, env=env, timeout=120)
        run([exe], cwd=src, env=env, timeout=45)
        print("UI_HOST_" + title.upper() + ": PASS", flush=True)
    print("V19 UI POLISH HOST C REGRESSIONS: 4/4 PASS", flush=True)

def backup(fap: Path, backup_folder: Path) -> Path:
    require(not backup_folder.exists(), "PC backup destination occupied; STOP")
    backup_folder.mkdir(parents=True)
    saved = backup_folder / "labmate-v19-before-ui-polish-97724.fap"
    with fap.open("rb") as src, saved.open("xb") as dest:
        shutil.copyfileobj(src, dest)
    require(saved.stat().st_size == OLD_FAP_BYTES and sha256(saved) == OLD_FAP_SHA,
            "prior FAP PC backup SHA256 mismatch")
    print("PREVIOUS_V19_FAP_PC_BACKUP: PASS", flush=True)
    return saved

def main() -> None:
    home = Path.home()
    original = home / "Momentum-Firmware"
    sdk = home / "LabMate-v19-WinSDK-050ec62"
    workspace = home / ("LabMate-v19-UIPolish-" + SOURCE[:7])
    src = workspace / "source"
    backup_dir = home / "Documents/LabMate-FAP-PC-Backups" / (
        "V19-UI-POLISH-PREBUILD-" + SOURCE[:7])
    require(workspace.is_dir(), "prior workspace absent: no redownload/replay")
    require(not backup_dir.exists(), "previous FAP PC backup already exists; STOP")
    dest, fap = check_inputs(src, original, sdk)
    host_tests(src, workspace)
    previous = backup(fap, backup_dir)
    for name, (_, current) in UI.items():
        source_file = src / "src" / name
        target_file = dest / "src" / name
        require(git_blob(source_file) == current, "UI source altered before copy")
        shutil.copyfile(source_file, target_file)
        require(git_blob(target_file) == current, "UI SDK copy readback failed: " + name)
    print("ISOLATED_E11_UI_SOURCE_UPDATE: 7/7 PASS", flush=True)
    env = dict(os.environ)
    for var in ("FBT_ROOT", "FBT_NOENV", "FBT_TOOLCHAIN_PATH", "FBT_TOOLCHAIN_ROOT"):
        env.pop(var, None)
    env["GIT_PAGER"] = "cat"
    run(["cmd.exe", "/d", "/c", "fbt.cmd", "fap_labmate"], cwd=sdk,
        env=env, timeout=1500)
    require(fap.is_file() and sha256(fap) != OLD_FAP_SHA,
            "new FAP missing or unchanged")
    run([sys.executable, src / "scripts/verify_v19_e11_sdk_fap.py", sdk, fap],
        timeout=120)
    print("V19 UI POLISH WINDOWS FAP BUILD ONLY PASS", flush=True)
    print("UI_SOURCE_COMMIT:", SOURCE)
    print("FAP_PATH:", fap)
    print("FAP_BYTES:", fap.stat().st_size)
    print("FAP_SHA256:", sha256(fap))
    print("PREVIOUS_FAP_PC_BACKUP:", previous)
    print("DEVICE_WRITES: ZERO | FIRMWARE_FLASH: NO | AUTO_INSTALL: NO")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("V19 UI POLISH RESUME NO-GO:", exc, file=sys.stderr)
        print("NO DEVICE/USB/FLASH INSTALL. Preserve workspace and current FAP.",
              file=sys.stderr)
        raise SystemExit(1)
