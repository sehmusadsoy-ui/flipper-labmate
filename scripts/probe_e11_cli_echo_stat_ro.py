#!/usr/bin/env python3
"""Source-pinned, READ-ONLY probe of real E11 Momentum CLI command framing.

Issue exactly one fixed, harmless storage stat command and inspect the
first CRLF-delimited line (echo), second line (size), and prompt. This
separates shell-echo from native command output WITHOUT storage writes.
Recheck empty sidecar / old FAP / JS + Manifest with fixed read-only
commands before attributing any result to native transport identity.
Never issue write_chunk, append, rename, remove, launch, reboot or flash.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from check_v18_e11_final_fap_prewrite_ro import (
    APP_REMOTE, pinned_local_expectation
)
from check_v18_e11_h_js_runtime_ro import (
    REMOTE as JS_REMOTE, compare_remote_identity as check_js
)
from check_v18_e11_postupdate_readonly import (
    REMOTE as POST_REMOTE, evaluate as check_resources
)

STAGE = "/ext/apps/Tools/labmate.e11-new-stage"
RESERVED = "/ext/apps/Tools/labmate.e11-pre-final.bak"
EMPTY_MD5 = "d41d8cd98f00b204e9800998ecf8427e"
EXPECTED_OLD_SIZE = b"File, size: 81532b"
STAGE_EMPTY_SIZE = b"File, size: 0b"
STAGE_CMD = f'storage stat "{STAGE}"'
CLI_EOL = "\r\n"
CLI_PROMPT = ">: "


def probe_fixed_stat(client) -> dict[str, str]:
    """Read-only. Capture the *previously discarded* first echo line."""
    if client.CLI_EOL != CLI_EOL or client.CLI_PROMPT != CLI_PROMPT:
        raise ValueError("unexpected pinned Momentum console framing")
    echo = client.send_and_wait_eol(STAGE_CMD + "\r")
    result = client.read.until(client.CLI_EOL)
    tail = client.read.until(client.CLI_PROMPT)

    if not isinstance(echo, bytes) or len(echo) > 160:
        raise ValueError("unbounded or nonbinary stat first line")
    if not isinstance(result, bytes) or len(result) > 160:
        raise ValueError("unbounded or nonbinary stat second line")
    if not isinstance(tail, bytes) or len(tail) > 160:
        raise ValueError("unbounded or nonbinary stat tail")
    # Include ONLY the fixed path's echo hex for a mismatched command.
    # Any other data/serial IDs in the unexpected line are deliberately
    # NOT shown: classification rather than untrusted text.
    if echo != STAGE_CMD.encode("ascii"):
        return {
            "cli_first_line": "UNEXPECTED (" + str(len(echo)) + " bytes)",
            "cli_second_line": "EXPECTED_EMPTY_FILE" if result == STAGE_EMPTY_SIZE else "UNEXPECTED",
            "cli_tail": "EXPECTED_CRLF" if tail == b"\r\n" else "UNEXPECTED",
            "real_echo_ready_handshake_confirmed": "NO",
        }
    return {
        "cli_first_line": "EXACT_COMMAND_ECHO",
        "cli_second_line": "EXPECTED_EMPTY_FILE" if result == STAGE_EMPTY_SIZE else "UNEXPECTED",
        "cli_tail": "EXPECTED_CRLF" if tail == b"\r\n" else "UNEXPECTED",
        "real_echo_ready_handshake_confirmed": "NO (READ ONLY stat, never issued write_chunk)",
    }


def read_only_audit(client, post: dict[str, str], js: dict[str, str]) -> dict[str, str]:
    # Determine exact command-echo behavior BEFORE any write-side assumptions.
    frame = probe_fixed_stat(client)
    if (frame["cli_first_line"] != "EXACT_COMMAND_ECHO"
            or frame["cli_second_line"] != "EXPECTED_EMPTY_FILE"
            or frame["cli_tail"] != "EXPECTED_CRLF"):
        raise ValueError("real read-only stat command framing unexpected; STOP")
    client.send_and_wait_eol("device_info\r")
    device_info = client.read.until(client.CLI_PROMPT)
    paths = dict(POST_REMOTE)
    paths.update({k: v for k, v in JS_REMOTE.items() if k not in paths})
    allowed = {
        APP_REMOTE, "/ext/apps_data/js_app/plugins/js_gpio.fal",
        "/ext/apps_data/js_app/plugins/js_event_loop.fal", "/ext/Manifest"
    }
    if set(paths.values()) != allowed:
        raise ValueError("native resource read scope changed")
    current = {k: client.hash_flipper(path).strip() for k, path in paths.items()}
    check_resources(device_info, {k: current[k] for k in POST_REMOTE}, post)
    check_js(device_info, {k: current[k] for k in JS_REMOTE}, js)
    if stat_exact(client, APP_REMOTE) != EXPECTED_OLD_SIZE:
        raise ValueError("old active LabMate stat drift")
    if stat_exact(client, STAGE) != STAGE_EMPTY_SIZE:
        raise ValueError("existing staged sidecar is no longer empty")
    if stat_exact(client, RESERVED) != b"Storage error: file/dir not exist":
        raise ValueError("reserved backup path unexpectedly present")
    if client.hash_flipper(STAGE).strip().lower() != EMPTY_MD5:
        raise ValueError("existing staged sidecar MD5 no longer empty")
    if client.hash_flipper(APP_REMOTE).strip().lower() != post["E11_APP"]:
        raise ValueError("old active LabMate FAP hash drift")
    return {
        "real_cli_echo": frame["cli_first_line"],
        "real_cli_stat_result": frame["cli_second_line"],
        "old_app": "PINNED MD5 + 81532 BYTE SIZE MATCH",
        "native_gpio_event_loop_manifest": "PINNED MD5 MATCH",
        "existing_stage": "PRESENT EMPTY 0 BYTES, MD5 MATCH",
        "old_fap_reserved_backup": "ABSENT",
        "writing": "NONE",
        "fap_installed": "NO",
        "write_chunk_ready_probed": "NO",
    }


def stat_exact(client, path: str) -> bytes:
    if path not in (APP_REMOTE, STAGE, RESERVED):
        raise ValueError("unapproved stage stat")
    client.send_and_wait_eol(f'storage stat "{path}"\r')
    status = client.read.until(client.CLI_EOL)
    tail = client.read.until(client.CLI_PROMPT)
    if tail != b"\r\n":
        raise ValueError("unrecognized trailing stat/prompt frame")
    return status


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", required=True)
    p.add_argument("--momentum-scripts", type=Path, required=True)
    p.add_argument("--old-candidate", type=Path, required=True)
    args = p.parse_args()
    print("E11 CLI ECHO FRAMING READ-ONLY INSPECTION (NO SD WRITE)")
    try:
        if not re.fullmatch(r"COM[1-9][0-9]{0,2}", args.port):
            raise ValueError("invalid exact COM port")
        post, js = pinned_local_expectation(args.old_candidate)
        scripts = args.momentum_scripts
        module = scripts / "flipper" / "storage.py"
        if scripts.is_symlink() or module.is_symlink() or not module.is_file():
            raise ValueError("pinned native Flipper transport missing")
        sys.path.insert(0, str(scripts.resolve()))
        import flipper.storage as sdk
        verify_transport_origin(sdk.__file__, scripts)
        device = sdk.FlipperStorage(args.port)
        device.read = DeadlineRead(device.port, timeout_seconds=15.0)
        with device as client:
            report = read_only_audit(client, post, js)
    except Exception as exc:
        print("E11 CLI ECHO READ-ONLY NO-GO: " +
              (str(exc) if type(exc) is ValueError else type(exc).__name__),
              file=sys.stderr)
        print("STOP - NO RETRY, NO FAP WRITE, NO FILE DELETE OR RENAME", file=sys.stderr)
        return 1
    for key, value in report.items():
        print(key + ": " + value)
    print("E11 REAL DEVICE READ-ONLY CLI ECHO + OLD FAP / EMPTY STAGE PASS")
    print("NO STAGE UPLOAD OR FAP PROMOTION EXECUTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
