# LabMate v1.8 E11 — Installation route safety decision

**Decision date:** 2026-10-17. **Actual Flipper not modified.**
**Status: NO-GO for any firmware installation.** This is an
evidence-based *selection/engineering review*, NOT an installer.

## One verified current-device fact changes the plan

After preserving the user's 14 historical and 10 current LabMate
data files in separate PC copies, the user ran the real USB
read-only `/ext/Manifest` audit with pinned Momentum CLI:
`old_manifest_resource_files=2114`,
`old_manifest_directories=165`, `manifest_total_records=2281`,
`old_cleanup_lists_installed_labmate_fap=YES`,
`old_cleanup_labmate_data_files=0`,
`old_cleanup_non_labmate_apps_data_files=156`,
`old_cleanup_app_fap_files=268`, and
`live_manifest_readback_md5_screen=MATCH`.
This is a real readback MD5 consistency-screened user report;
it is not a signed or independently archived full Manifest image.
Source: [operator count-only evidence](evidence/V1_8_E11_LIVE_OLD_MANIFEST_OPERATOR_2026-10-17.txt).

A separate static verification of pinned native Momentum firmware
`applications/system/updater/util/update_task_worker_backup.c`
confirms that when a resource update executes, the updater reads the
**old** `/ext/Manifest`, attempts removal of the listed files and
then extracts the **new** `resources.tar.gz`.
Resource FILE entries are removed by path without checking whether
the actual installed FAP was modified manually. Therefore the
current EXITFIX app (`/ext/apps/Tools/labmate.fap`) is **in the
scope of removal by the updater's old-resource cleanup**. It has
**not** actually been removed.

## Alternatives compared before any physical trial

| Route | Outcome if its relevant stages execute | Decision |
| --- | --- | --- |
| Existing *split* E11 review bundle, excludes NEW LabMate FAP but retains update resources | OLD Manifest includes LabMate FAP so it is targeted for removal; NEW archive does not restore any LabMate FAP. Could leave LabMate absent after update. | **REJECTED as EXITFIX-preserving trial. DO NOT FLASH.** |
| Existing *original full* E11 updater with NEW LabMate FAP embedded | OLD cleanup targets EXITFIX; NEW resources include a distinct E11 app. Original installed working FAP should not be assumed preserved. New FAP/new firmware/native coexistence and full boot have not been tested. | **NO-GO pending explicit future authorization and real safety review.** |
| Speculative firmware-only updater without resource phase | Might avoid old resource cleanup, but unmodified existing resources/FAP may be ABI- or firmware-service-incompatible. No approved firmware-only package or device boot validation exists. | **NOT DEVELOPED/NOT APPROVED.** |
| FAP-only test against current installed dirty firmware | Cannot verify newly patched firmware-level lease coordination because new native firmware is not installed. | **Insufficient for E11 native resource acceptance.** |
| Continue GitHub-based static/C/model/CI tests | No firmware/device writes, can test source behavior and refine trial design. | **ALLOWED; current active path.** |

The 156 other app-data FILE manifest entries are not proof that
user files are deleted now. `old_cleanup_labmate_data_files=0`
means the old *resource-manifest removal list* contains zero LabMate
persistent-data paths; it is **not a universal storage guarantee**.
The owner has called non-LabMate SD data low-priority, but that
does not authorize deletion or installation.

## Tooling/release guardrails

- [Offline, count-only split NO-GO gate](../scripts/check_v18_e11_split_trial_gate.py)
  consumes the operator's anonymized real-device summary and asserts
  complete metadata, consistent totals, existing-old LabMate FAP
  entry and unapproved installation status. It always emits either
  `REJECTED_OLD_MANIFEST_WOULD_REMOVE_INSTALLED_FAP` or a
  separate fail-closed `NOT_PROVEN_SAFE_DO_NOT_USE_AS_TRIAL`.
  Never a GO.
- [8 negative/positive policy tests](../tests/test_v18_e11_split_trial_gate.py)
  check malformed input, record count tampering, forged approval
  and even a hypothetical old Manifest not listing the LabMate FAP.
- New future PC-only derivative stages now include an explicit
  warning in READ_ME_FIRST that existing EXITFIX is listed by
  the LIVE old Manifest and the split archive is **rejected** as an
  EXITFIX-preserving trial. Previously generated binary review
  files remain immutable and still carry **DO NOT FLASH**.
- [CI #38983595126](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38983595126)
  **SUCCESS**, including source-cleanup, serial old-Manifest,
  split policy and derivation warning tests. Actual output:
  `split_review_as_exitfix_preserving_trial:
  REJECTED_OLD_MANIFEST_WOULD_REMOVE_INSTALLED_FAP`;
  `firmware_trial_authorized: NO`.
- [v1.8 integrated host #38983566497](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38983566497)
  **SUCCESS**, including new fail-closed trial gate.

## What remains open before an experimental new-firmware trial

The next eligible *planning* action is to design a **new, mutually
consistent firmware + FAP + resource** trial and a truly understood
rollback path, not reuse either available experimental review
archive. Requirements include evidence of compatible matching
native lease APIs, expected app presence after resource cleanup,
manifest/resource preservation policy, confirmation of USB/power
and isolation of GPIO accessories, and separately requested
owner consent to the **specific** selected firmware write.

The old official Momentum MNTM-012 updater is a verified file
but not an exact byte-for-byte recovery of the currently installed
custom `mntm-dev dirty=true` firmware. The actual EXITFIX FAP
has a readback SHA256 and retained copy; older Stable FAP is
different. Restoring firmware or pressing qFlipper repair has
not been rehearsed and might erase internal settings.

The real native E11 GPIO/TIM1/TIM2/EXTI lease, refusal,
STOP/BACK, return and re-entry physical tests necessarily wait
until a separately approved **safe** matched native trial.
Unavailable external test fixtures remain explicitly DEFERRED,
not a manufactured hardware PASS.

**Current release state: draft PR #13, main/Stable untouched,
working EXITFIX installed, no firmware flash, no restore,
no SD modification, v1.9 not yet started.**


## 2026-10-17 — Packed NEW resource Manifest validated: FAP-SPLIT has stale FAP reference

After the earlier real-device old-resource Manifest confirmed
`apps/Tools/labmate.fap` is in the CLEANUP list,
a new [actual E11 packed resources
comparison](V1_8_E11_PACKED_MANIFEST_VERIFICATION_2026-10-17.md)
checked separately pinned original FULL and FAP-excluded derivative
`resources.tar.gz` binaries against their OWN embedded
`Manifest` MD5 and byte-size records.

**Original FULL archive:** 2,115 resource files (not counting
Manifest); 2,114 correctly declared resource records,
`dolphin/firstboot.bin` is the only explicitly accepted
Momentum-generated file outside the Manifest; **0 mismatched
MD5/size records, 0 missing declared files**, E11 FAP and native
JS binary SHA256 match independently pinned review files.
This is PACKAGING PASS, NOT firmware/device acceptance.

**FAP-separated derivative:** 2,114 resource files (excluding
Manifest), but the unchanged new Manifest still declares
2,114 files INCLUDING the now-absent LabMate FAP:
**exactly one declared orphan, the removed E11 LabMate FAP**.
That is a SECOND independent reason for `SPLIT_TRIAL=REJECTED`
beyond the actual installed old Manifest targeting EXITFIX for
deletion. Do not repack/retag this derivative as a functional
installer. Original FULL also remains NO-GO pending firmware
recovery/native device trials and explicit owner install permission.

Test evidence: [full actual archive reconciliation
#38984202194](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38984202194)
**SUCCESS**; [native integrated
#38984217069](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38984217069)
**SUCCESS**. The risk workflow has been changed not to
upload fresh downloadable binaries for the known-rejected
SPLIT derivative. Source provenance, external accessories,
device/SD and working EXITFIX all remain untouched.
