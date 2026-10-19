# LabMate v1.9 E11 — Activation decision after independent physical staging

**Date:** 2026-10-19  
**Branch/PR:** `dev/v1.9-logic-scope`, Draft PR #15.  
**Current real device status:** **v1.8 FINAL ACTIVE; v1.9 STAGED AND TWICE INDEPENDENTLY READ BACK.**  
**Activation permission:** **NOT GRANTED.** The previously granted one-time *stage-only* consent has been consumed. No rename, rollback, firmware flash, user-data write or Stable merge is authorized.

## Confirmed physical device evidence

Operator executed the once-authorized COM7 stage-only operation and the separate independent COM7 poststage read-only verification. Both PASS.

- Exact candidate `/ext/apps/Tools/labmate.v19-new-stage`: **97,540 bytes** SHA-256 `e1f43390c4078fbaad7e13124331926e0d6667294f2815e8b63762bd16f3ff90`, twice read back by each separate real-USB session.
- Active `/ext/apps/Tools/labmate.fap`: pinned v1.8 FINAL, **81,528 bytes**, SHA-256 of prior real COM7 readback `393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61`. Independent poststage device MD5/size PASS.
- Preserved existing historical `/ext/apps/Tools/labmate.e11-pre-final.bak`: read-only identity PASS.
- Future reserved v1.8 backup filename `/ext/apps/Tools/labmate.v18-final-before-v19.bak`: **ABSENT** in the independent poststage scan.
- PC-only fallbacks: actual live v1.8 FINAL FAP PC readback and historical E11 v1.8DEV FAP both hash-pinned; current LabMate data snapshot **12 files / 2,128 bytes**; not a full microSD backup, not proof of a successful restore.
- No v1.9 application activation, Flipper firmware update, device rename, or rollback has yet been performed.

## Native E11 SDK compatibility: evidence and the remaining hole

The pinned v1.9 build was compiled against the same **Momentum base** `d3f89dfe2ef6b01839201598e9be1590cba80322` plus documented E11 patches, matching the provenance established for the earlier custom E11 release.

The local build/review script `scripts/verify_v19_e11_sdk_fap.py` checks the patched SDK's `targets/f7/api_symbols.csv`, patched headers, code and ARM ELF header. Its required symbols are:

1. `furi_hal_resource_lease_try_acquire`
2. `furi_hal_resource_lease_release`
3. `furi_hal_gpio_try_add_int_callback`

The exact patched source-chain also explicitly inserts the third export (`scripts/patch_momentum_gpio_tryadd.py`), while the resource lease patch inserts the first two (`scripts/patch_momentum_resource_lease.py`). The v1.9 `src/labmate_scope_native.c` calls these APIs with a fail-closed compile-time header gate, but **compile-time matching does not detect a different installed binary at runtime**.

**Remaining gap:** Neither Momentum `device_info` nor the on-microSD JS plugins/Manifest MD5 proves the SHA256 or exported-symbol table of the firmware currently flashed inside the STM32. The earlier real v1.8 E11 execution supports that this is a paired custom-E11 firmware, but is not byte-exact proof of all three required v1.9 exports. No such independent installed-firmware image/export attestation has been produced. Do not mark native ABI VERIFIED or claim universal v1.9 compatibility.

## Promotion design: two separate non-atomic renames — NOT AUTHORIZED

Any future *single controlled activation attempt* must first use a **fresh read-only state classifier for the poststage state** (not the prewrite checker). It must abort if current v1.8, staged v1.9, old E11 backup, E11 native resources or empty new v1.8 backup name has drifted.

Only after a code review, offline fault-injection tests of the **actual** future activation implementation, clear residual-ABI-risk decision and separate explicit owner consent may the two target-limited SD renames be attempted:

1. `/ext/apps/Tools/labmate.fap` -> `/ext/apps/Tools/labmate.v18-final-before-v19.bak` (preserves exact final v1.8 device bytes).
2. `/ext/apps/Tools/labmate.v19-new-stage` -> `/ext/apps/Tools/labmate.fap`.

They are **not atomic together**. After step 1 and before step 2, the normal application filename is temporarily absent. Timeout, power loss, ambiguous CLI reply or any hash/status mismatch means STOP. The original E11 backup and CSV/Profiles must not be moved or modified. No implicit recovery or automatic rollback.

The activated state (if ever authorized and reached) requires a **new independent read-only three-path reconciliation** before even considering first GUI launch. The existing stage-only checker would no longer describe that state. A separate exact-state/manual v1.8 restoration procedure, requiring its own new authorization, must be reviewed and fail closed: a hypothetical restore cannot be asserted or executed from these successful simulations alone.

## Decision today

- **GO:** Retain v1.9 staged bytes, current v1.8 active, and work PC-only on the production activation/rollback review.
- **NO-GO:** Immediate device activation, automatic recovery, firmware flash or Main/Stable promotion. A proven staged FAP is **not** an approved activation.
- The operator may later expressly approve a bounded experimental v1.9 activation **after** understanding that firmware flash-image ABI attestation remains unavailable, or elect to hold v1.8 until stronger on-device firmware evidence can be obtained. Neither choice is implied by the prior stage-only approval.

No more staging or extra device-side writes are required to preserve today's PASS state.


## 2026-10-19 — one offline real-FAP activation and rollback rehearsal

Reviewed injection-only implementation added to the **draft** `dev/v1.9-logic-scope` branch:
- `scripts/review_v19_e11_activation_recovery_offline.py` uses the *same actual method-level* stat, MD5, full byte-readback and two protected rename command frames against the existing `FakeCLI` implementation, with all **three exact PC FAP** hashes. It checks the already-staged state twice, the intermediate missing-active state, and the promoted final state, never auto-retries, and refuses any previously occupied backup target. It models two separately manually requested recovery routes: restoring v1.8 after only the first activation rename, or preserving failed v1.9 and replacing it with the protected v1.8 file after activation.
- `tests/test_v19_e11_activation_recovery_real_fap_offline.py` contains **22 synthetic positive and negative tests**, including fault injection after first or second rename, corruption, unexpected source states, repeat attempts, resource/backup conflicts and no automatic recovery. **These 22 tests have NOT yet been operator executed and no PASS is asserted.**

Unlike earlier conceptual simulations, this rehearsal tests the reviewed rename orchestration function itself, including native-like response framing, and reads **full binary contents** at each important filesystem state. **But this is still a fake CLI, not an authenticated COM7 transport**, and its `main` cannot open COM nor write to disk. The real device state stays `STAGED_V19_NONAPP_ACTIVE_V18` with no v1.9 activation or firmware image attestation.

Next: user pulls development branch and runs one host test and one real-3-FAP offline replay. Only after actual PASS may a separate narrowly scoped activation command and independent post-activation read-only checker be prepared. Any on-device activation still requires a **new explicit owner authorization** and a reviewed mechanism to handle non-atomic gap without blindly retrying or automatically restoring.

```bash
python3 /mnt/c/Users/sehmu/labmate-src-v19/tests/test_v19_e11_activation_recovery_real_fap_offline.py -v
```

Then, after 22/22 PASS, run:

```bash
python3 /mnt/c/Users/sehmu/labmate-src-v19/scripts/review_v19_e11_activation_recovery_offline.py \
 --candidate /mnt/c/Users/sehmu/Documents/LabMate-FAP-PC-Backups/V19-WINDOWS-PC-CANDIDATE-3d66658-20261019/labmate-v1.9DEV-E11-WINDOWS-PC-ONLY.fap \
 --current-v18-pc-backup /mnt/c/Users/sehmu/Documents/LabMate-FAP-PC-Backups/V19-pretrial-live-v18-5e5cf7bc9ade41289c870ed156864482/installed_LabMate_v18_FINAL_E11_before_v19.fap \
 --legacy-e11-pc-backup /mnt/c/Users/sehmu/Documents/LabMate-FAP-PC-Backups/E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d/installed_E11_v18DEV_before_final_label.fap
```

The historical 36/36 v1.8 hardware checks, paired JS resource MD5, and pinned build SDK exports support the custom E11 pairing but do NOT certify that the currently flashed firmware image actually exports those symbols. The exact runtime ABI discrepancy remains unresolved and must be disclosed before any later activation consent.


## GitHub CI review gate — workflow defined, result pending

A branch-scoped `.github/workflows/check-v19-e11-activation-rollback-offline.yml` now exercises the 22 new activation/manual rollback fault-injection cases plus existing native CLI and virtual FAP-swap tests on GitHub-hosted Linux. The workflow has **no access to COM7 or Flipper**, uses no firmware updater, performs no stage/rename and has read-only repository token permission. **No independent CI run conclusion has been obtained yet; do not claim CI PASS.** The actual operator host suite and real-three-FAP replay are also pending, so activation is not ready. The public Stable and Draft PR state are unchanged.


## Actual operator three-FAP offline promotion and manual recovery PASS; one mock test expectation corrected

The operator executed `tests/test_v19_e11_activation_recovery_real_fap_offline.py -v` on the local repo and observed **21/22 PASS, one failure**: `test_unexpected_stat_echo_aborts_before_rename` expected error text `stat echo`, but the fake native transport itself first raises `ValueError: simulated CLI command echo disagreement`. The code correctly aborted before any rename. **No device-writing activation was attempted**.

The operator separately ran the rehearsal against the **actual three pinned Windows PC FAP files**:

```text
V19 E11 ACTUAL RENAME ORCHESTRATION - THREE REAL FAPS, IN MEMORY ONLY
OFFLINE_V19_PROMOTION: PASS_TWO_RENAMES
OFFLINE_MANUAL_V18_ROLLBACK: PASS_V19_PRESERVED
OFFLINE_MANUAL_INTERRUPTION_RECOVERY: PASS_V18_ACTIVE_AND_V19_STAGED
USB_CALLS: ZERO | DEVICE_WRITES: ZERO | PC_WRITES: ZERO
REAL V1.9 ACTIVATION: NOT AUTHORIZED | FIRMWARE ABI: NOT_ATTESTED
```

This is operator-proven **in-memory real-artifact** success only; not a live rename/rollback or a firmware compatibility attestation.

In commit `ec2fc7a3accb01f318a04ee709d63988519b9757`, only the **test** was corrected to require the actual lower-level transport error and additionally require **zero renames, zero binary chunks, one read-only stat attempt, and unchanged active v1.8/staged v1.9/legacy backup bytes**. No application, fake native CLI, or real-device writer implementation was changed. The revised **22/22 test result is PENDING** until the operator reruns it.

Until then and until a reviewed explicit activation grant, retain the real device in the currently independently verified `STAGED_V19_NONAPP_ACTIVE_V18` state. No more `-ApplyStageOnly`, no on-device rename/restore/flash/retry.


## 2026-10-19 — operator confirms corrected 22/22 offline fault cases PASS

The operator pulled `dev/v1.9-logic-scope` from `766a100` to `aafb860`, then actually reran `tests/test_v19_e11_activation_recovery_real_fap_offline.py -v` with **all 22 tests PASS**, `Ran 22 tests in 0.007s`, `OK`. The previously reported real-three-PC-FAP in-memory activation + manual rollback + interrupted first-rename recovery rehearsal also PASS. The 22/22 result closes **host-only** behavior checking of the current fake CLI and reviewed in-memory transition function. It does **not** authenticate the STM32 installed firmware ABI, does not prove a live rename/restore, and does not authorize activation. The real v1.9 FAP stays staged, with final v1.8 still active. Next work: review a separately constrained real COM7 activation adapter and independent post-activation state checker, fully offline tested, with explicit separate activation permission before first actual mutation.
