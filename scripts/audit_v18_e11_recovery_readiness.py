#!/usr/bin/env python3
"""Offline E11 recovery equivalence / trial decision audit, NO FLASH.

Facts used here are recorded operator observations and independent local
artifact checks. This program cannot interrogate a device or prove recovery.
It deliberately never prints GO or authorizes a firmware/FAP installation.
A matching nominal firmware branch/source prefix is NOT full image identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from preflight_v18_e11_local import (
    INSTALLED_EXITFIX, ROLLBACK, ARTIFACTS
)
from check_v18_full_vs_mntm012 import OFFICIAL_MNTM012_SHA256

SUPPORTED_BASE = "d3f89dfe2ef6b01839201598e9be1590cba80322"
RECORDED_CHANNEL = "mntm-dev"
RECORD_DIRTY = True
RECORDED_API = "87.1"
RECORDED_INSTALLED_IMAGE_SHA256 = None  # not measured through trusted full firmware readback
OFFICIAL_FALLBACK_RELEASE = "mntm-012"
CANDIDATE_LABEL = "DO NOT FLASH"
PROTECTED_LABMATE_COPIES = (14, 10)


@dataclass(frozen=True)
class Evidence:
    installed_channel: str
    current_base_commit: str
    current_dirty: bool
    current_api: str
    installed_firmware_sha256: str | None
    firmware_recovery_target: str
    rollback_tgz_sha256: str
    installed_fap_sha256: str
    preserved_fap_copy_sha256: str
    available_stable_fap_sha256: str
    candidate_fap_sha256: str
    candidate_label: str
    historical_labmate_backup_files: int
    current_labmate_snapshot_files: int
    whole_sd_preserved: bool
    rollback_boot_rehearsed: bool
    explicit_new_trial_authorized: bool


def recorded_evidence() -> Evidence:
    """Only documented evidence, not a new measurement or current promise."""
    return Evidence(
        installed_channel=RECORDED_CHANNEL,
        current_base_commit=SUPPORTED_BASE,
        current_dirty=RECORD_DIRTY,
        current_api=RECORDED_API,
        installed_firmware_sha256=RECORDED_INSTALLED_IMAGE_SHA256,
        firmware_recovery_target=OFFICIAL_FALLBACK_RELEASE,
        rollback_tgz_sha256=ROLLBACK["flipper-z-f7-update-mntm-012.tgz"],
        installed_fap_sha256=INSTALLED_EXITFIX,
        preserved_fap_copy_sha256=INSTALLED_EXITFIX,
        available_stable_fap_sha256=ROLLBACK["labmate-v18-stable.fap"],
        candidate_fap_sha256=ARTIFACTS["labmate.fap"],
        candidate_label=CANDIDATE_LABEL,
        historical_labmate_backup_files=PROTECTED_LABMATE_COPIES[0],
        current_labmate_snapshot_files=PROTECTED_LABMATE_COPIES[1],
        whole_sd_preserved=False,
        rollback_boot_rehearsed=False,
        explicit_new_trial_authorized=False,
    )


def _hex(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def audit(e: Evidence) -> dict[str, str]:
    for fingerprint in (
        e.rollback_tgz_sha256, e.installed_fap_sha256,
        e.preserved_fap_copy_sha256, e.available_stable_fap_sha256,
        e.candidate_fap_sha256
    ):
        if not _hex(fingerprint):
            raise ValueError("missing or invalid SHA256 evidence")
    if e.installed_firmware_sha256 is not None and not _hex(e.installed_firmware_sha256):
        raise ValueError("unusable installed firmware image hash")
    if len(e.current_base_commit) != 40 or any(
        c not in "0123456789abcdef" for c in e.current_base_commit
    ):
        raise ValueError("invalid nominal current base commit")
    if e.rollback_tgz_sha256 != OFFICIAL_MNTM012_SHA256:
        raise ValueError("rollback package is not independently pinned official 012")
    if e.candidate_label != CANDIDATE_LABEL:
        raise ValueError("candidate is not explicitly blocked for physical install")
    if not e.installed_channel or not e.firmware_recovery_target:
        raise ValueError("missing device/recovery channel identity")
    if e.historical_labmate_backup_files < 1 or e.current_labmate_snapshot_files < 1:
        raise ValueError("missing both LabMate PC states")

    # Distinguish checked artifact bytes from a restored running image.
    current_firmware_exact = "NOT_PROVEN"
    reason = "NO_TRUSTED_FULL_INSTALLED_IMAGE_SHA256"
    if e.installed_firmware_sha256 is not None:
        # We have no exact prior-image DFU/restore hash pinned here.
        # Even source/base equality isn't byte-identity after dirty patches.
        reason = "PRIOR_FULL_RESTORABLE_FW_IMAGE_NOT_INDEPENDENTLY_VERIFIED"

    same_channel = e.installed_channel.casefold() == e.firmware_recovery_target.casefold()
    # Even a nominal channel match is NOT proof of exact image bytes.
    nominal_mismatch = not same_channel or e.current_dirty
    exact_fap = e.installed_fap_sha256 == e.preserved_fap_copy_sha256
    stable_is_same = e.installed_fap_sha256 == e.available_stable_fap_sha256
    candidate_is_same = e.installed_fap_sha256 == e.candidate_fap_sha256

    return {
        "observed_current_firmware": e.installed_channel,
        "observed_dirty_source": "YES" if e.current_dirty else "NO",
        "observed_firmware_api": e.current_api,
        "official_fallback_release": e.firmware_recovery_target,
        "official_rollback_archive_sha256_pinned": "YES",
        "nominal_channel_or_dirty_mismatch": "YES" if nominal_mismatch else "NO",
        "exact_prior_firmware_recovery": current_firmware_exact,
        "exact_prior_firmware_blocker": reason,
        "known_official_release_fallback": "FILE_VERIFIED_BOOT_UNTESTED",
        "preserved_current_exitfix_fap_identity": "MATCH" if exact_fap else "MISMATCH",
        "stable_fap_is_current_exitfix": "YES" if stable_is_same else "NO",
        "candidate_fap_is_current_exitfix": "YES" if candidate_is_same else "NO",
        "labmate_historical_and_current_pc_copies": "PRESERVED" if (
            e.historical_labmate_backup_files > 0 and e.current_labmate_snapshot_files > 0
        ) else "NOT_PROVEN",
        "whole_sd_contents_preserved": "YES" if e.whole_sd_preserved else "NO_OPTIONAL",
        "rollback_boot_on_device_rehearsed": "YES" if e.rollback_boot_rehearsed else "NO",
        "new_trial_owner_permission": "YES" if e.explicit_new_trial_authorized else "NO",
        "firmware_trial_decision": "NO_GO",
        "device_changes_performed": "NO",
    }


def main() -> int:
    report = audit(recorded_evidence())
    for k, value in report.items():
        print(f"{k}: {value}")
    print("E11 OFFLINE RECOVERY EQUIVALENCE AUDIT PASS - TRIAL NO-GO")
    print("An old signed/hashed updater is not a demonstrated exact prior-device restore.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
