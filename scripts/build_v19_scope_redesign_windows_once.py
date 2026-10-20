#!/usr/bin/env python3
"""One-time, build-only native Windows review of LabMate v1.9 Scope redesign.

GitHub source commit and every changed source/test blob are pinned. This script
does NOT communicate with Flipper, start programs, install an FAP, write SD,
flash firmware, or change the stable version. It backs up the previous FAP on
the Windows PC before modifying only the isolated E11 SDK app source.
Never retry after a failed/partial SDK source swap; inspect exact state first.
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

SOURCE = "5c34ac6e140b5e8276338beb91ea2f9dff76fc84"
MOMENTUM = "d3f89dfe2ef6b01839201598e9be1590cba80322"
OLD_FAP_SHA = "0f0b246d042c45eabe2c29dab692dbc7df20817c419c011ca31a313d4b62141a"
OLD_FAP_SIZE = 99376
FAM = "a7b6623fd1b118e9b76034e070ed202246eb4251"
CHECKER = "841eb5f982e5c2e951cc98278060eedac078941b"
# Source basename: (old installed SDK Git blob, new reviewed Git blob).
CHANGED = {
    "labmate_scope_ui.h": (None, "ed7379c877c541228f0395710091680b7276d800"),
    "labmate_scope_display.c": ("1d7012b2a3176aa4035db4ac2a6dbb3faa715fb4", "d9cee05a54f778754473d63944df380452a410ba"),
    "labmate_scope_display.h": ("f0540b69d2c85a1aecdeb80f942d3d2f3be6db80", "a1c735699d6f814fda411c7e65939cd554456238"),
    "labmate_scope_pair_view.c": ("1395ff12e833830f3527a2eca8f1d2b259b8f915", "9f321a172a1504b254afba8cee029e93a7ac5f7a"),
    "labmate_scope_reference_view.c": ("41734b19cf5ed15129aa5fdf670a725e70bb24c7", "e99740cec7dd2413149a9019eb624fb85ef2f6ee"),
    "labmate_scope_bridge.c": ("0211fa9852ae72cc50d67c5b32dad9b1110a6d7e", "039ec8be0e407af8a077d8f3ca2c219b4240dbd5"),
    "labmate_internal.h": ("afca584528de85788df0589f3e22ac3fbe1a98ff", "ade05ed99bbc4335b6428ba69cbd736395d290b2"),
    "labmate_view.c": ("e5f95321c5fc8f1423cbce2974da46d582f19907", "fb94bff13e95968406a8629c755c810787583f0b"),
    "labmate_ui_primitives.c": ("6bd424ce8bacb5bd8cc023bfd60d3dc5aef10759", "81b00e440ebba508b3f73d7b075e51b273bbbf82"),
    "labmate_ui_primitives.h": ("ac6b6b91dc32b512b11683810dd0c7d14a07d25d", "b61ca6e4fd8de5a7048b49588dac3bde166cc8cd"),
}
TESTS = {
    "test_labmate_scope_display.c": "8ab78cf8b8bbd41cd777f3ed30885d01d2a8cc48",
    "test_labmate_scope_pair_view.c": "b8bed84fcb5fef095b762f1a2af8474137851031",
    "test_scope_reference_view.c": "026a8114e924ec5c30422e7f2181a6a8957d3a79",
    "test_labmate_scope_focus.c": "7530cfee04c230eca3a705a346e8bd6d219b00c3",
    "test_labmate_ui_keylabels.c": "2d8083812cbc805ec7dfd685f3d8b55274e6c853",
}
STUB = "7a909b0a5f65469851a16976251380ffea5fa704"

def check(value: bool, message: str) -> None:
    if not value: raise RuntimeError(message)

def git_blob(file: Path) -> str:
    content = file.read_bytes()
    return hashlib.sha1(
        b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()

def sha256(file: Path) -> str:
    with file.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()

def git_head(dir: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(dir), "rev-parse", "HEAD"],
        text=True, stderr=subprocess.PIPE, timeout=30).strip()

def run(args, *, cwd: Path | None = None, env=None, seconds=180) -> None:
    argv = [str(a) for a in args]
    print("COMMAND:", " ".join(argv), flush=True)
    p = subprocess.run(argv, cwd=cwd, env=env, timeout=seconds)
    check(p.returncode == 0, f"command exit {p.returncode}; STOP, NO AUTO RETRY")

def extract_pinned(root: Path) -> Path:
    check(not root.exists(), "prior redesign build attempt found; preserve and review")
    root.mkdir(parents=True)
    package = root / "pinned_source.zip"
    endpoint = "repos/sehmusadsoy-ui/flipper-labmate/zipball/" + SOURCE
    print("PINNED_SOURCE:", SOURCE, flush=True)
    with package.open("xb") as target:
        code = subprocess.run(["gh", "api", endpoint],
                              stdout=target, timeout=180).returncode
        check(code == 0, "GitHub authenticated source retrieval failed")
    check(package.stat().st_size < 50_000_000 and is_zipfile(package),
          "invalid or oversized source archive")
    src = root / "source"
    src.mkdir()
    with ZipFile(package) as archive:
        entries = archive.infolist()
        check(entries and sum(i.file_size for i in entries) < 100_000_000,
              "invalid expanded archive size")
        roots = {i.filename.split("/")[0] for i in entries if i.filename}
        check(len(roots) == 1 and next(iter(roots)).startswith(
            "sehmusadsoy-ui-flipper-labmate-" + SOURCE[:7]),
            "source zip root differs from pinned commit")
        for info in entries:
            name = info.filename
            check("\\" not in name and not name.startswith("/") and
                  all(p not in ("", ".", "..") for p in name.rstrip("/").split("/")),
                  "zip-slip or malformed archive entry")
            check(not stat.S_ISLNK(info.external_attr >> 16),
                  "symlink in source archive")
            parts = name.rstrip("/").split("/")[1:]
            if not parts: continue
            dest = src.joinpath(*parts)
            if info.is_dir():
                dest.mkdir(parents=True, exist_ok=True)
            else:
                check(info.file_size < 20_000_000, "oversize source member")
                dest.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as inp, dest.open("xb") as output:
                    shutil.copyfileobj(inp, output)
    for name, (_, blob) in CHANGED.items():
        check(git_blob(src / "src" / name) == blob,
              "new UI Git object mismatch: " + name)
    for name, blob in TESTS.items():
        check(git_blob(src / "tests" / name) == blob,
              "pinned host regression mismatch: " + name)
    check(git_blob(src / "tests/host_stubs/gui/gui.h") == STUB,
          "pinned Canvas geometry stub mismatch")
    check(git_blob(src / "application.fam") == FAM, "manifest drift")
    check(git_blob(src / "scripts/verify_v19_e11_sdk_fap.py") == CHECKER,
          "E11 FAP verifier drift")
    print("PINNED_UI_SOURCE_AND_HOST_TEST_BLOBS: PASS", flush=True)
    return src

def check_host_tests(src: Path, root: Path) -> None:
    cc = Path(r"C:\msys64\ucrt64\bin\cc.exe")
    check(cc.is_file(), "MSYS2 UCRT64 C compiler missing")
    run([cc, "--version"])
    env = dict(os.environ)
    env["PATH"] = str(cc.parent) + os.pathsep + env.get("PATH", "")
    dest = root / "host_tests"
    dest.mkdir()
    matrix = (
        ("scope", ("tests/test_labmate_scope_display.c",
                   "src/labmate_scope_display.c", "src/labmate_scope_plot.c")),
        ("compare", ("tests/test_labmate_scope_pair_view.c",
                     "src/labmate_scope_pair_view.c", "src/labmate_scope_pair.c",
                     "src/labmate_scope_compare.c")),
        ("reference", ("tests/test_scope_reference_view.c",
                       "src/labmate_scope_reference_view.c",
                       "src/labmate_scope_tolerance.c", "src/labmate_scope_compare.c")),
        ("focus", ("tests/test_labmate_scope_focus.c",
                   "src/labmate_scope_plot.c")),
        ("keylabels", ("tests/test_labmate_ui_keylabels.c",
                       "src/labmate_ui_primitives.c")),
    )
    for title, sources in matrix:
        binary = dest / (title + ".exe")
        run([cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
             "-Itests/host_stubs", "-Isrc", *sources, "-o", binary],
            cwd=src, env=env, seconds=120)
        run([binary], cwd=src, env=env, seconds=30)
        print("HOST_" + title.upper() + ": PASS", flush=True)
    print("V19 SCOPE REDESIGN HOST REGRESSIONS: 5/5 PASS", flush=True)

def preflight_sdk(sdk: Path, original: Path) -> tuple[Path, Path]:
    check(sdk.is_dir() and original.is_dir(), "native SDK folders missing")
    check(git_head(sdk) == MOMENTUM and git_head(original) == MOMENTUM,
          "isolated or original Momentum firmware baseline drift")
    check((sdk / "fbt.cmd").is_file(), "isolated fbt.cmd missing")
    app = sdk / "applications_user/labmate"
    check(git_blob(app / "application.fam") == FAM, "SDK manifest mismatch")
    for name, (old, _) in CHANGED.items():
        current = app / "src" / name
        if old is None:
            check(not current.exists(), "new Scope header unexpectedly installed")
        else:
            check(current.is_file() and git_blob(current) == old,
                  "SDK app differs from previous UI polish: " + name)
    existing = sdk / "build/f7-firmware-C/.extapps/labmate.fap"
    check(existing.is_file() and existing.stat().st_size == OLD_FAP_SIZE and
          sha256(existing) == OLD_FAP_SHA,
          "current prior 99,376-byte FAP not exactly attested")
    # Do not erase or reconstruct firmware; existing patched SDK APIs
    # are verified again after native build by the repo's strict checker.
    print("PRIOR_99376_FAP_AND_E11_SDK_READONLY_GATE: PASS", flush=True)
    return app, existing

def backup_previous(fap: Path, directory: Path) -> Path:
    check(not directory.exists(), "previous immutable FAP PC backup already exists")
    directory.mkdir(parents=True)
    target = directory / "labmate-v19-99376-before-redesign.fap"
    with fap.open("rb") as inp, target.open("xb") as out:
        shutil.copyfileobj(inp, out)
        out.flush()
        os.fsync(out.fileno())
    check(target.stat().st_size == OLD_FAP_SIZE and
          sha256(target) == OLD_FAP_SHA,
          "prior FAP PC backup failed byte-identical readback")
    print("PRIOR_99376_FAP_PC_BACKUP: PASS", flush=True)
    return target

def main() -> None:
    check(os.name == "nt", "Windows only; no WSL")
    home = Path.home()
    sdk = home / "LabMate-v19-WinSDK-050ec62"
    original = home / "Momentum-Firmware"
    root = home / ("LabMate-v19-Redesign-" + SOURCE[:7])
    backupdir = home / "Documents/LabMate-FAP-PC-Backups" / (
        "V19-SCOPE-REDESIGN-PREBUILD-" + SOURCE[:7])
    check(not root.exists() and not backupdir.exists(),
          "previous build state already present; STOP, do not retry")
    app, fap = preflight_sdk(sdk, original)
    source = extract_pinned(root)
    check_host_tests(source, root)
    backupfile = backup_previous(fap, backupdir)
    for name, (_, blob) in CHANGED.items():
        frm = source / "src" / name
        into = app / "src" / name
        check(git_blob(frm) == blob, "source changed before SDK copy")
        if into.exists():
            shutil.copyfile(frm, into)
        else:
            with frm.open("rb") as a, into.open("xb") as b:
                shutil.copyfileobj(a, b)
        check(git_blob(into) == blob, "SDK copy/readback mismatch: " + name)
    print("SCOPE_UI_SOURCE_SYNC: 10/10 PASS", flush=True)
    environment = dict(os.environ)
    for key in ("FBT_ROOT", "FBT_NOENV", "FBT_TOOLCHAIN_PATH", "FBT_TOOLCHAIN_ROOT"):
        environment.pop(key, None)
    environment["GIT_PAGER"] = "cat"
    run(["cmd.exe", "/d", "/c", "fbt.cmd", "fap_labmate"],
        cwd=sdk, env=environment, seconds=1500)
    check(fap.is_file() and 80_000 <= fap.stat().st_size <= 250_000 and
          sha256(fap) != OLD_FAP_SHA, "new FAP missing or outside bounded size")
    run([sys.executable, source / "scripts/verify_v19_e11_sdk_fap.py", sdk, fap],
        seconds=120)
    print("V19 SCOPE REDESIGN WINDOWS FAP BUILD ONLY PASS", flush=True)
    print("GITHUB_UI_SOURCE_COMMIT:", SOURCE)
    print("FAP_PATH:", fap)
    print("FAP_SIZE:", fap.stat().st_size)
    print("FAP_SHA256:", sha256(fap))
    print("PREVIOUS_FAP_PC_BACKUP:", backupfile)
    print("DEVICE_WRITES: ZERO | FIRMWARE_FLASH: NO | AUTO_INSTALL: NO")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("V19 SCOPE REDESIGN BUILD NO-GO:", exc, file=sys.stderr)
        print("No retry or Flipper install; preserve PC state for review.",
              file=sys.stderr)
        raise SystemExit(1)
