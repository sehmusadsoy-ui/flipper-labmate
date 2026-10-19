#!/usr/bin/env python3
"""Windows PowerShell helper: pinned E11 v1.9 FAP build ONLY (no USB/flash).
Creates a separate Windows SDK worktree; leaves the existing SDK files and
working Flipper app intact. Mirrors 114 vetted CI patch/test commands.
"""
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from zipfile import ZipFile, is_zipfile

SOURCE = "050ec62fe372422056e0e903cde6c5e6f54f10f2"
E11_BASE = "d3f89dfe2ef6b01839201598e9be1590cba80322"
BLOBS = {
    "src/labmate_scope_plot.c": "4175452c669256be4da72740daabea680bc4f1d8",
    "src/labmate_scope_plot.h": "f4772278c18a8a3bc4aaa17554f5e1eb63d8b5b5",
    "src/labmate_scope_display.c": "5ef5665a39540d3d7ee99c5fa9b3c8ec77ff1d5e",
    "src/labmate_scope_bridge.c": "9c6fc49628e193ca5a0ca2f84fb4b22a74d53102",
    "tests/test_labmate_scope_focus.c": "7530cfee04c230eca3a705a346e8bd6d219b00c3",
    "scripts/verify_v19_e11_sdk_fap.py": "841eb5f982e5c2e951cc98278060eedac078941b",
    ".github/workflows/build-v19-e11-fap-review-only.yml":
        "4bf19d01a3960516e0b4c55052473434ad8af307",
}
PATCH_RE = re.compile(
    r"python3 labmate/(?:scripts|tests)/[a-z0-9_]+\.py"
    r"(?: momentum-src)?(?: labmate)?(?: --[a-z0-9-]+)*"
)

def need(value, message):
    if not value:
        raise RuntimeError(message)

def command(args, cwd=None, env=None):
    print("COMMAND:", " ".join(str(x) for x in args), flush=True)
    result = subprocess.run([str(x) for x in args], cwd=cwd, env=env)
    need(result.returncode == 0, f"exit {result.returncode} from {args[0]}")

def git(*args):
    return subprocess.check_output(["git", *map(str, args)], text=True).strip()

def gitblob(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def main():
    need(os.name == "nt", "Windows PowerShell required (no WSL)")
    need(sys.version_info >= (3, 11), "Python 3.11+ required")
    home = Path.home()
    old_sdk = home / "Momentum-Firmware"
    src_area = home / ("LabMate-v19-WinSource-" + SOURCE[:7])
    sdk = home / ("LabMate-v19-WinSDK-" + SOURCE[:7])
    need((old_sdk / "fbt.cmd").is_file(), "existing Windows Momentum fbt.cmd missing")
    need(git("-C", old_sdk, "rev-parse", "HEAD") == E11_BASE,
         "Windows Momentum base is NOT the pinned E11 SDK")
    need(not sdk.exists(), "isolated SDK worktree already exists; do not overwrite")
    # A failed codeload attempt from the earlier Windows helper created an
    # EMPTY source directory before receiving HTTP 404. Reuse only if empty.
    if src_area.exists():
        need(src_area.is_dir() and not any(src_area.iterdir()),
             "source directory has existing data; refuse overwrite")
    else:
        src_area.mkdir()
    archive = src_area / "source.zip"
    endpoint = ("repos/sehmusadsoy-ui/flipper-labmate/zipball/" + SOURCE)
    print("AUTHENTICATED GH API PINNED ARCHIVE:", endpoint, flush=True)
    # gh api follows GitHub's authenticated zipball redirect. stdout must be
    # byte-for-byte binary; never pass this stream through PowerShell text
    # redirection or git HTTPS credential prompts.
    with archive.open("wb") as stream:
        status = subprocess.run(["gh", "api", endpoint], stdout=stream).returncode
    need(status == 0, "GitHub CLI archive download failed")
    need(archive.is_file() and archive.stat().st_size > 100,
         "empty or invalid GitHub archive")
    need(archive.stat().st_size <= 50_000_000,
         "GitHub source archive exceeds 50 MB safety limit")
    need(is_zipfile(archive), "GitHub CLI returned data that is not ZIP")
    with ZipFile(archive) as z:
        names = z.namelist()
        need(all(not n.startswith("/") and ".." not in n.split("/") and
                 "\\" not in n for n in names), "unsafe ZIP path")
        roots = {n.split("/", 1)[0] for n in names}
        need(len(roots) == 1, "unexpected source archive root")
        z.extractall(src_area)
    src = src_area / next(iter(roots))
    for name, digest in BLOBS.items():
        path = src / name
        need(path.is_file() and gitblob(path) == digest,
             "source Git blob mismatch: " + name)
    workflow = (src / ".github/workflows/build-v19-e11-fap-review-only.yml").read_text()
    start = "      - name: Reapply the previously audited E11 patch chain (SOURCE ONLY)"
    stop = "      - name: Stage v1.9DEV into native FAP source (no install)"
    need(workflow.count(start) == 1 and workflow.count(stop) == 1,
         "missing pinned CI patch-chain section")
    section = workflow.split(start, 1)[1].split(stop, 1)[0]
    steps = []
    for raw in section.splitlines():
        line = raw.strip()
        if line.startswith("python3 "):
            need(PATCH_RE.fullmatch(line), "unrecognized CI patch/test step: " + line)
            steps.append(line.split())
    need(len(steps) == 114, f"E11 CI patch list count mismatch: {len(steps)}")
    need(steps[0][1].endswith("patch_momentum_i2c_timeout.py") and
         steps[-1][1].endswith("check_v18_native_legacy_tim2_contract.py"),
         "E11 CI patch boundaries do not match")
    print(f"GITHUB EXACT FILE HASHES: {len(BLOBS)}/{len(BLOBS)} PASS; CI STEPS: 114")
    command(["git", "-C", old_sdk, "worktree", "add", "--detach", sdk, E11_BASE])
    need(git("-C", sdk, "rev-parse", "HEAD") == E11_BASE, "isolated SDK base mismatch")
    need(not git("-C", sdk, "status", "--porcelain"),
         "new isolated SDK unexpectedly dirty")
    for i, parts in enumerate(steps, 1):
        script = src / parts[1].replace("labmate/", "", 1)
        need(script.is_file(), "missing CI test/patch: " + parts[1])
        args = [str(sdk) if a == "momentum-src" else
                str(src) if a == "labmate" else a for a in parts[2:]]
        print(f"E11 SOURCE PATCH/TEST {i}/114", flush=True)
        command([sys.executable, script, *args])
    command(["git", "-C", sdk, "diff", "--check"])
    target = sdk / "applications_user/labmate"
    target_src = target / "src"
    target_src.mkdir(parents=True, exist_ok=True)
    for name in ("application.fam", "labmate_10px.png"):
        shutil.copyfile(src / name, target / name)
    for suffix in ("*.c", "*.h"):
        for f in (src / "src").glob(suffix):
            shutil.copyfile(f, target_src / f.name)
    for name in ("labmate_scope_plot.c", "labmate_scope_display.c",
                 "labmate_scope_bridge.c"):
        need((src / "src" / name).read_bytes() == (target_src / name).read_bytes(),
             "staged source mismatch: " + name)
    need('fap_version="1.9"' in (target / "application.fam").read_text(),
         "bad FAP version")
    need('#define LABMATE_VERSION_TEXT "v1.9DEV"' in
         (target_src / "labmate_internal.h").read_text(), "bad app version")
    env = dict(os.environ)
    for key in ("FBT_ROOT", "FBT_NOENV", "FBT_TOOLCHAIN_PATH", "FBT_TOOLCHAIN_ROOT"):
        env.pop(key, None)
    print("FAP ONLY: cmd.exe /d /c fbt.cmd fap_labmate", flush=True)
    command(["cmd.exe", "/d", "/c", "fbt.cmd", "fap_labmate"], cwd=sdk, env=env)
    fap = sdk / "build/f7-firmware-C/.extapps/labmate.fap"
    need(fap.is_file(), "linked FAP missing")
    command([sys.executable, src / "scripts/verify_v19_e11_sdk_fap.py", sdk, fap])
    print("V19 WINDOWS FAP BUILD ONLY PASS")
    print("SOURCE_COMMIT:", SOURCE)
    print("FAP_PATH:", fap)
    print("FAP_SHA256:", hashlib.sha256(fap.read_bytes()).hexdigest())
    print("DEVICE_WRITES: ZERO | FIRMWARE_FLASH: NO | AUTO_INSTALL: NO")
    print("STOP: use separate explicit backup-safe Flipper install approval")

if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print("V19 WINDOWS BUILD NO-GO:", err, file=sys.stderr)
        print("No Flipper USB/flash/install was attempted; do NOT use any "
              "partial/unverified FAP.", file=sys.stderr)
        sys.exit(1)
