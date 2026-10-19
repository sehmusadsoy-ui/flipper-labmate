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
