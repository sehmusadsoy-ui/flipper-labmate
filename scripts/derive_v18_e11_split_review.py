#!/usr/bin/env python3
"""Derive NEW, immutable-reference E11 FAP-SEPARATED REVIEW TGZ only.

The source artifact remains DO NOT FLASH. This derivative also remains
DO NOT FLASH. NO USB, serial, updater/install, device SD, restore or release.
Derives exact-byte firmware and radio with one omitted SD resource:
apps/Tools/labmate.fap (delivered separately as independently pinned FAP).
This is NOT a rebuilt native firmware nor a proven safe upgrade.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
from pathlib import Path
import tarfile

from audit_v18_e11_resource_impact import (
    FAP_PATH, JS_PATH, audit, inventory_resources, normalized, sha
)
from preflight_v18_e11_local import ARTIFACTS, SOURCE, RUN
from stage_v18_e11_review_only import inspect_updater, FILES, ROOT
from verify_v18_full_review_pair import verify, OFFICIAL_RADIO_SHA256

DERIVED_NAME = "firmware-full-update-SPLIT-REVIEW-DO-NOT-FLASH.tgz"
WARNING = (
    "NOT A RELEASE. DO NOT FLASH OR INSTALL THIS DERIVED REVIEW FILE.\n"
    "No physical test, no recovery rehearsal, no release authorization.\n"
    "Derived from previously vetted #38966248325; embedded LabMate FAP is removed.\n"
    "The matched LabMate FAP remains a SEPARATE file, not part of updater resources.\n"
    "Independent firmware boot / data restore safety is NOT established.\n"
)


def tarball(items: list[tuple[str, bytes | None]]) -> bytes:
    """Canonical, path-safe regular files/directories, deterministic gzip."""
    tarbuf = io.BytesIO()
    with tarfile.open(fileobj=tarbuf, mode="w", format=tarfile.PAX_FORMAT) as tf:
        seen: set[str] = set()
        for name, data in items:
            is_dir = data is None
            key = normalized(name, is_dir)
            if not key:
                continue
            if key in seen:
                raise ValueError("duplicate derived member")
            seen.add(key)
            info = tarfile.TarInfo(key + ("/" if is_dir else ""))
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mode = 0o755 if is_dir else 0o644
            if is_dir:
                info.type = tarfile.DIRTYPE
                tf.addfile(info)
            else:
                if len(data) > 90_000_000:
                    raise ValueError("oversized derived member")
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))
    out = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=out, mode="wb", mtime=0) as gz:
        gz.write(tarbuf.getvalue())
    return out.getvalue()


def split_resources(
    resource_blob: bytes, *,
    expected_fap: str = ARTIFACTS["labmate.fap"],
    expected_js: str = ARTIFACTS["js_gpio.module"]
) -> bytes:
    original = inventory_resources(resource_blob)
    matched_fap = 0
    nodes: list[tuple[str, bytes | None]] = []
    with tarfile.open(fileobj=io.BytesIO(resource_blob), mode="r:gz") as tf:
        for m in tf:
            if not (m.isfile() or m.isdir()):
                raise ValueError("linked/special source resource rejected")
            name = normalized(m.name, m.isdir())
            if not name:
                continue
            if m.isdir():
                nodes.append((name, None))
                continue
            if name.lower() == FAP_PATH.lower():
                stream = tf.extractfile(m)
                if stream is None or sha(stream.read()) != expected_fap:
                    raise ValueError("expected bundled FAP SHA256 mismatch")
                matched_fap += 1
                continue
            stream = tf.extractfile(m)
            if stream is None:
                raise ValueError("unreadable source resource member")
            blob = stream.read(m.size + 1)
            if len(blob) != m.size:
                raise ValueError("truncated source resource member")
            nodes.append((name, blob))
    if matched_fap != 1:
        raise ValueError("expected exactly one matching embedded LabMate FAP")
    result_blob = tarball(nodes)
    after = inventory_resources(result_blob)
    expected_after = {key: val for key, val in original.items()
                      if key.lower() != FAP_PATH.lower()}
    if after != expected_after:
        raise ValueError("unexpected resource change beyond removing exact LabMate FAP")
    js = [key for key in after if key.lower() == JS_PATH.lower()]
    if len(js) != 1 or after[js[0]] != expected_js:
        raise ValueError("split resources do not preserve exact JS GPIO binary")
    return result_blob


def derive_full_review(
    full: dict[str, bytes],
    *, expected_fap: str = ARTIFACTS["labmate.fap"],
    expected_js: str = ARTIFACTS["js_gpio.module"],
    expected_dfu: str = ARTIFACTS["firmware.dfu"],
    expected_radio: str = OFFICIAL_RADIO_SHA256,
) -> bytes:
    if set(full) != set(FILES):
        raise ValueError("wrong source updater member set")
    nested = split_resources(
        full["resources.tar.gz"], expected_fap=expected_fap, expected_js=expected_js
    )
    content = [
        (ROOT, None),
        *((ROOT + "/" + name, nested if name == "resources.tar.gz" else full[name])
          for name in FILES),
    ]
    result = tarball(content)
    # Critical identity controls verified again after derivation; only nested
    # resources may change, not native DFU/radio or updater manifest.
    with tarfile.open(fileobj=io.BytesIO(result), mode="r:gz") as tf:
        members = {m.name: tf.extractfile(m).read() for m in tf if m.isfile()}
    if set(members) != {ROOT + "/" + name for name in FILES}:
        raise ValueError("derived updater member mismatch")
    for name in FILES:
        previous = full[name]
        actual = members[ROOT + "/" + name]
        if name != "resources.tar.gz" and actual != previous:
            raise ValueError("derived updater changed non-resource member: " + name)
    if sha(members[ROOT + "/firmware.dfu"]) != expected_dfu:
        raise ValueError("changed native DFU in derived archive")
    if sha(members[ROOT + "/radio.bin"]) != expected_radio:
        raise ValueError("changed official radio in derived archive")
    return result


def stage_derived_review(candidate: Path, old_official: Path, output: Path) -> Path:
    if output.exists() or output.is_symlink():
        raise ValueError("review output already exists")
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError("output parent must be pre-existing real directory")
    absolute = output.resolve(strict=False)
    for protected in (candidate, old_official.parent):
        base = protected.resolve(strict=False)
        if absolute == base or base in absolute.parents:
            raise ValueError("output would modify a protected source/rollback folder")
    verify(candidate, SOURCE, RUN)
    summary = audit(old_official, candidate)
    if not summary["split_model_exact_fap_excluded"]:
        raise ValueError("split model did not pass")
    original = inspect_updater(candidate / "firmware-full-update.tgz")
    derived_bytes = derive_full_review(original)
    # Before any output: nested source, derived and official radio/OB verified.
    # Original radio/option bytes were independently checked by audit().
    if b"resources.tar.gz" not in original["update.fuf"]:
        raise ValueError("updater manifest unexpectedly lacks resources")
    output.mkdir()
    result = output / DERIVED_NAME
    result.write_bytes(derived_bytes)
    (output / "READ_ME_FIRST.txt").write_text(WARNING, encoding="utf-8")
    (output / "PROVENANCE.txt").write_text(
        "Original Actions run: " + str(RUN) + "\n"
        "Original LabMate source: " + SOURCE + "\n"
        "Original TGZ SHA256: " + ARTIFACTS["firmware-full-update.tgz"] + "\n"
        "Split TGZ SHA256: " + sha(derived_bytes) + "\n"
        "Only intended resource deletion: " + FAP_PATH + "\n"
        "No flash authorization: true\n",
        encoding="utf-8",
    )
    if hashlib.sha256(result.read_bytes()).hexdigest() != sha(derived_bytes):
        raise ValueError("derived file write verification failed")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--official-rollback", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        result = stage_derived_review(args.candidate, args.official_rollback, args.output)
    except (OSError, ValueError, UnicodeError, tarfile.TarError) as e:
        p.exit(1, "SPLIT REVIEW DERIVATION REFUSED - NO FLASH: " + str(e) + "\n")
    print("E11 DERIVED FAP-SEPARATED REVIEW TGZ:", result)
    print("SHA256:", hashlib.sha256(result.read_bytes()).hexdigest())
    print("E11 SPLIT REVIEW DERIVATION PASS - DO NOT FLASH / NO RECOVERY PROOF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
