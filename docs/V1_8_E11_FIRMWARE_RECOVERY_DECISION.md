# LabMate v1.8 E11 — Firmware identity, fallback and recovery DECISION

**Status 2026-10-17:** read-only identity/risk audit **PASS (decision NO-GO)**.
NO firmware was flashed, FAP installed, Flipper reset, recovery entered,
private SD directory modified or rollback rehearsed by this change.

This memo is for planning; it is **not an executable repair procedure**.
The developer's installed and working EXITFIX app + running custom Momentum
firmware are preserved. PR #13 remains draft, Stable/main unmodified.

## Distinguish the three firmware/application identities

| Evidence | Value | What is actually supported |
| --- | --- | --- |
| Running Flipper firmware reported via real COM7 | `mntm-dev` base abbreviated `d3f89dfe`, dirty=true; API 87.1 | Development build; neither complete firmware image SHA nor full applied patch set independently read back |
| OFFLINE fallback updater | Official Momentum release `mntm-012`; exact known TGZ SHA256 `1d9e1e600c8680172ff6f6913ca0b12484e7d45adbc72a66552e534784c8c1a7` | Independently pinned local file; **not** proven able to restore exact running `mntm-dev` bytes, patch state or custom ABI |
| Working app currently installed | EXITFIX FAP; actual on-device readback SHA256 `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be` | Previous installed app identity **proven** and a matching PC copy preserved |
| Historical Stable app fallback | `labmate-v18-stable.fap` SHA256 `119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0` | Verified separate *older app*, **not the working EXITFIX binary** |
| New E11 candidate FAP | `labmate.fap` SHA256 `2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0` | Matched with E11 patched candidate, **uninstalled**, cannot borrow E1–E9 hardware PASS |
| E11 FAP-separated package | `v18E11-SPLIT-REVIEW-DO-NOT-FLASH` | Single resource path removed and independently audited, but physical boot/order and rollback NOT accepted |

**Observed risk:** The official `mntm-012` release may be useful as a
fallback to a published firmware, but it is NOT a demonstrated
**byte-for-byte restoration of the current dirty `mntm-dev` build**.
The current firmware cannot be declared exact-restorable just because
the Git commit prefix matches the E11 build base or the official
fallback package has a valid SHA256. Changing the FAP to an older
Stable build likewise would not recreate current EXITFIX byte state.
The dedicated EXITFIX readback copy does preserve that application's
bytes, but its compatibility with a different rollback firmware
must be assessed separately.

## Recovery modes must not be confused with backups

Official Flipper Zero recovery instructions:
https://docs.flipper.net/zero/basics/firmware-update/firmware-recovery

The manufacturer documents recovery via the built-in USB DFU
bootloader and qFlipper when firmware is corrupt. **Important: an
actual qFlipper firmware REPAIR can erase internal storage, including
settings and paired-device information; the microSD files are
typically preserved.** This can result in losing current internal
state even if the device boots afterwards. The local settings
archive has been verified as readable; **restoring it has not
been tested**. DFU availability does not equal guaranteed safe
rollback and is NOT a reason to execute Repair now.

Two distinct possible outcomes of a future *separately approved*
recovery attempt must be explained to the operator:

1. **Official-release fallback:** restoring `mntm-012` may get the
   device onto a known release, but current custom patched firmware
   identity, plugin APIs, settings and app compatibility may change.
2. **Exact pre-trial state restore:** requires an independently
   authenticated/restorable prior custom firmware image and a tested
   recovery method compatible with that specific device. **NOT
   ESTABLISHED**. Do not claim this can be achieved with official
   `mntm-012` or by reusing a DFU from a different E11 candidate.

A rollback update, DFU repair, factory reset, FAP overwrite,
settings restore or SD resource synchronization is a DEVICE WRITE
and needs a **separate, explicit owner decision** with a pre-reviewed
package/procedure. The current instruction is not to perform any
such operation.

## Existing backup and hardware evidence

- **Current LabMate directory PC copy: PASS** from real COM7
  read-only USB transfer: 10 files, 1,791 bytes, each MD5 screened
  against device and local SHA256 after write.
- **Older LabMate directory: preserved** separately as a 14-file
  historical PC copy. Different sets are expected: 9 older-only
  paths, 5 newer-only paths, 2 changed versions. Nothing restored.
- **qFlipper internal-settings TGZ:** 14 files + 1 directory,
  known SHA256. **Never tested by restoring to the device.**
- **Other SD content:** 57 non-LabMate app-data directories found
  on the real Flipper, not fully copied. Owner has said these
  additional data are low-priority. A full USB file backup is
  available as an **optional** precaution and is not a blocker for
  offline E11 development. This is not permission to erase the SD.
- Existing EXITFIX E1–E9 physical reports are for an EARLIER app
  and cannot be attributed to E11 full firmware/FAP pair.

## Fail-closed check wired to CI

[`scripts/audit_v18_e11_recovery_readiness.py`](../scripts/audit_v18_e11_recovery_readiness.py)
uses pinned provenance and **recorded** device observations.
It separates:
- official fallback file SHA evidence from **actual boot/restore**;
- installed custom `mntm-dev dirty` identity from nominal release;
- copied current EXITFIX FAP from older Stable and uninstalled E11 FAP;
- optional whole-SD protection from **mandatory firmware trial**
  and recovery safety review.

Its output is **`E11 OFFLINE RECOVERY EQUIVALENCE AUDIT PASS -
TRIAL NO-GO`**: PASS means the risk assessment didn't accidentally
claim an equivalence. It **does not** mean an installation/recovery
procedure has passed. There is deliberately NO automatic firmware
writer, release approval or rollback trigger.

**CI at 2026-10-17:**
- [Native host combined regression #38981611042](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38981611042) **SUCCESS**, includes 13 synthetic recovery-equivalence tests.
- [Exact package comparison #38981663476](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38981663476) **SUCCESS**; pinned official MNTM-012 vs new E11 package, unchanged official RADIO and option-byte policies, original + FAP-excluded review resource integrity.

## What is next (and what is not allowed yet)

**Finished without any device write:** current LabMate snapshots,
static FAP separation, official-vs-E11 radio/option-byte comparison,
a separately reviewed qFlipper/DFU recovery path and exact-state
identity gap identification.

**Still OPEN:** (a) physical boot/recovery rehearsal on an appropriate
device or separately approved non-destructive trial plan, (b)
prior custom firmware image equivalence/compatibility recovery
decision, (c) explicit approval for any future specific write
procedure and package, (d) real E11 GPIO/TIM1/TIM2/EXTI coexistence
and STOP/BACK/reacquisition tests, and (e) fixture-dependent
measurements from `DEFERRED_HARDWARE_TESTS.md`.

**Release decision: E11 TRIAL NO-GO; no Stable merge.**
