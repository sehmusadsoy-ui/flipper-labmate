#!/usr/bin/env python3
"""E11 post-update read-only evidence screen, not a firmware/boot PASS.

Accesses only a known pinned PC E11 package and device CLI:
device_info, storage md5 on three fixed resource paths. No updater,
storage writes, resets, app execution, recovery or restoration.

A resource hash match cannot attest internal flash or native TIM/EXTI
firmware. Physical E11 ownership tests remain independently required.
"""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import re
import sys
import tarfile

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from preflight_v18_e11_local import ARTIFACTS, RUN, SOURCE, assert_sha
from stage_v18_e11_review_only import inspect_updater
from verify_v18_full_review_pair import verify

EXPECTED_BASE = "d3f89dfe"
EXPECTED_FIRMWARE_LABEL = "mntm-dev"
REMOTE = {
    "E11_APP": "/ext/apps/Tools/labmate.fap",
    "E11_JS_GPIO": "/ext/apps_data/js_app/plugins/js_gpio.fal",
    "E11_NEW_MANIFEST": "/ext/Manifest",
}
MD5 = re.compile(r"[a-f0-9]{32}\Z")


def extract_new_manifest(resources: bytes) -> bytes:
    """Only extract the Manifest from an already full-verified nested archive."""
    found = []
    with tarfile.open(fileobj=io.BytesIO(resources), mode="r:gz") as archive:
        for member in archive:
            name = member.name
            while name.startswith("./"):
                name = name[2:]
            if name.lower() != "manifest":
                continue
            if not member.isfile() or member.size <= 0 or member.size > 4_000_000:
                raise ValueError("invalid packaged NEW resource Manifest")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("NEW Manifest archive unreadable")
            content = stream.read(member.size + 1)
            if len(content) != member.size:
                raise ValueError("NEW Manifest archive truncated")
            found.append(content)
    if len(found) != 1:
        raise ValueError("expected exactly one packaged NEW resource Manifest")
    return found[0]


def expected_md5(candidate: Path) -> dict[str, str]:
    """Verify independent source/run/binaries and derive device comparison values."""
    for name, digest in ARTIFACTS.items():
        assert_sha(candidate / name, digest)
    verify(candidate, SOURCE, RUN)
    packed = inspect_updater(candidate / "firmware-full-update.tgz")
    manifest = extract_new_manifest(packed["resources.tar.gz"])
    return {
        "E11_APP": hashlib.md5((candidate / "labmate.fap").read_bytes()).hexdigest(),
        "E11_JS_GPIO": hashlib.md5((candidate / "js_gpio.module").read_bytes()).hexdigest(),
        "E11_NEW_MANIFEST": hashlib.md5(manifest).hexdigest(),
    }


def evaluate(identity: bytes, live: dict[str, str], known: dict[str, str]) -> None:
    if not isinstance(identity, bytes) or not 1 <= len(identity) <= 131072:
        raise ValueError("invalid device_info response")
    firmware = identity.decode("utf-8", errors="strict").lower()
    if EXPECTED_FIRMWARE_LABEL not in firmware or EXPECTED_BASE not in firmware:
        raise ValueError("unexpected firmware label or commit report")
    if set(live) != set(REMOTE) or set(known) != set(REMOTE):
        raise ValueError("incomplete exact post-update evidence set")
    for key in REMOTE:
        actual = live[key].strip().lower()
        expected = known[key].strip().lower()
        if not MD5.fullmatch(actual) or not MD5.fullmatch(expected):
            raise ValueError("missing or invalid resource MD5: " + key)
        if actual != expected:
            raise ValueError("live resource differs from pinned FULL E11: " + key)


def device_read_only(port: str, scripts: Path) -> tuple[bytes, dict[str, str]]:
    if not re.fullmatch(r"COM[1-9][0-9]{0,2}", port):
        raise ValueError("explicit valid COM port required")
    storage_file = scripts / "flipper" / "storage.py"
    if scripts.is_symlink() or storage_file.is_symlink() or not storage_file.is_file():
        raise ValueError("pinned Momentum Flipper CLI transport missing")
    sys.path.insert(0, str(scripts.resolve()))
    import flipper.storage as transport
    verify_transport_origin(transport.__file__, scripts)
    storage = transport.FlipperStorage(port)
    storage.read = DeadlineRead(storage.port, timeout_seconds=20)
    with storage as connected:
        connected.send_and_wait_eol("device_info\r")
        info = connected.read.until(connected.CLI_PROMPT)
        found = {key: connected.hash_flipper(path).strip()
                 for key, path in REMOTE.items()}
    return info, found


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--momentum-scripts", required=True, type=Path)
    p.add_argument("--port", default="COM7")
    args = p.parse_args()
    try:
        known = expected_md5(args.candidate)
        identity, live = device_read_only(args.port, args.momentum_scripts)
        evaluate(identity, live, known)
    except Exception as exc:
        # Never disclose full device_info output or serial/device identifiers.
        cause = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("E11 POST-UPDATE READ-ONLY SCREEN: INCOMPLETE OR MISMATCH", file=sys.stderr)
        print("Reason: " + cause, file=sys.stderr)
        print("DO NOT AUTO-RETRY UPDATE OR RESTORE. Inspect device state.", file=sys.stderr)
        return 1
    print("E11 LIVE FIRMWARE LABEL AND BASE: MATCH (NOT A FULL FIRMWARE FINGERPRINT)")
    print("E11 LIVE APP FAP: MATCH PINNED E11 BY MD5")
    print("E11 LIVE NATIVE JS GPIO PLUGIN: MATCH PINNED E11 BY MD5")
    print("E11 LIVE RESOURCE MANIFEST: MATCH PINNED E11 BY MD5")
    print("E11 POST-UPDATE RESOURCE SCREEN PASS - READ ONLY")
    print("BOOT SEEN BY CLI; NATIVE GPIO/TIM1/TIM2/EXTI PHYSICAL PASS: NOT TESTED")
    print("DO NOT MERGE OR TAG STABLE BASED ON THIS SCREEN.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
