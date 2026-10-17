#!/usr/bin/env python3
"""H0 diagnostics: attest exact E11 packaged vs installed native JS event_loop.

Only pinned PC artifacts and Flipper CLI device_info/storage md5 are read.
No JavaScript execution, storage writes, GPIO access, uploads, firmware
updates, reset, recovery, raw device_info or private file lists.
"""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
import re
import sys
import tarfile

PINNED = {
    "labmate.fap": "2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0",
    "js_gpio.module": "fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a",
    "firmware-full-update.tgz": "11ed3cdf4e99c9c7218973695d349cd946be97d21dfc59231113bde15e94c553",
}
UPDATER_ROOT = "f7-update-mntm-HEAD-d3f89dfe"
UPDATER_RESOURCE = UPDATER_ROOT + "/resources.tar.gz"
INNER_EVENT_LOOP = "apps_data/js_app/plugins/js_event_loop.fal"
REMOTE = {
    "labmate.fap": "/ext/apps/Tools/labmate.fap",
    "js_gpio.module": "/ext/apps_data/js_app/plugins/js_gpio.fal",
    "event_loop": "/ext/apps_data/js_app/plugins/js_event_loop.fal",
}
MD5_PATTERN = re.compile(r"[0-9a-f]{32}")


def digest_file(path: Path) -> tuple[str, str]:
    if path.is_symlink() or not path.is_file() or not (0 < path.stat().st_size < 100_000_000):
        raise ValueError("local pinned artifact unavailable: " + path.name)
    sha = hashlib.sha256()
    md5 = hashlib.md5()
    with path.open("rb") as reader:
        while chunk := reader.read(1024 * 1024):
            sha.update(chunk)
            md5.update(chunk)
    return sha.hexdigest(), md5.hexdigest()


def strip_dot_prefix(name: str) -> str:
    while name.startswith("./"):
        name = name[2:]
    return name


def packaged_event_loop_md5(resources: bytes) -> str:
    """Read exactly the one named member of independently SHA-pinned resource TAR."""
    if not isinstance(resources, bytes) or not (0 < len(resources) < 65_000_000):
        raise ValueError("missing or oversized expected resources archive")
    value = None
    with tarfile.open(fileobj=io.BytesIO(resources), mode="r:gz") as tf:
        for entry in tf:
            if strip_dot_prefix(entry.name) != INNER_EVENT_LOOP:
                continue
            if value is not None or not entry.isfile() or not 0 < entry.size < 8_000_000:
                raise ValueError("duplicate/invalid JS event_loop member in FULL resources")
            member = tf.extractfile(entry)
            if member is None:
                raise ValueError("unreadable event_loop member")
            body = member.read(entry.size + 1)
            if len(body) != entry.size:
                raise ValueError("truncated/oversized event_loop member")
            value = hashlib.md5(body).hexdigest()
    if value is None:
        raise ValueError("matched E11 FULL resources do not contain named js_event_loop.fal")
    return value


def local_expected_md5(candidate: Path) -> dict[str, str]:
    if candidate.is_symlink() or not candidate.is_dir():
        raise ValueError("pinned FULL E11 candidate directory missing")
    known = {}
    for name, sha_expected in PINNED.items():
        sha, md5 = digest_file(candidate / name)
        if sha != sha_expected:
            raise ValueError("independent E11 artifact SHA256 differs: " + name)
        known[name] = md5

    bundle = candidate / "firmware-full-update.tgz"
    resources = None
    with tarfile.open(bundle, mode="r:gz") as tf:
        for entry in tf:
            if strip_dot_prefix(entry.name) != UPDATER_RESOURCE:
                continue
            if resources is not None or not entry.isfile() or not 0 < entry.size < 65_000_000:
                raise ValueError("invalid/duplicate resources in pinned FULL updater")
            member = tf.extractfile(entry)
            if member is None:
                raise ValueError("unreadable pinned FULL resources")
            resources = member.read(entry.size + 1)
            if len(resources) != entry.size:
                raise ValueError("truncated pinned FULL resources")
    if resources is None:
        raise ValueError("no resources in pinned FULL updater")

    return {
        "labmate.fap": known["labmate.fap"],
        "js_gpio.module": known["js_gpio.module"],
        "event_loop": packaged_event_loop_md5(resources),
    }


def compare_remote_identity(info: bytes, remote: dict[str, str], expected: dict[str, str]) -> None:
    if not isinstance(info, bytes) or not 1 <= len(info) < 131072:
        raise ValueError("invalid device information response")
    low = info.decode("utf-8", "strict").lower()
    if "mntm-dev" not in low or "d3f89dfe" not in low:
        raise ValueError("different firmware label/base; no claims")
    if set(remote) != set(REMOTE) or set(expected) != set(REMOTE):
        raise ValueError("incomplete JS runtime identity audit")
    for k in REMOTE:
        live = remote[k].lower().strip()
        if not MD5_PATTERN.fullmatch(live):
            raise ValueError("remote file not readable as MD5: " + k)
        if live != expected[k]:
            raise ValueError("remote checksum mismatches pinned FULL resources: " + k)


def check_device(port: str, scripts: Path, expected: dict[str, str]) -> None:
    if not re.fullmatch(r"COM[1-9][0-9]{0,2}", port):
        raise ValueError("explicit COMn serial port required")
    storage_file = scripts / "flipper" / "storage.py"
    if scripts.is_symlink() or storage_file.is_symlink() or not storage_file.is_file():
        raise ValueError("pinned local Momentum CLI transport missing")

    from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
    sys.path.insert(0, str(scripts.resolve()))
    import flipper.storage as transport
    verify_transport_origin(transport.__file__, scripts)

    device = transport.FlipperStorage(port)
    device.read = DeadlineRead(device.port, timeout_seconds=20)
    with device as serial:
        serial.send_and_wait_eol("device_info\r")
        info = serial.read.until(serial.CLI_PROMPT)
        remote = {key: serial.hash_flipper(path).strip()
                  for key, path in REMOTE.items()}
    compare_remote_identity(info, remote, expected)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--momentum-scripts", required=True, type=Path)
    p.add_argument("--candidate", required=True, type=Path)
    args = p.parse_args()
    print("E11 H JS RUNTIME CHECK: READ-ONLY device_info + 3 storage md5; NO JS/RUN/FLASH.")
    try:
        expected = local_expected_md5(args.candidate)
        check_device(args.port, args.momentum_scripts, expected)
    except (OSError, ValueError, UnicodeError, RuntimeError, tarfile.TarError) as exc:
        # Only public fixed source/artifact names; never raw device replies.
        print("E11 H JS RUNTIME INCOMPLETE: " + str(exc), file=sys.stderr)
        print("H0 UNPROVEN; H1/H2 NOT AUTHORIZED. NO AUTOMATIC FIX.", file=sys.stderr)
        return 1
    except Exception as exc:
        print("E11 H JS RUNTIME INCOMPLETE: " + type(exc).__name__, file=sys.stderr)
        print("H0 UNPROVEN; H1/H2 NOT AUTHORIZED.", file=sys.stderr)
        return 1
    print("E11 H JS EVENT_LOOP FAL: EXACT FULL-BUNDLE MD5 MATCH")
    print("E11 H JS GPIO FAL + LABMATE FAP: EXACT PINNED PAIR MD5 MATCH")
    print("E11 H JS RUNTIME FILE-INTEGRITY SCREEN PASS - JS EXECUTION NOT TESTED")
    print("H0/H1/H2 REMAIN NOT PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
