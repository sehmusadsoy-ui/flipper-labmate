#!/usr/bin/env python3
"""Resume the same isolated Windows E11 FAP build at audited step 61.

Never alters the user's original Momentum SDK or installed Flipper app.
Only accepts the exact pinned source and audited 60-step patch state.
Does NOT silently skip C host tests or perform USB, COM, flash or install.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SOURCE = "050ec62fe372422056e0e903cde6c5e6f54f10f2"
E11_BASE = "d3f89dfe2ef6b01839201598e9be1590cba80322"
CHECKS = {
    "src/labmate_scope_plot.c": "4175452c669256be4da72740daabea680bc4f1d8",
    "src/labmate_scope_plot.h": "f4772278c18a8a3bc4aaa17554f5e1eb63d8b5b5",
    "src/labmate_scope_display.c": "5ef5665a39540d3d7ee99c5fa9b3c8ec77ff1d5e",
    "src/labmate_scope_bridge.c": "9c6fc49628e193ca5a0ca2f84fb4b22a74d53102",
    "tests/test_labmate_scope_focus.c": "7530cfee04c230eca3a705a346e8bd6d219b00c3",
    "scripts/verify_v19_e11_sdk_fap.py": "841eb5f982e5c2e951cc98278060eedac078941b",
    ".github/workflows/build-v19-e11-fap-review-only.yml":
        "4bf19d01a3960516e0b4c55052473434ad8af307",
}
# Keep the original 050ec62 source immutable: the 61st test's second
# native host executable needs a separate name on Windows to avoid ld.exe
# being denied when overwriting a just-executed PE file.
RFID_TEST = "tests/test_v18_native_rfid_field_owner.py"
RFID_OLD_BLOB = "a9d0f292531bcf793dfea2037a5c9f6dd0faf887"
RFID_NEW_BLOB = "135e0a008be81a09bc71948440b6589c71807648"
RFID_ANCHOR = 'str(d/"lease.c"),"-o",str(exe)],check=True)\n        subprocess.run([str(exe)],check=True)'
RFID_REPLACEMENT = 'str(d/"lease.c"),"-o",str(d/"allocator_test")],check=True)\n        subprocess.run([str(d/"allocator_test")],check=True)'
SYMBOLS = {
    "furi_hal_resource_lease_try_acquire",
    "furi_hal_resource_lease_release",
    "furi_hal_gpio_try_add_int_callback",
}

def must(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)

def run(args, cwd=None, env=None) -> None:
    print("COMMAND:", " ".join(map(str, args)), flush=True)
    rc = subprocess.run(list(map(str, args)), cwd=cwd, env=env).returncode
    must(rc == 0, f"exit {rc}; cannot proceed")

def output(args) -> str:
    return subprocess.check_output(list(map(str, args)), text=True).strip()

def gitblob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def compiler_path() -> Path:
    # The ARM cross-compiler cannot run x86_64 host tests.
    roots = [Path(r) for r in (
        r"C:\msys64\ucrt64\bin",
        r"C:\msys64\mingw64\bin",
        r"C:\msys64\clang64\bin",
        r"C:\msys64\mingw32\bin",
    )]
    found = shutil.which("cc")
    if found:
        candidate = Path(found).resolve()
        must(candidate.suffix.lower() == ".exe", f"cc is not a native .exe: {candidate}")
        return candidate
    for root in roots:
        candidate = root / "cc.exe"
        if candidate.is_file():
            return candidate.resolve()
    raise RuntimeError(
        "Windows native x86_64 C compiler 'cc.exe' missing. "
        "No tests skipped. Install a native GCC toolchain (e.g., "
        "MSYS2 UCRT64 mingw-w64-ucrt-x86_64-gcc), then retry. "
        "Do NOT use arm-none-eabi-gcc to execute host tests."
    )

def main() -> None:
    must(os.name == "nt", "Only native Windows PowerShell is supported")
    must(sys.version_info >= (3, 11), "Python >= 3.11 required")
    home = Path.home()
    original = home / "Momentum-Firmware"
    sdk = home / ("LabMate-v19-WinSDK-" + SOURCE[:7])
    source_area = home / ("LabMate-v19-WinSource-" + SOURCE[:7])
    src = source_area / ("sehmusadsoy-ui-flipper-labmate-" + SOURCE[:7])
    must(original.is_dir() and sdk.is_dir() and src.is_dir(),
         "The exact previous six-step Windows build folders are missing")
    must(output(["git", "-C", original, "rev-parse", "HEAD"]) == E11_BASE,
         "Original Momentum base changed")
    must(output(["git", "-C", sdk, "rev-parse", "HEAD"]) == E11_BASE,
         "Isolated Momentum base changed")
    for name, sha in CHECKS.items():
        file = src / name
        must(file.is_file() and gitblob(file) == sha, "Source Git blob mismatch: " + name)
    tracked = output(["git", "-C", sdk, "diff", "--name-only", "HEAD"])
    dirty = {line.replace("\\", "/") for line in tracked.splitlines() if line}
    # The exact expected tracked-file inventory comes from the pinned E11
    # stage-60 precondition, rather than an ad hoc hardcoded approximation.
    sys.path.insert(0, str(src / "scripts"))
    from patch_momentum_native_rfid_field_owner import (
        EXPECTED as BEFORE_FIELD, H, R, RFID, RFID_H, API, MARK
    )
    expected_dirty = set(BEFORE_FIELD) | {H, R, RFID, RFID_H, API}
    must(dirty == expected_dirty,
         "E11 step-60 tracked source fingerprint mismatch; "
         f"missing={sorted(expected_dirty-dirty)} extra={sorted(dirty-expected_dirty)}")
    must(MARK in (sdk / RFID).read_text(encoding="utf-8"),
         "E11 stage-60 RFID field source patch missing")
    must("FURI_HAL_LEASE_NATIVE_RFID_FIELD" in
         (sdk / H).read_text(encoding="utf-8"),
         "E11 stage-60 resource mask missing")
    must("Function,+,furi_hal_rfid_field_detect_try_start,_Bool," in
         (sdk / API).read_text(encoding="utf-8"),
         "E11 stage-60 firmware API export missing")
    untracked = output(["git", "-C", sdk, "ls-files", "--others", "--exclude-standard"])
    must(not untracked, "Unexpected untracked SDK files; stop")
    api = (sdk / "targets/f7/api_symbols.csv").read_text(encoding="utf-8")
    for name in SYMBOLS:
        must(f"Function,+,{name}," in api, "Missing patched API " + name)
    resource = (sdk / "targets/f7/furi_hal/furi_hal_resources.h").read_text()
    gpio = (sdk / "targets/f7/furi_hal/furi_hal_gpio.h").read_text()
    pwm = (sdk / "targets/f7/furi_hal/furi_hal_pwm.c").read_text()
    must("#define FURI_HAL_RESOURCE_LEASE_API_V1 1" in resource
         and "#define FURI_HAL_PWM_NATIVE_LEASE_API_V1 1" in resource
         and "#define FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK 1" in gpio
         and "/* LabMate E11 native PWM lease owner:" in pwm,
         "E11 patch markers incomplete")
    run(["git", "-C", sdk, "diff", "--check"])
    # Fail early if no executable host compiler, without touching worktree.
    cc = compiler_path()
    print("HOST C COMPILER:", cc, flush=True)
    run([cc, "--version"])
    ccbin = str(cc.parent)
    env = dict(os.environ)
    env["PATH"] = ccbin + os.pathsep + env.get("PATH", "")
    # This prevents e.g. arm-gcc in the firmware path from impersonating cc.
    must(shutil.which("cc", path=env["PATH"]) is not None,
         "cc not discoverable under native Windows PATH")
    workflow = (src / ".github/workflows/build-v19-e11-fap-review-only.yml").read_text()
    begin = "      - name: Reapply the previously audited E11 patch chain (SOURCE ONLY)"
    end = "      - name: Stage v1.9DEV into native FAP source (no install)"
    must(workflow.count(begin) == 1 and workflow.count(end) == 1,
         "Pinned E11 workflow markers mismatch")
    section = workflow.split(begin, 1)[1].split(end, 1)[0]
    commands = [line.strip().split() for line in section.splitlines()
                if line.strip().startswith("python3 ")]
    must(len(commands) == 114 and
         commands[60][1] == "labmate/tests/test_v18_native_rfid_field_owner.py",
         "Pinned E11 114-step chain mismatch")
    print("WIN E11 PREVIOUS STEPS 1..60: VERIFIED FROM PATCH STATE / USER LOG")
    print("RESTART FROM 61/114; NO ORIGINAL SDK MODIFICATIONS", flush=True)
    for index in range(60, len(commands)):
        parts = commands[index]
        must(parts[0] == "python3" and
             parts[1].startswith(("labmate/scripts/", "labmate/tests/")) and
             parts[1].endswith(".py"), f"Unexpected chain step {index+1}")
        script = src / parts[1].removeprefix("labmate/")
        must(script.is_file(), f"Missing source script: {script}")
        args = [str(sdk) if a == "momentum-src" else
                str(src) if a == "labmate" else a for a in parts[2:]]
        print(f"E11 SOURCE PATCH/TEST {index+1}/114", flush=True)
        if index == 60:
            # Both identical native C cases passed in the user's log.
            # Only the third host executable is moved to a distinct file;
            # all original test input code and assertions remain unchanged.
            must(gitblob(script) == RFID_OLD_BLOB,
                 "RFID host test source not the pinned original")
            text = script.read_text(encoding="utf-8")
            must(text.count(RFID_ANCHOR) == 1, "RFID test patch anchor mismatch")
            patched = text.replace(RFID_ANCHOR, RFID_REPLACEMENT, 1)
            raw = patched.encode("utf-8")
            replacement_sha = hashlib.sha1(
                b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            must(replacement_sha == RFID_NEW_BLOB,
                 "RFID Windows host test patch differs from approved GitHub blob")
            with tempfile.TemporaryDirectory(prefix="labmate_e11_rfid_win_overlay_") as tmp:
                overlay = Path(tmp) / "test_v18_native_rfid_field_owner.py"
                overlay.write_bytes(raw)
                print("WIN RFID TEST: same C assertions, distinct allocator.exe", flush=True)
                run([sys.executable, overlay, *args], env=env)
        else:
            run([sys.executable, script, *args], env=env)
    run(["git", "-C", sdk, "diff", "--check"])
    target = sdk / "applications_user/labmate"
    must(not target.exists(), "Existing target app path; refuse unreviewed overwrite")
    target.mkdir(parents=True)
    (target / "src").mkdir()
    for n in ("application.fam", "labmate_10px.png"):
        shutil.copyfile(src / n, target / n)
    for pat in ("*.c", "*.h"):
        for f in (src / "src").glob(pat):
            shutil.copyfile(f, target / "src" / f.name)
    must('fap_version="1.9"' in (target / "application.fam").read_text(),
         "Wrong FAP version")
    must('#define LABMATE_VERSION_TEXT "v1.9DEV"' in
         (target / "src/labmate_internal.h").read_text(),
         "Wrong LabMate version")
    for key in ("FBT_ROOT", "FBT_NOENV", "FBT_TOOLCHAIN_PATH", "FBT_TOOLCHAIN_ROOT"):
        env.pop(key, None)
    print("WINDOWS NATIVE FAP BUILD ONLY", flush=True)
    run(["cmd.exe", "/d", "/c", "fbt.cmd", "fap_labmate"], cwd=sdk, env=env)
    fap = sdk / "build/f7-firmware-C/.extapps/labmate.fap"
    must(fap.is_file(), "FAP output not produced")
    run([sys.executable, src / "scripts/verify_v19_e11_sdk_fap.py", sdk, fap])
    print("V19 WINDOWS FAP BUILD ONLY PASS")
    print("SOURCE_COMMIT:", SOURCE)
    print("FAP_PATH:", fap)
    print("FAP_SHA256:", hashlib.sha256(fap.read_bytes()).hexdigest())
    print("USB/DEVICE_WRITES: ZERO | FIRMWARE_FLASH: NO | AUTO_INSTALL: NO")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("V19 WINDOWS RESUME NO-GO:", exc, file=sys.stderr)
        print("No Flipper install or firmware flash; do not use any "
              "unverified candidate.", file=sys.stderr)
        raise SystemExit(1)
