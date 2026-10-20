#!/usr/bin/env python3
"""Finish the EXISTING LabMate v1.9 E11-only draft after verified readback.

Never create/re-upload/delete/clobber a release, tag, branch, asset, Flipper
FAP or firmware. Publishing requires exact preexisting draft, source pin,
the server SHA256 digests and three complete independently downloaded assets.
This is the recovery for premature git-ref checking of an unpublished draft.
Run only on the user's native Windows PC with explicit publication approval.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

REPO = "sehmusadsoy-ui/flipper-labmate"
TAG = "v1.9"
SOURCE = "72eb58d6c65d31f510acf6f532ee23c543a9149d"
TITLE = "LabMate v1.9 Stable — Logic Scope (E11 Custom Momentum ONLY)"
FAP_SHA = "d8bb04cf6de6ebaa466e7487e619d9f68af21dac49df2aa51e91dfae1f9f55c2"
NOTES_BLOB = "e97f1f797b245bddd1ea8206ae466933549531d1"
V18_MAIN_FAM_BLOB = "951734bbc8b498cca9f099590363ee4c46f7488b"
V18_TAG = "02b05639364d6dd71f5eb70456eca379c59218cb"
E11_TAG = "99cb65d0194dc59d423cfa439c90618ac6b9f114"
OLD_SHA = "0f0b246d042c45eabe2c29dab692dbc7df20817c419c011ca31a313d4b62141a"
ASSETS = {
    "labmate.fap": (101468, FAP_SHA),
    "SHA256SUMS.txt": (78, "34c70492a0efc336e5da2105efaee1e20b03f2c34daae98737a48dc770f002e4"),
    "READ_ME_FIRST-E11.md": (1361, "394d3ab06f7d1c57013372d42cd6adb15bfb273189deb5c29e32769a5f115e4d"),
}

def require(ok: bool, reason: str) -> None:
    if not ok:
        raise RuntimeError(reason)

def sha256(p: Path) -> str:
    with p.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def git_blob(p: Path) -> str:
    data = p.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def run(argv, *, capture=True, timeout=90):
    cmd = [str(x) for x in argv]
    print("COMMAND:", " ".join(cmd), flush=True)
    p = subprocess.run(
        cmd, capture_output=capture, text=capture, timeout=timeout,
        encoding="utf-8" if capture else None, errors="strict" if capture else None)
    if p.returncode != 0:
        if capture:
            print((p.stderr or "")[-1600:], file=sys.stderr)
        raise RuntimeError("command failed " + str(p.returncode) +
                           "; DO NOT RE-RUN OR DELETE THE DRAFT")
    return p.stdout if capture else None

def ghapi(resource: str) -> object:
    return json.loads(run(["gh", "api", resource], timeout=45))

def draft() -> dict:
    data = json.loads(run([
        "gh", "release", "view", TAG, "-R", REPO,
        "--json", "name,body,tagName,isDraft,isPrerelease,targetCommitish,assets"
    ], timeout=45))
    require(data.get("tagName") == TAG and data.get("isDraft") is True and
            data.get("isPrerelease") is False,
            "exact v1.9 unpublished Stable draft not present")
    require(data.get("targetCommitish") == SOURCE,
            "draft target commit differs from the ACTUALLY TESTED FAP source")
    require(data.get("name") == TITLE,
            "release name/compatibility notice drift: received " +
            repr(data.get("name")) + "; expected " + repr(TITLE))
    description = str(data.get("body") or "")
    for marker in ("E11-patched Momentum firmware ONLY",
                   SOURCE, FAP_SHA, "ordinary/stock Momentum",
                   "No multi-channel acquisition or high-speed"):
        require(marker in description, "release notes omit " + marker)
    asset_list = data.get("assets")
    require(isinstance(asset_list, list) and len(asset_list) == 3,
            "unexpected asset count in existing draft")
    existing = {item.get("name"): item for item in asset_list}
    require(set(existing) == set(ASSETS), "existing draft asset names differ")
    for name, (size, digest) in ASSETS.items():
        a = existing[name]
        require(a.get("size") == size and a.get("digest") == "sha256:" + digest,
                "GitHub server asset hash/size mismatch: " + name)
    return data

def previous_releases() -> None:
    # All calls are GET only. Do not mutate the ordinary v1.8 release.
    ordinary = ghapi("repos/" + REPO + "/releases/latest")
    require(ordinary.get("tag_name") == "v1.8",
            "normal-Momentum Latest is not v1.8")
    normal = ghapi("repos/" + REPO + "/git/ref/tags/v1.8")
    custom = ghapi("repos/" + REPO + "/git/ref/tags/v1.8-e11-custom-momentum")
    require(normal.get("object", {}).get("sha") == V18_TAG and
            custom.get("object", {}).get("sha") == E11_TAG,
            "previous v1.8 release tags moved")
    app = ghapi("repos/" + REPO + "/contents/application.fam?ref=main")
    require(app.get("sha") == V18_MAIN_FAM_BLOB,
            "ordinary Stable main application manifest changed")
    git_commit = ghapi("repos/" + REPO + "/git/commits/" + SOURCE)
    require(git_commit.get("sha") == SOURCE and git_commit.get("tree"),
            "actual tested source commit is unavailable")
    # A draft may intentionally have no git tag yet. Do not require one.
    tag = ghapi("repos/" + REPO + "/git/matching-refs/tags/v1.9")
    require(isinstance(tag, list) and len(tag) == 0,
            "v1.9 Git tag already exists; STOP (do not change it)")
    print("DRAFT_WITHOUT_TAG_AND_V18_LATEST: PASS", flush=True)

def check_local(package: Path, fap: Path, previous: Path) -> None:
    require(package.is_dir() and not package.is_symlink(),
            "prior local release directory missing or symlinked")
    actual_names = {f.name for f in package.iterdir()}
    require(actual_names == set(ASSETS) | {"RELEASE_NOTES.md"},
            "unexpected/missing local draft package files")
    for name, (size, digest) in ASSETS.items():
        asset = package / name
        require(asset.is_file() and not asset.is_symlink() and
                asset.stat().st_size == size and sha256(asset) == digest,
                "local release asset changed: " + name)
    notes = package / "RELEASE_NOTES.md"
    require(notes.is_file() and not notes.is_symlink() and
            git_blob(notes) == NOTES_BLOB,
            "local release description bytes changed")
    require(package.joinpath("SHA256SUMS.txt").read_text(encoding="ascii") ==
            FAP_SHA + "  labmate.fap\n", "release SHA256SUMS content mismatch")
    require(fap.stat().st_size == ASSETS["labmate.fap"][0] and
            sha256(fap) == FAP_SHA and not fap.is_symlink(),
            "previously built genuine FAP does not match installed candidate")
    require(previous.stat().st_size == 99376 and
            sha256(previous) == OLD_SHA and not previous.is_symlink(),
            "previous 99,376-byte FAP PC recovery backup changed")
    require(package.joinpath("labmate.fap").read_bytes() == fap.read_bytes(),
            "release package differs from native Windows built candidate")
    print("LOCAL_FAP_AND_3_ASSETS_BYTE_HASHES: PASS", flush=True)

def download_and_readback(package: Path) -> None:
    # A GitHub draft has no source archive/tag ref; request named ASSETS only.
    # gh release download uses the release asset URLs, not missing tag archive.
    with tempfile.TemporaryDirectory(prefix="labmate-v19-draft-verify-") as d:
        folder = Path(d)
        run([
            "gh", "release", "download", TAG, "-R", REPO,
            "--dir", folder, "--pattern", "labmate.fap",
            "--pattern", "SHA256SUMS.txt",
            "--pattern", "READ_ME_FIRST-E11.md"
        ], capture=False, timeout=240)
        require({p.name for p in folder.iterdir()} == set(ASSETS),
                "draft download did not return exactly three assets")
        for name, (size, digest) in ASSETS.items():
            downloaded = folder / name
            require(downloaded.is_file() and downloaded.stat().st_size == size and
                    sha256(downloaded) == digest and
                    downloaded.read_bytes() == package.joinpath(name).read_bytes(),
                    "full GitHub draft asset readback mismatch: " + name)
    print("DRAFT_REMOTE_ASSET_3_OF_3_FULL_READBACK: PASS", flush=True)

def main() -> None:
    require(os.name == "nt", "Windows only; not WSL")
    require(sys.argv[1:] == ["--publish-existing-draft"],
            "explicit --publish-existing-draft required")
    require(shutil.which("gh") is not None, "GitHub CLI missing")
    home = Path.home()
    package = home / "Documents/LabMate-Releases/v1.9-STABLE-E11-72eb58d"
    fap = home / r"LabMate-v19-WinSDK-050ec62\build\f7-firmware-C\.extapps\labmate.fap"
    previous = home / (
        r"Documents\LabMate-FAP-PC-Backups"
        r"\V19-SCOPE-REDESIGN-PREBUILD-72eb58d"
        r"\labmate-v19-99376-before-redesign.fap"
    )
    check_local(package, fap, previous)
    previous_releases()
    draft()
    print("EXISTING_V19_DRAFT_PINNED_ASSETS: PASS", flush=True)
    download_and_readback(package)
    # Final read-only recheck immediately before PUBLICATION action.
    draft()
    previous_releases()
    print("READY_TO_PUBLISH_EXISTING_VERIFIED_DRAFT: PASS", flush=True)
    # No new release/tag upload; publish only the existing independently
    # verified draft. GitHub creates the absent v1.9 tag at this step.
    run(["gh", "release", "edit", TAG, "-R", REPO,
         "--draft=false", "--latest=false"], capture=False, timeout=120)
    public = json.loads(run([
        "gh", "release", "view", TAG, "-R", REPO,
        "--json", "tagName,isDraft,isPrerelease,targetCommitish,url,assets"
    ], timeout=60))
    require(public.get("isDraft") is False and
            public.get("isPrerelease") is False and
            public.get("tagName") == TAG and
            public.get("targetCommitish") == SOURCE,
            "post-publish release attributes not confirmed")
    tag = ghapi("repos/" + REPO + "/git/ref/tags/" + TAG)
    require(tag.get("object", {}).get("type") == "commit" and
            tag.get("object", {}).get("sha") == SOURCE,
            "published v1.9 tag does not point to exact tested commit")
    require(ghapi("repos/" + REPO + "/releases/latest").get("tag_name") == "v1.8",
            "ordinary v1.8 Latest changed: manual investigation required")
    require({a.get("name"): (a.get("size"), a.get("digest"))
             for a in public.get("assets", [])} ==
            {name: (size, "sha256:" + digest)
             for name, (size, digest) in ASSETS.items()},
            "published release assets drifted")
    print("LABMATE_V19_E11_COMPATIBLE_STABLE_RELEASE: PASS", flush=True)
    print("RELEASE_URL:", public.get("url"))
    print("TAG_COMMIT:", SOURCE)
    print("FAP_SHA256:", FAP_SHA)
    print("ORDINARY_MOMENTUM_LATEST: v1.8 UNCHANGED")
    print("DEVICE_WRITES: ZERO | FIRMWARE_FLASH: NO")

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("V19 EXISTING DRAFT RECOVERY NO-GO:", str(error), file=sys.stderr)
        print("NO RETRY. Preserve the existing release draft, package and tags.",
              file=sys.stderr)
        raise SystemExit(1)
