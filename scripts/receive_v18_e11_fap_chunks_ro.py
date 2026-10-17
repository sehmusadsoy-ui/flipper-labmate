#!/usr/bin/env python3
"""Strict bounded receive of ONE LabMate FAP over pinned Momentum storage read_chunks.

Pinned Momentum's upstream FlipperStorage.read_file() calls port.read(n) once,
but pyserial.read(n) can legitimately return fewer bytes on timeout. Its
read_size counter adds REQUESTED bytes rather than number actually received.
This reader waits for the exact number of bytes in EVERY chunk and never
overclaims success. No storage write, flash, FAP install, GPIO, or reset.
The only serial reply is 'y', required by storage_cli_read_chunks to
acknowledge a pending READ. This is not a file write or CLI shell command.
"""
from __future__ import annotations

import hashlib
import re
import time

FAP = "/ext/apps/Tools/labmate.fap"
EXPECTED_BYTES = 81532
EXPECTED_SHA256 = "2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0"
CHUNK_SIZE = 8192
CHUNK_TIMEOUT_SECONDS = 25.0
MAX_TOTAL_SECONDS = 180.0

SIZE_REPLY = re.compile(rb"Size: ([1-9][0-9]{0,7})\Z")


def receive_exact_port(stream, wanted: int, *, timeout: float = CHUNK_TIMEOUT_SECONDS) -> bytes:
    """Fail closed on short timed read. Never count requested bytes as delivered."""
    if not 1 <= wanted <= CHUNK_SIZE:
        raise ValueError("invalid bounded serial chunk target")
    deadline = time.monotonic() + timeout
    result = bytearray()
    while len(result) < wanted:
        if time.monotonic() >= deadline:
            raise TimeoutError("incomplete USB serial chunk before finite deadline")
        got = stream.read(min(2048, wanted - len(result)))
        if not isinstance(got, bytes):
            raise ValueError("serial stream returned nonbytes")
        if len(got) > wanted - len(result):
            raise ValueError("USB stream returned oversized chunk")
        if got:
            result.extend(got)
    return bytes(result)


def read_old_fap_exact(client, *, expected_sha256: str = EXPECTED_SHA256,
                       expected_bytes: int = EXPECTED_BYTES) -> bytes:
    """Read fixed app path ONLY; strict Size/Ready/byte boundaries and SHA."""
    if (not isinstance(expected_bytes, int) or expected_bytes <= 0 or
            expected_bytes > 200_000 or
            not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)):
        raise ValueError("invalid pinned FAP expected identity")
    if not hasattr(client, "port") or not hasattr(client, "read"):
        raise ValueError("missing trusted Flipper storage client")
    if getattr(client, "chunk_size", CHUNK_SIZE) != CHUNK_SIZE:
        raise ValueError("unexpected pinned USB read chunk size")

    initial = client.send_and_wait_eol(
        f'storage read_chunks "{FAP}" {CHUNK_SIZE}\r')
    if initial not in (b"",):
        raise ValueError("unexpected storage command echo/response")
    reply = client.read.until(client.CLI_EOL)
    m = SIZE_REPLY.fullmatch(reply)
    if not m or int(m.group(1)) != expected_bytes:
        raise ValueError("remote storage read size differs from pinned old FAP")

    output = bytearray()
    expires = time.monotonic() + MAX_TOTAL_SECONDS
    while len(output) < expected_bytes:
        if time.monotonic() >= expires:
            raise TimeoutError("bounded full FAP read exceeded total deadline")
        ready = client.read.until("Ready?" + client.CLI_EOL)
        if ready not in (b"\r\n", b""):
            raise ValueError("unexpected native storage Ready frame")
        # read.until can buffer bytes ahead of its delimiter; because
        # device awaits y before sending the chunk, no pending binary
        # must be present BEFORE acknowledging this Ready frame.
        if getattr(client.read, "buffer", None):
            raise ValueError("unconsumed bytes before storage chunk acknowledgement")
        needed = min(CHUNK_SIZE, expected_bytes - len(output))
        client.send("y")  # read-flow handshake only, not SD data write
        output.extend(receive_exact_port(client.port, needed))
    if len(output) != expected_bytes:
        raise ValueError("incomplete/oversized strict FAP copy")

    # This read normally ends with CRLF + CLI prompt per storage_cli.c.
    terminal = client.read.until(client.CLI_PROMPT)
    if terminal != b"\r\n":
        raise ValueError("unexpected trailing storage transfer response")
    blob = bytes(output)
    if hashlib.sha256(blob).hexdigest() != expected_sha256:
        raise ValueError("exact FAP SHA256 mismatch after full serial read")
    return blob
