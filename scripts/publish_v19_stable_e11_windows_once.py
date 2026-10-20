#!/usr/bin/env python3
"""Publish LabMate v1.9 as compatibility-limited E11-only Stable via GitHub CLI.

RUN ONLY on the release operator's native Windows PC after their explicit
publishing decision. Never connects to Flipper, overwrites main or v1.8,
flashes firmware, migrates data, merges PRs or changes GitHub Actions.
Fail-closed and NON-RETRYABLE: a failure after 'gh release create' leaves
an unpublished draft for deliberate inspection, never auto-deletes assets.
Requires authenticated 'gh' release permissions and the exact verified
101468-byte FAP present in the pre-existing isolated E11 build directory.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPO = "sehmusadsoy-ui/flipper-labmate"
API = "repos/" + REPO
TAG = "v1.9"
SOURCE = "72eb58d6c65d31f510acf6f532ee23c543a9149d"
NOTES_REF = "6fae0bf75715a99ba9227d25c2766568b1d230ef"
NOTES_FILE = "docs/V1_9_STABLE_E11_RELEASE_NOTES.md"
NOTES_GIT_BLOB = "e97f1f797b245bddd1ea8206ae466933549531d1"
FAP_NAME = "labmate.fap"
FAP_SIZE = 101468
FAP_SHA = "d8bb04cf6de6ebaa466e7487e619d9f68af21dac49df2aa51e91dfae1f9f55c2"
PREVIOUS_SIZE = 99376
PREVIOUS_SHA = "0f0b246d042c45eabe2c29dab692dbc7df20817c419c011ca31a313d4b62141a"
MAIN_APP_FAM_BLOB = "951734bbc8b498cca9f099590363ee4c46f7488b"
V18_STABLE_TAG_SHA = "02b05639364d6dd71f5eb70456eca379c59218cb"
E11_RELEASE_TAG_SHA = "99cb65d0194dc59d423cfa439c90618ac6b9f114"
TITLE = "LabMate v1.9 Stable — Logic Scope (E11 Custom Momentum ONLY)"
SUMS = FAP_SHA + "  labmate.fap\n"
FIRST_READ = """# READ ME FIRST: LabMate v1.9 is E11-CUSTOM-FIRMWARE-ONLY

This FAP has been tested only on a Flipper Zero running a matching, patched
Momentum E11 native resource-lease and GPIO callback ABI.

DO NOT install it on ordinary Momentum, official Flipper firmware,
Unleashed/Xtreme or unknown firmware. An app file does not install or repair
the needed native E11 firmware interfaces. Do not attempt any firmware update
or SD Manifest clean-up as an automatic prerequisite.

For ordinary Momentum use the existing v1.8 Stable:
https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8

The earlier E11 custom release contains expert-only firmware review materials:
https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8-e11-custom-momentum
Those firmware updater assets are NOT certified one-click upgrades.

Firmware/ABI must be verified before FAP install. Preserve your installed
FAP, previous v1.8/E11 backups, microSD CSV files and Profiles.
Only 3.3V logic inputs on PC1. One digital channel; not an analog scope,
not a calibrated timebase and no high-speed/multi-channel performance claim.

RELEASE TAG: v1.9
APP FAP BYTES: 101468
APP FAP SHA256: d8bb04cf6de6ebaa466e7487e619d9f68af21dac49df2aa51e91dfae1f9f55c2
TESTED APP SOURCE: 72eb58d6c65d31f510acf6f532ee23c543a9149d
No firmware flash / on-device writes occur during publication.
"""

def require(condition: bool, problem: str) -> None:
    if not condition:
        raise RuntimeError(problem)

def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def blob(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()

def checked_file(path: Path, size: int, sha: str, label: str) -> None:
    require(not path.is_symlink() and path.is_file(), label + ": missing or link")
    require(path.stat().st_size == size, label + ": size mismatch")
    require(digest(path) == sha, label + ": SHA256 mismatch")

def command(args, *, capture: bool = False, timeout: int = 180):
    argv = [str(i) for i in args]
    print("COMMAND:", " ".join(argv), flush=True)
    p = subprocess.run(argv, capture_output=capture, timeout=timeout,
                       text=capture, encoding="utf-8" if capture else None)
    if p.returncode:
        if capture and p.stderr:
            print(p.stderr[-1600:], file=sys.stderr)
        raise RuntimeError("command failed (status " + str(p.returncode) +
                           "); stop; do not retry or clobber")
    return p.stdout if capture else ""

def api_json(resource: str) -> dict:
    response = command(["gh", "api", resource], capture=True)
    result = json.loads(response)
    require(isinstance(result, dict), "GitHub response was not an object: " + resource)
    return result

def expect_absent(resource: str) -> None:
    p = subprocess.run(["gh", "api", resource],
                       capture_output=True, text=True, timeout=45)
    if p.returncode == 0:
        raise RuntimeError("v1.9 already exists at " + resource +
                           "; preserve it, do not overwrite")
    require("HTTP 404" in p.stderr or "404 Not Found" in p.stderr,
            "GitHub API missing-resource response was not a definite HTTP 404: " +
            resource + " (" + p.stderr[-180:] + ")")

def attested_notes() -> bytes:
    item = api_json(API + "/contents/" + NOTES_FILE + "?ref=" + NOTES_REF)
    require(item.get("sha") == NOTES_GIT_BLOB, "pinned release-note Git blob changed")
    raw = base64.b64decode("".join(str(item["content"]).split()), validate=True)
    require(blob(raw) == NOTES_GIT_BLOB, "release-note byte-level Git hash mismatch")
    text = raw.decode("utf-8")
    for needle in (SOURCE, FAP_SHA, "E11", "256-edge", "ordinary/stock Momentum",
                   "No multi-channel acquisition or high-speed"):
        require(needle in text, "release note is missing compatibility/performance caveat: " +
                needle)
    return raw

def remote_fap_and_assets(release: dict, package: Path, verify: Path) -> None:
    require(release.get("tag_name") == TAG, "remote release tag mismatch")
    require(not release.get("prerelease"), "E11-limited v1.9 must be Stable, not prerelease")
    require(release.get("target_commitish") == SOURCE, "release target commit drift")
    body = str(release.get("body", ""))
    require(SOURCE in body and FAP_SHA in body and
            "E11-patched Momentum firmware ONLY" in body,
            "release description lacks pinned provenance or E11 warning")
    assets = release.get("assets")
    require(isinstance(assets, list) and
            {item.get("name") for item in assets} ==
            {"labmate.fap", "SHA256SUMS.txt", "READ_ME_FIRST-E11.md"},
            "release assets contain unexpected/missing entries")
    for asset in assets:
        name = asset["name"]
        local = package / name
        require(int(asset["size"]) == local.stat().st_size,
                "uploaded asset size drift: " + name)
        check_remote = asset.get("digest")
        if check_remote:
            require(check_remote == "sha256:" + digest(local),
                    "server asset digest drift: " + name)
    # Independently download ALL candidate assets from the unpublished DRAFT
    # using the GitHub CLI and compare full bytes. Failure leaves it draft.
    require(not verify.exists(), "verification directory already exists")
    verify.mkdir()
    command(["gh", "release", "download", TAG, "-R", REPO,
             "--dir", verify, "--pattern", "labmate.fap",
             "--pattern", "SHA256SUMS.txt",
             "--pattern", "READ_ME_FIRST-E11.md"], timeout=300)
    for name in ("labmate.fap", "SHA256SUMS.txt", "READ_ME_FIRST-E11.md"):
        local = package / name
        remote = verify / name
        require(remote.is_file() and remote.read_bytes() == local.read_bytes(),
                "remote independent byte readback mismatch: " + name)
    checked_file(verify / FAP_NAME, FAP_SIZE, FAP_SHA, "downloaded release FAP")
    print("DRAFT_REMOTE_ASSET_3_OF_3_FULL_READBACK: PASS", flush=True)

def main() -> None:
    require(os.name == "nt", "native Windows only; no WSL")
    require(sys.argv[1:] == ["--publish-stable-e11"],
            "explicit --publish-stable-e11 argument required")
    require(shutil.which("gh") is not None, "GitHub CLI not found")
    home = Path.home()
    fap = home / r"LabMate-v19-WinSDK-050ec62\build\f7-firmware-C\.extapps\labmate.fap"
    previous = home / (
        r"Documents\LabMate-FAP-PC-Backups"
        r"\V19-SCOPE-REDESIGN-PREBUILD-72eb58d"
        r"\labmate-v19-99376-before-redesign.fap"
    )
    package = home / ("Documents/LabMate-Releases/v1.9-STABLE-E11-" + SOURCE[:7])
    require(not package.exists(), "previous release package exists: inspect before retry")
    require(package.parent.is_dir(), "create Documents/LabMate-Releases manually first")
    checked_file(fap, FAP_SIZE, FAP_SHA, "PINNED_WINDOWS_NATIVE_FAP")
    checked_file(previous, PREVIOUS_SIZE, PREVIOUS_SHA, "PRESERVED_PREVIOUS_PC_FAP")
    print("OLD_AND_NEW_FAP_PC_SHA256_CHECKS: PASS", flush=True)

    repo = api_json(API)
    require(repo.get("full_name") == REPO and
            repo.get("default_branch") == "main",
            "GitHub repository/default branch changed")
    gh_args = command(["gh", "release", "create", "--help"], capture=True)
    edit_args = command(["gh", "release", "edit", "--help"], capture=True)
    require("--latest" in gh_args and "--target" in gh_args and
            "--latest" in edit_args and "--draft" in edit_args,
            "GitHub CLI version lacks required draft/latest protection flags")
    assert source_commit_is_real(api_json(API + "/git/commits/" + SOURCE))
    main_fam = api_json(API + "/contents/application.fam?ref=main")
    require(main_fam.get("sha") == MAIN_APP_FAM_BLOB,
            "ordinary main v1.8 has changed: stop")
    v18 = api_json(API + "/git/ref/tags/v1.8")
    custom = api_json(API + "/git/ref/tags/v1.8-e11-custom-momentum")
    require(v18.get("object", {}).get("sha") == V18_STABLE_TAG_SHA and
            custom.get("object", {}).get("sha") == E11_RELEASE_TAG_SHA,
            "existing ordinary/E11 release tag drift")
    latest = api_json(API + "/releases/latest")
    require(latest.get("tag_name") == "v1.8",
            "existing ordinary Stable Latest has changed")
    expect_absent(API + "/git/ref/tags/" + TAG)
    expect_absent(API + "/releases/tags/" + TAG)
    print("PRIOR_STABLE_TAGS_AND_MAIN: PASS", flush=True)

    raw_notes = attested_notes()
    package.mkdir(parents=True)
    clean_fap = package / FAP_NAME
    with fap.open("rb") as inp, clean_fap.open("xb") as out:
        shutil.copyfileobj(inp, out)
        out.flush()
        os.fsync(out.fileno())
    checked_file(clean_fap, FAP_SIZE, FAP_SHA, "RELEASE_PACKAGE_FAP")
    notes = package / "RELEASE_NOTES.md"
    notes.write_bytes(raw_notes)
    sums = package / "SHA256SUMS.txt"
    sums.write_text(SUMS, encoding="ascii", newline="\n")
    readme = package / "READ_ME_FIRST-E11.md"
    readme.write_text(FIRST_READ, encoding="utf-8", newline="\n")
    require(sums.read_text("ascii") == SUMS, "SHA256SUMS disk readback failed")
    require(readme.read_text("utf-8") == FIRST_READ, "E11 warning disk readback failed")
    print("LOCAL_STABLE_E11_RELEASE_PACKAGE: PASS", flush=True)

    # The explicit user-authorized publication begins here.
    # gh release create makes a new tag from the EXACT tested source commit.
    # It remains a PRIVATE-TO-RELEASE-VIEWERS DRAFT until remote readback PASS.
    command(["gh", "release", "create", TAG,
             clean_fap, sums, readme,
             "--repo", REPO,
             "--target", SOURCE,
             "--title", TITLE,
             "--notes-file", notes,
             "--draft",
             "--latest=false"], timeout=300)
    tag = api_json(API + "/git/ref/tags/" + TAG)
    require(tag.get("object", {}).get("type") == "commit" and
            tag["object"]["sha"] == SOURCE,
            "created v1.9 tag does not point to exact tested source; STOP")
    draft = api_json(API + "/releases/tags/" + TAG)
    require(bool(draft.get("draft")), "new release was not draft before verification")
    with tempfile.TemporaryDirectory(prefix="labmate-release-verify-") as temp:
        remote_fap_and_assets(draft, package, Path(temp) / "download")
    print("PINNED_TAG_AND_DRAFT_REMOTE_FAP: PASS", flush=True)
    # Only AFTER independent full remote byte validation publish as Stable.
    # --latest=false preserves ordinary v1.8 as the normal default download.
    command(["gh", "release", "edit", TAG, "--repo", REPO,
             "--draft=false", "--latest=false"], timeout=120)
    published = api_json(API + "/releases/tags/" + TAG)
    require(not published.get("draft") and not published.get("prerelease") and
            bool(published.get("published_at")),
            "v1.9 was not confirmed as an E11-only Stable release")
    require(api_json(API + "/git/ref/tags/" + TAG)["object"]["sha"] == SOURCE,
            "source tag moved after publication")
    check_latest = api_json(API + "/releases/latest")
    require(check_latest.get("tag_name") == "v1.8",
            "ordinary v1.8 Latest changed unexpectedly; needs manual review")
    result = {
        "tag": TAG,
        "release_url": published.get("html_url"),
        "public": True,
        "prerelease": False,
        "only_compatible_with": "exact matched custom Momentum E11 firmware",
        "ordinary_latest_still": "v1.8",
        "source_commit": SOURCE,
        "fap_bytes": FAP_SIZE,
        "fap_sha256": FAP_SHA,
        "device_writes": 0,
        "firmware_flash": False,
    }
    receipt = package / "PUBLISHED_E11_STABLE_RECEIPT.json"
    with receipt.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print("LABMATE_V19_E11_COMPATIBLE_STABLE_RELEASE: PASS")
    print("RELEASE_URL:", result["release_url"])
    print("RELEASE_FAP_SHA256:", FAP_SHA)
    print("ORDINARY_MOMENTUM_LATEST: v1.8 UNCHANGED")
    print("DEVICE_WRITES: ZERO | FIRMWARE_FLASH: NO")

def source_commit_is_real(item: dict) -> bool:
    require(bool(item.get("tree")) and item.get("author") is not None,
            "tested FAP source commit cannot be authenticated on GitHub")
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("V19 STABLE E11 PUBLICATION NO-GO:", str(error), file=sys.stderr)
        print("STOP. If a draft/tag was created, preserve it for manual review.",
              file=sys.stderr)
        print("No automatic retry, overwrite, main-branch change or Flipper write.",
              file=sys.stderr)
        raise SystemExit(1)
