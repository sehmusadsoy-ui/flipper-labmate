#!/usr/bin/env python3
"""OFFLINE-only protocol fixture for staged v1.9 E11 FAP and two safe renames.

This module intentionally has no Flipper transport import, serial connection,
or device-run CLI. Its in-memory fake models exact command echoes, "Ready",
stat, MD5, chunk writes, readback, rename, and final state checks.
It is NOT an installer or proof of firmware ABI compatibility.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys
from dataclasses import dataclass, field

from simulate_v19_e11_fap_swap_offline import (
    ACTIVE, NEW, CURRENT_BACKUP, LEGACY_BACKUP, FAILED_V19_BACKUP,
    V19_SIZE, V19_SHA, V18_SIZE, V18_SHA, LEGACY_SIZE, LEGACY_SHA,
    verified_pc_artifact,
)

ABSENT = b"Storage error: file/dir not exist"
MD5_HEX = re.compile(r"[0-9a-f]{32}\Z")
MAX_CHUNK = 4096
ALLOWED = frozenset((ACTIVE, NEW, CURRENT_BACKUP, LEGACY_BACKUP, FAILED_V19_BACKUP))
RENAMES = frozenset(((ACTIVE, CURRENT_BACKUP), (NEW, ACTIVE)))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def require(condition: bool, why: str) -> None:
    if not condition:
        raise ValueError(why)


@dataclass
class FakeCLI:
    """One fake CLI session; never connects to a physical device."""
    v18: bytes
    legacy: bytes
    faults: set[str] = field(default_factory=set)
    CLI_EOL: str = "\r\n"
    CLI_PROMPT: str = ">: "
    fs: dict[str, bytes] = field(init=False)
    replies: list[bytes] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    pending_chunk: int | None = None
    chunk_count: int = 0
    rename_count: int = 0

    def __post_init__(self):
        require(len(self.v18) == V18_SIZE and sha(self.v18) == V18_SHA, "wrong current v1.8 fixture")
        require(len(self.legacy) == LEGACY_SIZE and sha(self.legacy) == LEGACY_SHA, "wrong legacy fixture")
        self.fs = {ACTIVE: self.v18, LEGACY_BACKUP: self.legacy}

    def until(self, marker: str) -> bytes:
        require(marker in (self.CLI_EOL, self.CLI_PROMPT), "bad CLI marker")
        require(bool(self.replies), "missing simulated CLI reply")
        return self.replies.pop(0)

    @property
    def read(self):
        return self

    @property
    def port(self):
        return self

    def send_and_wait_eol(self, command: str) -> bytes:
        require(command.endswith("\r"), "expected single CR")
        cmd = command[:-1]
        self.commands.append(cmd)
        if "echo-fail" in self.faults:
            raise ValueError("simulated CLI command echo disagreement")
        if cmd.startswith("storage stat "):
            match = re.fullmatch(r'storage stat "([^"]+)"', cmd)
            require(match is not None and match.group(1) in ALLOWED, "unapproved stat path")
            path = match.group(1)
            stat_line = (f"File, size: {len(self.fs[path])}b".encode()
                         if path in self.fs else ABSENT)
            self.replies.extend((stat_line, b"\r\n"))
        elif cmd.startswith("storage write_chunk "):
            match = re.fullmatch(r'storage write_chunk "([^"]+)" ([1-9][0-9]*)', cmd)
            require(match is not None and match.group(1) == NEW, "unapproved write path")
            size = int(match.group(2))
            require(1 <= size <= MAX_CHUNK, "bad write chunk size")
            require(self.pending_chunk is None, "parallel writes disallowed")
            self.pending_chunk = size
            self.replies.append(b"NotReady" if "bad-ready" in self.faults else b"Ready")
        elif cmd.startswith("storage rename "):
            match = re.fullmatch(r'storage rename "([^"]+)" "([^"]+)"', cmd)
            require(match is not None and (match.group(1), match.group(2)) in RENAMES,
                    "unapproved rename")
            source, target = match.groups()
            require(source in self.fs and target not in self.fs, "rename source/target mismatch")
            self.rename_count += 1
            # Native rename takes effect during command execution before the
            # response arrives. The fail mode leaves changed, uncertain state.
            self.fs[target] = self.fs.pop(source)
            self.replies.append(
                b"ambiguous" if ("rename-reply-fail" in self.faults or
                                 ("rename-reply-fail-second" in self.faults and
                                  self.rename_count == 2)) else b"\r\n"
            )
        else:
            raise ValueError("unrecognized native CLI command")
        return cmd.encode("ascii")

    def write(self, data: bytes) -> int:
        require(self.pending_chunk is not None, "binary write without Ready")
        require(type(data) is bytes and len(data) == self.pending_chunk, "unapproved binary length")
        self.chunk_count += 1
        if "short-first-chunk" in self.faults and self.chunk_count == 1:
            count = len(data) - 1
        else:
            count = len(data)
        self.fs[NEW] = self.fs.get(NEW, b"") + data[:count]
        self.pending_chunk = None
        if "chunk-tail-fail" in self.faults:
            self.replies.append(b"unexpected")
        else:
            self.replies.append(b"\r\n")
        return count

    def flush(self):
        return None

    def hash_flipper(self, path: str) -> str:
        require(path in ALLOWED and path in self.fs, "MD5 unavailable")
        if "stage-md5-bad" in self.faults and path == NEW:
            return "0" * 32
        return md5(self.fs[path])

    def read_file(self, path: str) -> bytes:
        require(path in ALLOWED and path in self.fs, "no readback path")
        if "stage-readback-corrupt" in self.faults and path == NEW:
            value = self.fs[path]
            return value[:-1] + bytes([value[-1] ^ 1])
        return self.fs[path]


def stat(client: FakeCLI, path: str) -> bytes:
    require(path in ALLOWED, "stat not allowlisted")
    cmd = f'storage stat "{path}"'
    echo = client.send_and_wait_eol(cmd + "\r")
    require(echo == cmd.encode("ascii"), "unrecognized native stat echo")
    line = client.read.until(client.CLI_EOL)
    tail = client.read.until(client.CLI_PROMPT)
    require(tail == b"\r\n", "unrecognized native stat tail")
    return line


def exact_file(client: FakeCLI, path: str, data: bytes) -> None:
    require(type(data) is bytes, "expected binary reference")
    require(stat(client, path) == f"File, size: {len(data)}b".encode(),
            "on-device file size drift")
    actual = client.hash_flipper(path).lower().strip()
    require(MD5_HEX.fullmatch(actual) is not None and actual == md5(data),
            "on-device file MD5 drift")
    require(client.read_file(path) == data, "on-device full binary readback drift")


def preflight(client: FakeCLI, v18: bytes, legacy: bytes) -> None:
    exact_file(client, ACTIVE, v18)
    exact_file(client, LEGACY_BACKUP, legacy)
    for item in (NEW, CURRENT_BACKUP, FAILED_V19_BACKUP):
        require(stat(client, item) == ABSENT, "reserved SD path already occupied")


def append_chunk(client: FakeCLI, chunk: bytes) -> None:
    require(type(chunk) is bytes and 1 <= len(chunk) <= MAX_CHUNK,
            "unrecognized stage chunk")
    cmd = f'storage write_chunk "{NEW}" {len(chunk)}'
    echo = client.send_and_wait_eol(cmd + "\r")
    require(echo == cmd.encode("ascii"), "native write echo mismatch")
    require(client.read.until(client.CLI_EOL) == b"Ready", "native write Ready mismatch")
    count = client.port.write(chunk)
    require(count == len(chunk), "short native write: STOP NO AUTO RETRY")
    client.port.flush()
    require(client.read.until(client.CLI_PROMPT) == b"\r\n", "native write tail ambiguous")


def stage(client: FakeCLI, candidate: bytes, v18: bytes, legacy: bytes) -> None:
    require(type(candidate) is bytes and len(candidate) == V19_SIZE and sha(candidate) == V19_SHA,
            "wrong candidate FAP bytes or hash")
    preflight(client, v18, legacy)
    for offset in range(0, len(candidate), MAX_CHUNK):
        append_chunk(client, candidate[offset:offset + MAX_CHUNK])
    exact_file(client, NEW, candidate)
    exact_file(client, ACTIVE, v18)
    exact_file(client, LEGACY_BACKUP, legacy)
    require(stat(client, CURRENT_BACKUP) == ABSENT, "v1.8 recovery target not empty")
    require(stat(client, FAILED_V19_BACKUP) == ABSENT, "v1.9 failure backup target not empty")


def rename_once(client: FakeCLI, source: str, target: str) -> None:
    require((source, target) in RENAMES, "rename not allowlisted")
    require(stat(client, source) != ABSENT, "rename source missing")
    require(stat(client, target) == ABSENT, "rename target occupied")
    cmd = f'storage rename "{source}" "{target}"'
    echo = client.send_and_wait_eol(cmd + "\r")
    require(echo == cmd.encode("ascii"), "unexpected native rename echo")
    require(client.read.until(client.CLI_PROMPT) == b"\r\n",
            "native rename result ambiguous; STOP, no auto retry")


def promote(client: FakeCLI, candidate: bytes, v18: bytes, legacy: bytes) -> None:
    """Two separate virtual renames. A failure always leaves state as-is."""
    exact_file(client, NEW, candidate)
    exact_file(client, ACTIVE, v18)
    exact_file(client, LEGACY_BACKUP, legacy)
    require(stat(client, CURRENT_BACKUP) == ABSENT, "v1.8 backup target occupied")
    require(stat(client, FAILED_V19_BACKUP) == ABSENT, "failed v1.9 backup path occupied")
    rename_once(client, ACTIVE, CURRENT_BACKUP)
    require(stat(client, ACTIVE) == ABSENT, "active FAP still present after first rename")
    exact_file(client, CURRENT_BACKUP, v18)
    exact_file(client, NEW, candidate)
    exact_file(client, LEGACY_BACKUP, legacy)
    rename_once(client, NEW, ACTIVE)
    exact_file(client, ACTIVE, candidate)
    exact_file(client, CURRENT_BACKUP, v18)
    exact_file(client, LEGACY_BACKUP, legacy)
    require(stat(client, NEW) == ABSENT, "stage not removed during final activation")
    require(stat(client, FAILED_V19_BACKUP) == ABSENT, "reserved failed FAP path changed")


def simulate(v18: bytes, legacy: bytes, candidate: bytes) -> dict:
    client = FakeCLI(v18, legacy)
    stage(client, candidate, v18, legacy)
    require(client.fs[ACTIVE] == v18 and client.fs[NEW] == candidate,
            "old app not preserved through stage")
    promote(client, candidate, v18, legacy)
    require(client.fs[ACTIVE] == candidate and
            client.fs[CURRENT_BACKUP] == v18 and
            client.fs[LEGACY_BACKUP] == legacy, "virtual FAP protection failed")
    require(client.rename_count == 2, "expected exactly 2 virtual renames")
    return {
        "MOCK_STAGE": "PASS",
        "MOCK_RENAMED_TO_V18_BACKUP": "PASS",
        "MOCK_V19_ACTIVATION": "PASS",
        "MOCK_ORIGINAL_E11_PRESERVED": "PASS",
        "MOCK_CHUNKS": client.chunk_count,
        "MOCK_RENAME_COUNT": client.rename_count,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate", required=True, type=Path)
    p.add_argument("--current-v18-pc-backup", required=True, type=Path)
    p.add_argument("--legacy-e11-pc-backup", required=True, type=Path)
    args = p.parse_args()
    print("V19 E11 IN-MEMORY CLI PROTOCOL FIXTURE (NO DEVICE OR DISK WRITES)")
    try:
        candidate = verified_pc_artifact(args.candidate, V19_SIZE, V19_SHA)
        v18 = verified_pc_artifact(args.current_v18_pc_backup, V18_SIZE, V18_SHA)
        prior = verified_pc_artifact(args.legacy_e11_pc_backup, LEGACY_SIZE, LEGACY_SHA)
        results = simulate(v18, prior, candidate)
    except Exception as exc:
        reason = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("V19 IN-MEMORY NATIVE CLI MODEL NO-GO: " + reason, file=sys.stderr)
        print("NO RETRY/INSTALL/DEVICE WRITE AUTHORIZED", file=sys.stderr)
        return 1
    for key, val in results.items():
        print(key + ": " + str(val))
    print("REAL-FAP INPUT MOCK NATIVE CLI E11 STAGE/TWO-RENAME: PASS")
    print("USB_CALLS: 0 | DEVICE_WRITES: 0 | PC_WRITES: 0")
    print("Firmware ABI attestation and real device write remain NOT AUTHORIZED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
