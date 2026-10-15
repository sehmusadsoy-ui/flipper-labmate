# v1.8 E11 — Firmware-Global Resource Lease Contract (DESIGN ONLY)

**Branch:** `dev/v1.8-completion` / Draft PR #13.
**Pinned, already installed firmware source:** Momentum
`d3f89dfe2ef6b01839201598e9be1590cba80322`.
**Installed LabMate EXITFIX FAP SHA256:**
`7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`.
**Approval state:** NO new firmware/FAP/USB install; NO v1.8 Stable approval.

## Why application-local ownership is insufficient

`LabMateCaptureOwner` and `LabMateCommOwner` reject overlaps **inside
LabMate**. A separate Momentum app/service can still use a timer, GPIO,
EXTI callback or PWM without consulting these variables.

Read-only review of the actual pinned firmware identified:
- `furi_hal_bus_enable(TIM1/TIM2)` checks (and asserts) that the
  peripheral is disabled, rather than returning a recoverable owner
  claim. A momentary `furi_hal_bus_is_enabled` check would introduce
  a time-of-check/time-of-use race; it is NOT a global lease.
- `furi_hal_gpio_add_int_callback` asserts that the chosen EXTI
  callback slot is empty. This is NOT a nonfatal try-add API.
- `furi_hal_pwm_start` and LabMate's direct TIM2 setup configure
  peripheral registers. `furi_hal_gpio_init_simple` reconfigures
  pins. Each can affect an unrelated prior owner if ownership is not
  jointly enforced.

This is a **source-level identified risk**, not a reproduced crash.
The completed EXITFIX E1–E9 physical tests show safe behavior under
the observed ordinary, noncompeting conditions, not general concurrency.

## Proposed firmware contract (NOT YET IMPLEMENTED)

A correct cross-firmware solution must be installed **inside the exact
firmware**, before any component configures a shared resource. Merely
adding a second LabMate-local mask, or checking a clock/callback state
before a call, is not sufficient.

1. Expose a versioned, firmware-owned and atomically enforced
   `try_claim(owner_handle, resource_mask)` with a stable FAP ABI.
   Lock the shared state in a short RTOS critical section, **not**
   across device operations or a long wait. Fail without any register,
   pin mode or callback mutation on conflict. Unsupported SDKs must
   fail closed; do not fall back to unsafe direct HAL access.
2. Alias each physical resource to the SAME underlying lease:
   TIM1+PA7 (PWM), TIM2+PB3 (counter/HIGH frequency),
   EXTI line+physical pin (PC0/PC1/PB2/PA4), I2C3+PC0+PC1,
   and PA4 for 1-Wire. Shared EXTI lines must respect MCU
   line-number sharing across GPIO ports. Claims that touch
   multiple resources are ALL-OR-NOTHING.
3. Only the matching **unique, versioned owner handle** may release
   its exact acquisition. A wrong owner, double release, partial
   release, stale handle or failed acquisition must not disable a
   peripheral, reset a pin, or remove a callback owned by someone
   else. Establish a defined lifecycle for abnormal app termination.
4. Integrate the contract into **all relevant firmware HAL entry
   paths and other firmware services**, not only LabMate; audit
   timer/GPIO/EXTI/I2C/PWM owners and any direct LL register writes.
   A bypassing legacy service is an outstanding blocker, not a
   protected service. Coordinate with existing external-I2C firmware
   mutex; do not introduce an independent competing I2C lock.
5. Design hardening and ABI checks must preserve the exact patched
   Momentum build's radio/option-byte semantics and original tools.
   No firmware patch may be deployed without a new pinned
   firmware+FAP CI build, complete recovery strategy, separate
   explicit operator consent and real-device acceptance.

## Executable contract prototype — HOST ONLY

`tests/v18_firmware_lease_proto.c` models a shared lease table.
It uses a `pthread_mutex_t` **only as a host stand-in** for a
kernel-protected atomic critical section. It is **not linked into
the production FAP or firmware**.

`check-v18-firmware-lease-proto.yml` independently checks the
exact pinned firmware HAL source expectations and compiles and
executes this host prototype with strict C11 warnings.

Expected HOST tests:
- Non-LabMate owner reserves TIM2/PB3: LabMate refused, then succeeds
  only after the real owner releases.
- EXTI/PC1 vs another PC1 consumer, I2C3 vs PC0/PC1, PWM TIM1/PA7
  vs unrelated TIM2/PB3: alias conflicts fail and disjoint ownership
  can coexist.
- Invalid/empty masks, mismatched/partial/foreign release, double
  release, **stale handle after resource reacquisition** and exhaustion
  never silently clear another owner's resource.
- **24 simultaneous acquisition threads ×25 rounds** race for
  one TIM2/PB3 lease: exactly one owner wins each round.
- Model never reconfigures hardware; no expected PIN/GPIO
  or firmware-side effects are inferred from a successful host run.

The updated HOST model now issues monotonically increasing opaque
handles under the same lock as the claim; a stale handle cannot
release a newly acquired resource, and 64-bit exhaustion fails
closed rather than wrapping. The **real firmware implementation**
still must solve handle uniqueness across service lifetimes, crash
recovery and reboots, supported ABI packaging, and protection against
legacy drivers that bypass the lease.
All these require real firmware integration, proper driver tests,
CI builds and separately approved device tests.

## E11.1a firmware API source stage (experimental, 2026-10-15)

DEV now contains the **experimental firmware-source patch**
[`scripts/patch_momentum_resource_lease.py`](../scripts/patch_momentum_resource_lease.py).
It targets the **exact** Momentum commit and adds two functions to
the **real** `furi_hal_resources.c/.h`, with matching API CSV entries:
`furi_hal_resource_lease_try_acquire(uint32_t resources)` and
`furi_hal_resource_lease_release(uint32_t handle, uint32_t resources)`.

The implementation uses short `FURI_CRITICAL_ENTER/EXIT` critical
sections; returns a monotonically minted nonzero opaque handle only
if every requested resource is free and one table slot is available;
rejects unsupported/noncanonical partial masks; rejects wrong/stale
handles, mismatched masks and double release; and fails closed if
the 32-bit handle counter is exhausted. The table itself does
**not** configure GPIO, EXTI, timers, UART or power, so a failed claim
has no device peripheral side effect.

The patch is purposefully **DORMANT**:
- The old HAL and other Momentum services **do not** call the new
  functions, so this does **NOT** already provide cross-service
  exclusion or a safe production driver interface.
- Its 16-claim capacity and 32-bit handle lifetime are a bounded
  development design; restart/crash ownership and legacy driver
  interposition remain unsolved.
- It edits only pinned **ephemeral CI firmware source** after an
  explicit source check. It does not write to the operator's
  `Momentum-Firmware` checkout, does not flash firmware and does
  not replace the installed EXITFIX FAP.
- The dedicated [E11.1a compile workflow](../.github/workflows/check-v18-firmware-lease-abi.yml)
  applies the already-audited timed I2C patch plus this experimental
  lease source, stages the current integrated LabMate and builds a
  **matched firmware + FAP** in CI, verifying both exported ELF
  symbols. This is build evidence only and publishes no install
  package or release.

**Acceptance distinction:** E11.1a is only a FIRST firmware-compiled
API primitive when CI succeeds; E11.1 requires integration into
all applicable callers, a documented firmware-wide ownership
policy and tested fail-closed behaviors before being considered
complete. No premature Stable approval.

### First real firmware compilation result (CI ONLY, 2026-10-15)

GitHub Actions [run 38749785393](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38749785393)
at source SHA `642496f0323423033b8115a1bbefe9f467588bd6`
completed **SUCCESS**. Verified actual logs include a successful
integrated `APPCHK` and
`REAL FIRMWARE + MATCHED FAP BUILD & EXPORTED ABI PASS (CI ONLY)`.
ELF global function checks found both experimental lease functions and
the existing bounded external-I2C API. Ephemeral, **non-deployable**
build identities logged:

- Experimental compiled `firmware.dfu` SHA256:
  `89593215d9425be1a83f44830495e7303b728752f0ef08dd713bfab35b743c8f`
- Matched experimental `labmate.fap` SHA256:
  `759ab30b970c4ccc10fd30004c38eb5087e409b99510eac89ef5b9ec7e88caf9`
- Current actual installed firmware DFU reference SHA256 remains:
  `e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0`

**The new DFU hash differs from the installed firmware.** These
experimental files **MUST NOT** be used for a FAP-only USB update,
mixed with existing installed firmware, flashed or promoted to Stable.
CI did not stage/publish a user-installable update artifact. The
experimental firmware API is dormant and the HAL-wide lease
interposition is missing.

### Stronger check: executing the real firmware lease C body (2026-10-15)

[GitHub Actions run 38750321416](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38750321416)
at exact source SHA `2311ffe183f32ccd2e563d1e314d3b9e1a5ef1b0`
completed **SUCCESS**. The new
[`tests/test_v18_firmware_lease_source.py`](../tests/test_v18_firmware_lease_source.py)
extracts the **same C functions actually injected into
`furi_hal_resources.c`**, substitutes host mutexes only for
`FURI_CRITICAL_ENTER/EXIT`, then strictly compiles and executes
those functions. CI logs confirm:

- `E11.1a ACTUAL FIRMWARE LEASE C SOURCE HOST HARNESS PASS: alias, stale handle, 24 threads x25, exhaustion`
- `E11.1a FIRMWARE SOURCE PATCH PASS`
- real full firmware build, integrated `APPCHK`, and three
  expected exported ELF symbols PASS.
- Rebuilt experimental DFU and FAP SHA256 match the independent
  previous CI build (shown above).

This closes the risk of relying **only** on a different example
model: the real firmware primitive's basic logic is now executed
under contention in an injected host environment. This **does not**
prove its FURI critical section semantics on device, HAL call-site
integration, legacy service cooperation, recovery after process
failure, or any real Flipper behavior. Those are **OPEN**.

## Evidence/status gates

| Gate | Scope | Status |
| --- | --- | --- |
| E11.0 | Source contract audit + contested host lease prototype | **HOST CI PASS (hardened)**, [run 38748481542](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38748481542), source SHA `f6e93a14e8f989d089fbe18e9e33628fd33abd1d` |
| E11.1 | Actual patched firmware atomically enforces leases across all relevant HAL/service paths | **NOT IMPLEMENTED** |
| E11.2 | Matched firmware+FAP builds/APPCHK, API/ABI, failure-path and no-register-mutation tests | **NOT TESTED** |
| E11.3 | Operator-approved on-device competing-service safety tests, rollback verified | **NOT TESTED** |
| E10 | Existing-file preservation; nine historical logs absent with unknown reason | **OPEN**, do not restore automatically |

**Release decision:** E11 is a v1.8 gate, not a v1.9 replacement.
Do not mark v1.8 complete based solely on host lease simulations.
The canonical `ROADMAP.md` and
`docs/MASTER_ROADMAP_V2_ADDENDUM.md` remain authoritative.

## E11.0 observed CI evidence (2026-10-15)

At the exact source commit `bdbcc5676072bfc6b0a455de191f17fc10a43c51`,
GitHub Actions [run 38747593373](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38747593373)
completed **SUCCESS**. Its one job passed all steps, including:

- `E11 PINNED-SOURCE AUDIT PASS: source hazard assumptions confirmed.`
- `HOST LEASE MODEL PASS: all-or-nothing, owner-safe, alias-safe, contested 24-thread test x25`
- `FIRMWARE-GLOBAL OWNERSHIP: NOT IMPLEMENTED / NOT HARDWARE VERIFIED`

This is **E11.0 host-model/source-audit PASS**, NOT E11.1 firmware-side
implementation, NOT a new FAP, and NOT a device PASS. The host
initial prototype used caller-provided numeric tokens; the
subsequent hardened prototype creates unique nonreused opaque handles
atomically, fails closed on exhaustion and rejects stale release.
Actual firmware integration, crash handling and service-by-service
interposition remain **NOT IMPLEMENTED**.

### E11.0b hardened handle regression PASS (2026-10-15)

GitHub Actions [run 38748481542](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38748481542)
completed **SUCCESS** at exact prototype commit
`f6e93a14e8f989d089fbe18e9e33628fd33abd1d`.
The actual CI job logs contain:

- `E11 PINNED-SOURCE AUDIT PASS`
- `HOST LEASE MODEL PASS: atomic all-or-nothing, stale-handle-safe, alias-safe, 24-thread contest x25`
- `FIRMWARE-GLOBAL OWNERSHIP: NOT IMPLEMENTED / NOT HARDWARE VERIFIED`

This is a *replacement* host-model evidence snapshot, not a new
firmware/FAP artifact or an on-device result.

## E11.1a–E11.1b firmware build and full caller inventory (2026-10-15)

### E11.1a: experimental firmware-resident primitive — COMPILE/ABI PASS ONLY

The exact pinned Momentum checkout received an experimental,
**dormant** firmware-resident claim/release API through
`scripts/patch_momentum_resource_lease.py` in a **temporary CI**
workspace. It uses short Furi critical sections, an atomic mask,
non-reused 32-bit handles, fixed composite peripheral+GPIO masks,
wrong/stale release refusal, and returns BUSY (handle 0) without
mutating peripheral registers. It has **no LabMate callers and does
not intercept existing Momentum HAL owners yet**.

The initial CI preflight exposed a real script bug: parsing
`git status --porcelain` with `.strip()` removed the leading
status column and mistakenly truncated source paths; preflight
correctly refused the patch. Commit
`3172db615cc13fb57a31e142c988eeaf8d189f6b` fixed this by
preserving the exact two-column porcelain format. The subsequently
observed [run 38749893972](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38749893972)
completed SUCCESS, as did prior run
[38749785393](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38749785393).
The exact workflow checks the original timed-I2C patch combined
with the dormant resource-lease API, builds full firmware and the
single integrated LabMate FAP, sees genuine `APPCHK`, and confirms
both lease functions and timed-I2C export in `firmware.elf`.

**This is not deployable as a FAP-only update.** Changing firmware
exports/ABI requires a different firmware image from the installed
one, a new full updater/rollback gate, all drivers integrated,
operator approval and device retests. No such installation is
approved or performed; the existing EXITFIX physical passes refer
to the old matched firmware/FAP.

### E11.1b: pinned original HAL owner inventory — SOURCE CI PASS

[Run 38750419882](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38750419882)
verified the exact known caller files using
`scripts/check_v18_owner_inventory.py`. These file counts include
HAL *definitions* where applicable and **are not counts of active
simultaneous owners**.

| Firmware symbol | Verified *.c/*.cpp source paths | Representative users / risk |
| --- | ---: | --- |
| `FuriHalBusTIM1` | 9 | PWM, iButton, NFC timer, RFID, infrared, speaker, signal reader, Sub-GHz external driver |
| `FuriHalBusTIM2` | 6 | pulse reader, digital sequence, RFID, infrared, Sub-GHz |
| `furi_hal_gpio_add_int_callback` | 9 | built-in input, NFC IRQ, one-wire slave, serial-control, JavaScript GPIO, external peripheral drivers |

The inventory guard FAILS CLOSED if an expected pinned source caller
appears or disappears, rather than treating an unreviewed HAL user
as protected. TIM1/2/EXTI are widely shared with firmware services;
blindly wrapping only LabMate would give a false guarantee.

**Next required migration:** identify all live HAL/service ownership
lifecycles; add an atomic claim at the actual resource-acquisition
boundary and correct release only after each driver's stop/cleanup;
ensure common GPIO/EXTI aliases and existing I2C mutex agree.
Mock fail-to-acquire tests must demonstrate **no clock changes,
interrupt removal, GPIO reconfiguration or other-owner disruption**.
Avoid a deliberate on-device conflict/crash test. The remaining
E11.1 firmware integration and E11.3 physical safety approval
remain **NOT IMPLEMENTED / NOT TESTED**.
