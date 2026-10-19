#!/usr/bin/env python3
"""Review-only E11 v1.9 activation adapter -- REAL SD RENAMES if separately authorized.

**NOT authorized by source being present.** Operator's prior consent covers
ONLY the completed, new non-.fap stage file. Activation must have an entirely
NEW, express approval after independent host tests and recognition that the
exact STM32-flashed firmware export ABI is NOT attested.

The only DEVICE MUTATIONS in this program are two same-directory, non-atomic
storage renames after byte-exact state attestation:
 /ext/apps/Tools/labmate.fap         -> labmate.v18-final-before-v19.bak
 /ext/apps/Tools/labmate.v19-new-stage -> labmate.fap
No retry/rollback, cleanup, firmware flash, app boot or LabMate data writes.
Any interrupted/ambiguous first rename may leave labmate.fap temporarily
ABSENT. STOP, preserve device state; use a separately approved READ-ONLY
classifier, never rerun this adapter.

Use the pin-checked Windows runner only, after separate activation approval.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
import sys

from audit_v18_e11_live_labmate_sd import DeadlineRead, verify_transport_origin
from backup_v19_active_v18_fap_ro import check_local
from check_v18_e11_phase2b_state_readonly import ABSENT
from check_v18_e11_postupdate_readonly import EXPECTED_BASE, EXPECTED_FIRMWARE_LABEL
from check_v19_e11_staged_device_ro import attest_poststage, verified_candidate
from prepare_v19_e11_pc_only import verify_backups
from review_v19_e11_activation_recovery_offline import (
    ACTIVE, NEW, CURRENT_BACKUP, LEGACY_BACKUP, FAILED_V19_BACKUP,
    FORWARD, rename_once, state_staged, state_between, state_activated,
)
from simulate_v19_e11_fap_swap_offline import V18_SIZE, V18_SHA, LEGACY_SIZE, LEGACY_SHA
from check_v18_e11_h_js_runtime_ro import REMOTE as JS_REMOTE

AUTH = "I_EXPLICITLY_APPROVE_V19_TWO_NONATOMIC_RENAMES_ONLY"
ABI_RISK = "I_ACCEPT_E11_INSTALLED_FIRMWARE_BINARY_ABI_NOT_ATTESTED"
# Keys MUST match the actual 'js' dict returned by check_local() /
# pinned_local_expectation(). 'E11_JS_GPIO' belongs to 'post', NOT 'js'.
PINNED_NATIVE = {
    "/ext/apps_data/js_app/plugins/js_gpio.fal": "js_gpio.module",
    "/ext/apps_data/js_app/plugins/js_event_loop.fal": "event_loop",
}
MD5_HEX = re.compile(r"[a-f0-9]{32}\Z")


def verified_pc(path: Path, size: int, sha: str) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size != size:
        raise ValueError("required pinned PC FAP missing or wrong size")
    b = path.read_bytes()
    if len(b) != size or hashlib.sha256(b).hexdigest() != sha:
        raise ValueError("required pinned PC FAP changed")
    return b


def identity_resources_ro(client, post: dict, js: dict) -> None:
    """Old E11 native-label/resources checked even between two renames."""
    cmd = "device_info"
    if client.send_and_wait_eol(cmd + "\r") != cmd.encode("ascii"):
        raise ValueError("unexpected device_info CLI echo")
    identity = client.read.until(client.CLI_PROMPT)
    if not isinstance(identity, bytes) or not 1 <= len(identity) <= 131072:
        raise ValueError("unrecognized current E11 identity")
    lower = identity.decode("utf-8", errors="strict").lower()
    if EXPECTED_FIRMWARE_LABEL not in lower or EXPECTED_BASE not in lower:
        raise ValueError("installed E11 native firmware label/base drift")
    for remote, key in PINNED_NATIVE.items():
        if JS_REMOTE.get(key) != remote:
            raise ValueError("original JS plugin paths changed")
        expected = js.get(key)
        if not isinstance(expected, str) or MD5_HEX.fullmatch(expected.lower()) is None:
            raise ValueError("missing/malformed pinned E11 JS resource entry: " + key)
        digest = client.hash_flipper(remote)
        if (not isinstance(digest, str) or MD5_HEX.fullmatch(digest.strip().lower()) is None or
                digest.strip().lower() != expected.lower()):
            raise ValueError("installed E11 native resource MD5 changed")
    expected_manifest = post.get("E11_NEW_MANIFEST")
    if not isinstance(expected_manifest, str) or MD5_HEX.fullmatch(expected_manifest.lower()) is None:
        raise ValueError("missing/malformed pinned E11 resource Manifest identity")
    manifest = client.hash_flipper("/ext/Manifest")
    if (not isinstance(manifest, str) or MD5_HEX.fullmatch(manifest.strip().lower()) is None or
            manifest.strip().lower() != expected_manifest.lower()):
        raise ValueError("installed E11 Manifest MD5 changed")


def activate_on_client_once(client, v19: bytes, v18: bytes, legacy: bytes,
                            post: dict, js: dict, v18_md5: str) -> dict:
    """Production activation path is independently host testable with FakeCLI."""
    # One fresh, same-session read-only scan of stage, v1.8, firmware resources
    # and historically preserved backup BEFORE ANY filesystem mutation.
    verification = attest_poststage(client, post, js, v18_md5, v19)
    if verification.get("state") != "STAGED_V19_NONAPP_ACTIVE_V18":
        raise ValueError("pre-activation state not explicitly expected")
    state_staged(client, v19, v18, legacy)  # full FAP reads and every free-name gate
    identity_resources_ro(client, post, js)
    state_staged(client, v19, v18, legacy)  # second full screen immediately before first move

    # NO write if above checks fail. No permission to rollback or retry here.
    rename_once(client, ACTIVE, CURRENT_BACKUP, FORWARD)
    state_between(client, v19, v18, legacy)  # full all-FAP readback + empty active path
    identity_resources_ro(client, post, js)
    rename_once(client, NEW, ACTIVE, FORWARD)
    state_activated(client, v19, v18, legacy)  # full all-FAP readback + old backups
    identity_resources_ro(client, post, js)
    state_activated(client, v19, v18, legacy)
    return {
        "v19_file_promotion": "PASS_TWO_NONATOMIC_RENAMES",
        "installed_app": "V19_SHA256_FULL_READBACK",
        "preserved_final_v18": "V18_BAK_FULL_READBACK",
        "original_e11_backup": "UNCHANGED_FULL_READBACK",
        "stage_path": "ABSENT",
        "other_files_user_data": "NOT_ACCESSED",
        "firmware_flash": "NO",
        "gui_boot": "NOT_TESTED",
        "installed_firmware_binary_abi": "NOT_ATTESTED",
        "next_action": "STOP_FOR_INDEPENDENT_READ_ONLY_ACTIVATED_STATE_SCAN",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", required=True)
    ap.add_argument("--momentum-scripts", required=True, type=Path)
    ap.add_argument("--old-candidate", required=True, type=Path)
    ap.add_argument("--saved-old-fap-backup", required=True, type=Path)
    ap.add_argument("--final-v18-fap", required=True, type=Path)
    ap.add_argument("--active-v18-backup", required=True, type=Path)
    ap.add_argument("--data-snapshot", required=True, type=Path)
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--approve-two-renames", required=True)
    ap.add_argument("--accept-unverified-abi-risk", required=True)
    args = ap.parse_args()
    print("V19 E11 REAL TWO-RENAME ACTIVATION REVIEW ADAPTER - NO AUTORETRY")
    print("CAUTION: a failure can leave the active LabMate FAP pathname absent!")
    try:
        # Verify new, independent, exact-scope authorization BEFORE touching COM.
        if (args.approve_two_renames != AUTH or
                args.accept_unverified_abi_risk != ABI_RISK):
            raise ValueError("new exact activation and explicit ABI risk consent required")
        if args.port != "COM7":
            raise ValueError("wrong fixed COM port")
        n, size = verify_backups(
            args.active_v18_backup, args.saved_old_fap_backup, args.data_snapshot
        )
        if (n, size) != (12, 2128):
            raise ValueError("pinned LabMate backup snapshot mismatch")
        post, js, v18_md5 = check_local(
            args.final_v18_fap, args.saved_old_fap_backup, args.old_candidate
        )
        v19 = verified_candidate(args.candidate)
        v18 = verified_pc(args.active_v18_backup /
            "installed_LabMate_v18_FINAL_E11_before_v19.fap", V18_SIZE, V18_SHA)
        legacy = verified_pc(args.saved_old_fap_backup /
            "installed_E11_v18DEV_before_final_label.fap", LEGACY_SIZE, LEGACY_SHA)
        root = args.momentum_scripts
        library = root / "flipper" / "storage.py"
        if root.is_symlink() or library.is_symlink() or not library.is_file():
            raise ValueError("pinned native CLI source unavailable")
        sys.path.insert(0, str(root.resolve()))
        import flipper.storage as sdk
        verify_transport_origin(sdk.__file__, root)
        device = sdk.FlipperStorage(args.port)
        device.read = DeadlineRead(device.port, timeout_seconds=40)
        with device as client:
            report = activate_on_client_once(client, v19, v18, legacy,
                                             post, js, v18_md5)
    except Exception as exc:
        message = str(exc) if type(exc) is ValueError else type(exc).__name__
        print("V19 E11 ACTIVATE NO-GO: " + message, file=sys.stderr)
        print("STOP. DO NOT RERUN, CLEAN, RENAME, ROLLBACK OR FLASH.", file=sys.stderr)
        print("The installed app may be ABSENT or already changed. Do not infer state.", file=sys.stderr)
        return 1
    for key, value in report.items():
        print(key + ": " + str(value))
    print("STOP: independent post-activation READ-ONLY classifier required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
