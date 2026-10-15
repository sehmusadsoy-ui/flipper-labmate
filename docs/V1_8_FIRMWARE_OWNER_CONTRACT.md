# v1.8 E11 — Firmware-Global Resource Lease Contract (DESIGN ONLY)

**Branch:** `dev/v1.8-completion` / Draft PR #13.
**Pinned, already installed firmware source:** Momentum
`d3f89dfe2ef6b01839201598e9be1590cba80322`.
**Installed LabMate EXITFIX FAP SHA256:**
`7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`.
**Approval state:** NO new firmware/FAP/USB install; NO v1.8 Stable approval.

**E10 operator clarification (2026-10-16):** The user reports
personally deleting Log History/CSV entries the previous day.
The absence of `log_0041.csv`–`log_0049.csv` is consistent
with intentional deletion, although no deletion log matches
each ID independently. Do **not** treat this as demonstrated
app data loss or a pending release gate. Keep old snapshots
and backups read-only; only investigate if a *new* unexplained
disappearance occurs. Any earlier E10 "OPEN/unknown reason"
phrasing in dated historical sections below records the
status *before* this clarification and is superseded here.
Firmware-wide E11 is a separate unresolved gate.


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
| E11.1 | Actual firmware ownership across relevant HAL/service paths | **PARTIAL** — LabMate claim integration + native Momentum PWM paths migrated; other independent GPIO/EXTI/TIM services still bypass |
| E11.2 | Matched firmware+FAP builds/APPCHK, API/ABI, failure-path and no-register-mutation tests | **SELECTED CI PASS** — multiple exact-source paired builds and native PWM actual-C denial tests; not a universal firmware/device PASS |
| E11.3 | Operator-approved on-device competing-service safety tests, rollback verified | **NOT TESTED** |
| E10 | Nine historical logs absent; operator now reports manual Log History deletions | **NOT A SUSPECTED APP-LOSS BLOCKER**; precise file-by-file deletion causality unverified; preserve backups |

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

### E11.1a actual firmware primitive runtime CI (2026-10-15)

[Run 38751054638](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38751054638)
at SHA `da9e8d84206c3c0f080b3ebea01ec2afb2c1321e`
completed **SUCCESS**. `tests/test_v18_firmware_lease_primitive.py`
extracts the **exact C function bodies** from
`scripts/patch_momentum_resource_lease.py` (not a second invented
claim/release implementation), substitutes a host pthread mutex for
Furi critical sections, compiles with GCC strict warnings and
executes behavior tests. Actual job log:

`E11.1a ACTUAL FIRMWARE LEASE C SOURCE HOST TEST PASS`

Verified host scenarios include rejected incomplete mask, busy
same-resource conflict, independent nonintersecting mask use,
wrong/partial/stale/double release, I2C vs PC1, 1-Wire vs IRQ PA4,
24 competing threads ×25 iterations with exactly one winner, and
fail-closed handle generation exhaustion. **This tests C source logic
on a host, not the STM32's interrupt primitives or other services.**
It does not prove an app can safely use TIM1/TIM2 while native
firmware drivers bypass the lease API. No device was changed.

### E11.1c — Nonasserting EXTI callback registration (EXPERIMENTAL)

To avoid calling pinned Momentum's assertion-only EXTI registration
when a callback is already present, DEV includes:

- [`scripts/patch_momentum_gpio_tryadd.py`](../scripts/patch_momentum_gpio_tryadd.py)
  — exact pinned-source, **read-only by default**, adds
  `furi_hal_gpio_try_add_int_callback(gpio, cb, ctx)` to
  `furi_hal_gpio.c/.h` and the firmware API symbol table.
  The function atomically tests the existing HAL callback slot;
  if occupied, it returns `false` without replacing the existing
  callback, context or enabling the interrupt.
- [`tests/test_v18_gpio_tryadd_source.py`](../tests/test_v18_gpio_tryadd_source.py)
  — compiles the **exact patched firmware C function body** on the
  host with mutex-backed critical-section and EXTI-enable stubs.
  Tests no-op invalid args, same shared EXTI line denial, preserved
  prior callback and 24 concurrent attempts ×25 rounds.
- [`check-v18-gpio-tryadd.yml`](../.github/workflows/check-v18-gpio-tryadd.yml)
  — separate CI workflow that applies the verified I²C, dormant
  resource lease and new GPIO callback API patches **only to
  ephemeral Momentum source**, then builds firmware + integrated
  LabMate FAP and checks ELF symbols.

**Scope limitation:** this *does not* claim GPIO pin ownership,
verify alternate-function or pin mode state, or protect any legacy
service that invokes the old assertion-based callback API.
In particular, calling it *after* reconfiguring a pin would still
be unsafe if a foreign service owns that pin. LabMate has **not
been migrated to use it**. It is a dormant ABI piece, not
a verified firmware-global conflict solution. No firmware or FAP
has been installed on the operator's Flipper.

CI evidence/status: **HOST + PINNED FIRMWARE BUILD CI PASS**, not
physical/hardware global-ownership PASS. [GitHub Actions
run 38794546759](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38794546759)
at exact source commit `e3b0f3504a534d62f1d9c092ba949fbe2d7e8769`
concluded SUCCESS: actual source body compiled with host
contention stubs, exact three-API-patch firmware source
preflight completed, real firmware + integrated FAP built
and `APPCHK` passed, then exported ELF symbols were confirmed.
Actual CI logs printed
`E11.1c EXACT FIRMWARE GPIO TRY-ADD C HOST TEST PASS`
and
`E11.1c ACTUAL FIRMWARE + FAP BUILD AND EXPORTED EXT IRQ API PASS`.

**CI-only artifact fingerprints (not installed):**
- Firmware DFU SHA256 `7c51915d81317e3be6661b46c54fe171deb71e1045f214ad6f72310766771611`.
- LabMate FAP SHA256 `e7ecd22a7a45fa88017a76a07f553ff67c4b2157b0e4eef9feb73eb2f968ccaa`.

These replace **neither** the installed matched DFU nor the installed
EXITFIX FAP; reusing this FAP on the current firmware is unsafe.
This function does not include pin lease acquisition, is not used
by the existing LabMate capture drivers, and does not protect
legacy firmware services. E11.1 integration remains OPEN.


## E11.1d — PB3/TIM2 first production-driver integration (2026-10-15)

**Experimental DEV only, NOT firmware-global safety or hardware approval.**
`src/labmate_frequency_tim2.c/.h` now requires the actual
`FURI_HAL_RESOURCE_LEASE_API_V1` firmware contract and atomically tries
`FURI_HAL_LEASE_COUNTER_PB3` **before any** PB3 GPIO alternate-function,
TIM2 clock/register, or interrupt-related writes. The driver returns a
boolean acquisition result. A denied lease, already-active local lease,
or an SDK lacking the lease API returns false without any hardware
initialization. The latter is intentionally fail-closed: a FAP built
from this experimental branch against unpatched/old Momentum will not
start Frequency HIGH or Event Counter. **Do not install or mix a DEV
FAP with existing installed firmware.**

Both callers (`labmate_frequency_capture.c`,
`labmate_event_counter.c`) preserve inactive capture state and mark
`capture_blocked` when the driver refuses the claim. TIM2
enable/disable/read/shutdown are guarded against a denied or absent
claim. Normal shutdown tears down only the acquired driver and releases
the exact handle/mask *after* hardware cleanup; a failed release
retains the local handle as a fail-closed condition, preventing a
second teardown or fresh configuration.

`tests/test_v18_tim2_lease_integration.py` compiles the **actual
production C driver** with instrumented host HAL macros in two modes:
missing API and occupied lease (no HAL writes, reads or releases), plus
successful claim/enable/read/stop/release, duplicate start/stop, and
failed release. This host harness does **not** model an independent
legacy HAL driver that bypasses the firmware lease or the real MCU
clock/register behavior.

`.github/workflows/check-v18-tim2-lease-integration.yml`
tests that real C driver and builds the exact pinned patched Momentum
firmware and one integrated LabMate FAP in CI, checking exported
symbols. [E11.1d run 38796545033](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38796545033)
**SUCCESS** at exact tested source `b006fa9c75c18612a10a30edb84cee6bab00cb7d`:
real production C host failure-path tests PASS; matching patched
`firmware_all fap_labmate`, exported-symbol check and FAP `APPCHK`
PASS. Experimental DFU SHA256
`7c51915d81317e3be6661b46c54fe171deb71e1045f214ad6f72310766771611`;
experimental integrated FAP SHA256
`a4b7ff8f44120a09c625abd624d23e3121c59edaaeea5c2cacd3aeffcd3bc174`.
Original source-boundary script was updated for boolean configure;
normal LabMate source CI
[run 38796737125](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38796737125)
**PASS** on `0a4aa3fbe143335307e652a69fdc6cb61b897ce0`.
**Neither binary is deployment-approved**; no USB/flash or Stable
release is authorized.

**Remaining E11.1d:** actual EXTI callback/pin registration and failure
rollback, GPIO Monitor, PWM TIM1/PA7, 1-Wire PA4, UART and I2C owners;
then shared firmware service adoption. A successful local PB3/TIM2
claim is **not** evidence that legacy independent TIM2 users cannot
bypass it. TIM2 hardware may still be reconfigured by a legacy service
until the common firmware-wide contract is enforced.

## E11.1d continuation — LOW PC1/EXTI1 opt-in driver, 2026-10-15

**Development branch only; no operator installation or global-ownership claim.**
Following the already accepted PB3/TIM2 driver stage, the actual
`src/labmate_frequency_capture.c` LOW/PC1 acquisition path now requests
`FURI_HAL_LEASE_IRQ_PC1` before any EXTI trigger or GPIO mode mutation.
It then calls the nonasserting
`furi_hal_gpio_try_add_int_callback()` **before** configuring the pin.
A BUSY lease or occupied EXTI callback slot leaves the existing pin,
interrupt configuration and callback untouched. Releasing a claimed
lease after callback refusal is attempted exactly once. If release
fails, the local handle remains blocked: never configure the GPIO
on a later START while ownership is unresolved.

On success, callback delivery is disabled while any stale falling
trigger is cleared and the input is configured as rising-edge PC1.
The ISR ignores any EXTI notification before the application has
published its active owner. STOP disables and removes the registered
callback, clears EXTI triggers, puts the owned pin in analog mode,
and only then tries to release the precise handle. Repeat STOP/START
and failed releases are fail-closed. The opt-in LOW capture deliberately
does **not** start on an SDK missing either E11 experimental firmware
API, rather than falling back to the old potentially asserting callback
registration. Keep old firmware and new DEV FAP separate.

Host tests `tests/test_v18_pc1_exti_lease_integration.py` compile
the **actual production LOW start/stop C functions** in both SDK modes
with instrumented HAL stubs; tests cover zero register/GPIO/IRQ
writes on missing API, denied lease and occupied callback, plus
success, STOP, duplicate calls and failed-release blocking.
The ISR pre-activation guard is also checked in source, but the actual
STM32 interrupt schedule and unrelated firmware services are **not**
simulated by that test. This first migration does not yet protect
GPIO Monitor, Pulse/other EXTI pins, Button Analyzer, PWM, 1-Wire,
UART or I2C, or force legacy Momentum services to participate.

Standard LabMate SDK/source + installer mock
[CI 38800552296](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38800552296)
**PASS** at code SHA `090a5b4f6223916912e4ec1d24d7f939c4d6f60e`.
Matched pinned patched firmware + integrated FAP
[CI 38800552304](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38800552304)
also **SUCCESS** at the same exact code SHA
`090a5b4f6223916912e4ec1d24d7f939c4d6f60e`.
The job built actual `firmware_all fap_labmate`, ran `APPCHK`,
and confirmed the lease/acquire, lease/release, GPIO try-add and
timed external I2C symbols were global/defined in firmware ELF.
CI-only DFU SHA256:
`7c51915d81317e3be6661b46c54fe171deb71e1045f214ad6f72310766771611`.
Matched CI-only FAP SHA256:
`0a46cb2097a2cec4561009387bc1cab3244da68edf5ddb93dbf2ef917ad4a44b`.
**These are experimental build files, not installed assets.** Neither
CI path flashed, uploaded to USB or modified any Stable release.

**Outstanding:** migrate all capture paths and firmware services at the
actual resource-acquisition boundaries; coordinate existing I2C mutex;
test callback and pin rollback with real firmware conflicts; complete
separately authorized safe on-device tests. E11.1 global contract is OPEN.

## E11.1d continuation — Pulse Analyzer and Button Analyzer EXTI integration (2026-10-15)

**Experimental DEV driver code only; not a global lease or physical PASS.**

The four production Pulse Analyzer IRQ inputs PC0, PC1, PB2, PA4
now request the matching firmware `FURI_HAL_LEASE_IRQ_*` mask before
touching the GPIO or EXTI registers. The actual selected pin and mask
are retained throughout the session. The Button Analyzer likewise
acquires the exact PC1/EXTI1 mask before its pull-up/pin configuration.
Both register through the nonasserting firmware
`furi_hal_gpio_try_add_int_callback()` **before** pin
configuration, reject an occupied callback without pin mutation,
disable the callback while preparing the pin, guard ISR delivery
before owner publication and clean up only the owned callback and
pin on STOP. The Button STOP/RESUME measurement state is preserved.

Old or unmatched Momentum SDKs cause these experimental capture
paths to fail closed rather than silently using the assertion-based
legacy GPIO callback API. Any denied lease leaves existing GPIO,
callback, EXTI and measurement state unchanged. The claim API remains
opt-in; a competing legacy service can still bypass it.

The shared capture coordinator now has a sticky
`capture_release_fault` flag. A failed-release path retains its
original handle and prevents new capture starts; a generic STOP
cannot clear the fault and incorrectly advertise safe reuse.

The host harness `tests/test_v18_pulse_button_exti_integration.py`
compiles/exercises the **actual production** start/stop C functions
in both SDK modes. Instrumented stubs check missing SDK, denied
lease, occupied callback, no mutation before acquisition, all four
Pulse pins, Button RESUME, double start/stop, STOP cleanup and
release failure. It does not execute STM32 IRQ timing, observe
registers on a Flipper, or model an uncoordinated legacy service.

The paired firmware/FAP
[dedicated CI workflow](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/workflows/check-v18-pulse-button-lease-integration.yml)
uses an ephemeral pinned Momentum checkout with the timed-I2C,
resource lease and nonasserting try-add source patches. Requiring
`firmware_all fap_labmate`, APPCHK and global ABI symbols is only
a build/export gate. Keep exact source/FAP SHA and final CI status
tied to the specific successful run; never treat queued or
in-progress CI as PASS. No hardware image or Stable asset is
modified. Original v1.8 Stable remains published unchanged.

**Outstanding E11.1:** GPIO Monitor, PWM TIM1/PA7, 1-Wire PA4,
UART, I2C cross-service coordination; migration of all applicable
independent Momentum HAL/services (TIM1, TIM2, EXTI) to the same
mandatory ownership agreement, firmware-wide stress/rollback tests
and new physical acceptance. E10's historical missing CSV IDs
remain an independent unresolved data-preservation issue.

### Pulse/Button host + matched real build evidence

[GitHub Actions run 38802540887](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38802540887)
**SUCCESS** on exact development source
`a71dfb657e72625f2ee2d77ec3db9f70ddade19c`.
The job compiled and executed the real production Pulse/Button
start/stop functions under strict HAL mocks: missing API, owner denied,
occupied callback (zero GPIO/EXTI modifications), four Pulse pins,
Button RESUME, repeated START/STOP, failed lease release. It also
reran earlier LOW/PC1 and TIM2 host tests.
Actual patched Momentum `firmware_all fap_labmate`, FAP `APPCHK`
and exported ELF symbol checks **PASS**.
The matching **CI-only**, never-installed DFU checksum is
`7c51915d81317e3be6661b46c54fe171deb71e1045f214ad6f72310766771611`.
The matching **CI-only**, never-installed FAP checksum is
`836f2e0cfd03660322801c5f47a15c17ec3f599cc9dfa887bba77e0d9bea7b9b`.

A subsequent hardening stage extends sticky failed-release propagation
to the shared STOP coordinator and the remaining PB3/TIM2 caller
paths (Frequency HIGH and Event Counter). Its exact code, tests and
checksums must be evaluated separately; earlier CI success does
not certify subsequent commits. No modified firmware/FAP has
been installed on the physical Flipper. Neither release nor merge
approval is inferred from any of these host/build tests.

### Shared capture STOP + PB3/TIM2 release fault hardening

A subsequent DEV change adds `capture_release_fault` to the
actual LabMate app state. When a firmware lease release fails, the
affected LOW Frequency, Pulse, Button, HIGH Frequency or Event
Counter path latches the condition and the common
`labmate_capture_stop_all()` does **not** clear the denial.
`labmate_capture_can_start()` rejects any further capture until
a fresh app instance; a failed-release handle remains reserved and
is not silently reused. `labmate_frequency_tim2_lease_pending()`
exposes the driver's post-shutdown unresolved TIM2 owner to its
two callers (HIGH Frequency and Counter). This does **not**
recover lost firmware resources across unrelated services or
guarantee automatic crash cleanup.

[Exact source `31e8f77d` TIM2 CI 38803046030](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38803046030)
**SUCCESS**: actual TIM2 C driver host tests (missing API,
conflict, STOP, failed-release retention), matched pinned Momentum
firmware + single LabMate FAP compilation and APPCHK, ABI export
checks all PASS. CI-only patched DFU SHA256:
`7c51915d81317e3be6661b46c54fe171deb71e1045f214ad6f72310766771611`.
CI-only FAP SHA256:
`3fe795d7f606154c0dfd32350c79405c831a573cfa5e250ff07f79ba0a714e76`.

Additional host test `tests/test_v18_capture_release_fault.py`
executes the **actual** shared STOP and acquisition C bodies and
checks sticky denial through repeated STOP and reattempted capture.
The [combined Pulse/Button workflow](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/workflows/check-v18-pulse-button-lease-integration.yml)
includes the newer test in its host gate. Its full matched build
should be recorded separately only once the exact run succeeds.
No compiled firmware, experimental FAP or Stable asset has been
installed or published.

### Final combined source/host/firmware checkpoint for this E11.1d iteration

[Combined run 38803350705](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38803350705)
**SUCCESS** at exact tested source
`6f3a67d91e4af2d8c26991d29b82bc5a154af93f`.
The host job executed actual production Pulse/Button start/stop,
shared STOP/can-start latch, PC1 Frequency and TIM2 C driver
denial/cleanup tests with strict HAL stubs. Actual pinned,
patched Momentum `firmware_all fap_labmate`, FAP `APPCHK`
and four defined ABI/ELF export symbols **PASS**.
CI-only experimental DFU SHA256:
`7c51915d81317e3be6661b46c54fe171deb71e1045f214ad6f72310766771611`.
CI-only experimental FAP SHA256:
`3fe795d7f606154c0dfd32350c79405c831a573cfa5e250ff07f79ba0a714e76`.
The current branch may contain **documentation-only** follow-up
commits after this exact tested source; do not imply they received
different hardware verification. The standalone, normal LabMate
SDK/source test [run 38802958804](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38802958804)
also succeeded on earlier exact source `975b8d4f2c2b3c09b059e0cc952c7f7a5f16535b`
including the TIM2 release propagation code; subsequent changes
until this combined checkpoint were Python host harness/workflow.

This is **SOURCE + HOST TEST + REAL BUILD PASS**, not Flipper
physical device acceptance or mandatory firmware-wide ownership.
No new custom firmware/FAP has been installed, `main`, Stable and
previous release assets are unchanged; PR #13 stays Draft.

## E11.1e — LabMate TIM1/PA7 PWM opt-in lease (development stage, 2026-10-15)

**DEV SOURCE integration, NOT mandatory firmware-global ownership.**
The actual `src/labmate_generator.c` now requests exactly
`FURI_HAL_LEASE_PWM_PA7` through the versioned firmware-owned
atomic API **before** calling `furi_hal_pwm_start()`, whose
implementation would otherwise change PA7 alternate-function and
TIM1 peripheral state. If firmware lacks the matching SDK/API or
a different cooperative caller holds the lease, START refuses
without ANY `furi_hal_pwm_start/stop/set_params` call.
An accepted owner may retune frequency/duty in-place only while
the lease is retained. STOP invokes the PWM HAL while still holding
its handle and then attempts an exact-mask release. A failed
release holds the opaque handle and latches a permanent local
`generator_release_fault`, preventing unsafe subsequent START
attempts and duplicate STOP. The on-screen badge reports BUSY
for a refusal and ERR for a failed release.

`tests/test_v18_pwm_lease_integration.py` compiles the **actual
production generator source** with HAL instrumentation in the
stock SDK and matched patched firmware API modes. The tests
check no peripheral writes on missing/busy claim; proper order
on START, frequency/duty retune, STOP then release; repeated
START/STOP; and refusal to reuse a failed release. The
dedicated [E11.1e workflow](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/workflows/check-v18-pwm-lease-integration.yml)
then builds exactly one matched patched Momentum firmware plus
LabMate FAP and checks `APPCHK` and exported symbols. Individual
run results and checksum evidence must be recorded separately.

**CRITICAL:** the existing Momentum firmware PWM and other TIM1
drivers still use legacy HAL entry points and may bypass the opt-in
lease entirely. The existing firmware lease table does NOT intercept
those calls; `furi_hal_pwm_start()` returns void and may assert
or race if a bypassing service configures TIM1. This stage has
not made on-device TIM1/PWM conflicts safe. Only migrate and
hardware-test against a separately approved complete firmware
owner integration; never install a FAP built for an SDK with
new exports on the old firmware.

### GPIO Monitor remains a separate E11.1e blocker

`src/labmate_monitor_gpio.c` still uses
`furi_hal_gpio_init_simple()` for both activation (input) and
release (analog). Its application-local PA7-while-PWM-running
policy does **not** detect independent firmware pin owners
and does not acquire a firmware pin lease. The present
experimental firmware mask table lacks generic single-pin
claims for all eight GPIO Monitor pins. Treat this as
**NOT PROTECTED / NOT TESTED**, not PASS. It requires review
of pin aliases and firmware services (especially PC3/PA6
shared-number EXTI concerns), a fail-closed pin claim before
a pin mode change, ownership-aware release and a dedicated
no-mutation-on-conflict host + matched-firmware build.
Avoid changing the tested Monitor UX blindly without a
supported lease contract.

No changes are authorized to the operator's hardware,
historical CSV files, original v1.8 source tag, Stable
release assets or `main`; PR #13 remains Draft.

### E11.1e initial PWM CI PASS and Monitor PA7 local hardening

[PWM firmware+FAP run 38806523352](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38806523352)
completed **SUCCESS** at exact source
`dba797760bae38e2405baf21c163fb404e44ca79`.
Its strict host test compiles the **actual** TIM1/PA7 generator
C implementation in both old-SDK and lease-enabled modes,
confirming no PWM HAL calls on denied/missing lease; START,
live frequency/duty retuning, idempotent STOP, correct release
ordering and failed-release restart refusal. Actual pinned patched
Momentum `firmware_all fap_labmate`, `APPCHK` and four
required firmware ELF function exports passed. CI-only DFU
SHA256 `7c51915d81317e3be6661b46c54fe171deb71e1045f214ad6f72310766771611`.
CI-only matching integrated LabMate FAP SHA256
`baa913a4c9ce59930caed02095d7a87b094e4e693f1e9ac018231b16bf2a7d34`.
**Not installed or release-approved.**

A follow-on, still *application-local* guard prevents GPIO Monitor
from choosing or reconfiguring PA7 when PWM is actively running,
a firmware lease claim was denied (`generator_blocked`),
or a PWM release failed (`generator_release_fault`). This also
protects navigation and monitor release paths from clearing
a GPIO that may belong to an active/stale PWM owner.
`tests/test_v18_monitor_pa7_protection.py` instruments and
executes the **actual** Monitor C file for these modes.
[Dedicated combined run 38806928654](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38806928654)
and the normal LabMate SDK/source CI must be checked for their
independent final conclusions and exact SHAs.

**Still not protected:** arbitrary firmware pin modes for all
other GPIO Monitor pins; a foreign legacy service that never uses
the E11 lease API; timer/interrupt owner recovery across crashes.
Preventing PA7 reconfiguration after an observed PWM denial
is useful local safety, **not** a firmware-wide GPIO lease.

### E11.1e Monitor eight-pin owner review (design, NOT implemented)

The actual pin mapping in `src/labmate_capture_core.c` and
`src/labmate_monitor_gpio.c` is:

| Monitor index | Pin | Related subsystem / conflict alias | Monitor firmware pin lease |
| --- | --- | --- | --- |
| 0 | PC0 | EXTI0 / external I2C3 | **NONE** |
| 1 | PC1 | EXTI1 / LOW Frequency / Button / I2C3 | **NONE** |
| 2 | PC3 | EXTI3 line number also used by onboard OK key | **NONE** |
| 3 | PB2 | EXTI2 / Pulse Analyzer | **NONE** |
| 4 | PB3 | TIM2 frequency/counter and shared EXTI3 line number | **NONE** |
| 5 | PA4 | EXTI4 / external 1-Wire sensor | **NONE** |
| 6 | PA6 | EXTI6 line number also used by onboard DOWN key | **NONE** |
| 7 | PA7 | TIM1 PWM; app-local RUN/BUSY/release-fault exclusion now added | **NONE** |

Existing firmware E11 API composite masks cannot be reused
as a general passive GPIO Monitor pin owner without reviewing
and defining valid single-pin masks, aliases, and pin-only
lifecycle. In particular, claiming an EXTI callback is not
appropriate for a passive polling Monitor, and merely calling
`furi_hal_gpio_read()` after silently skipping required pin-mode
configuration may produce invalid readings. A proper implementation
must add a pinned-versioned firmware pin contract and migrate
native pin-mode writers; mark the Monitor's **global GPIO ownership
as OPEN** until supported by CI and separately authorized hardware
verification. The PA7 app-local exclusion does not address the
other seven pins or foreign noncooperative services.

### E11.1e PWM plus Monitor PA7 combined CI evidence (2026-10-15)

[Combined real firmware/FAP run 38806928654](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38806928654)
**SUCCESS** at exact source SHA
`2cc12665d5acf90922a15b15efcbfdad11c685dd`.
The actual production `labmate_generator.c` compiled/executed
under strict host mocks in both old SDK and lease-enabled modes.
The actual `labmate_monitor_gpio.c` also compiled/executed against
instrumented GPIO stubs, confirming that a denied, running or
unresolved PWM lease prevents PA7 input/analog reconfiguration.
The TIM2 driver and common capture STOP host tests still passed.
Real exact pinned patched Momentum firmware and **one integrated**
LabMate FAP compiled; `APPCHK` and ELF exported-API checks passed.

**CI-only firmware DFU SHA256:**
`7c51915d81317e3be6661b46c54fe171deb71e1045f214ad6f72310766771611`.
**CI-only matched FAP SHA256:**
`96785b757ed4b254f80aafa5c7e63cc9f57f701a48803c492c0a1331e05e4849`.
These replace neither the currently installed firmware/FAP nor
the public v1.8 Stable binaries.

The normal LabMate source checks (including updated boundary
guards checking PA7 BUSY/failure exclusion) and standard
Momentum SDK FAP compile, plus mocked Windows installer passed in
[CI 38806991034](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38806991034)
at exact SHA `8435cbd7c817187c04ee5a6a81e418048e352221`.
This latter SHA adds a **static guard adjustment**, not further
production driver modifications.

**Release gate:** E11.1e local PWM lease and limited Monitor PA7
exclusion are HOST + FIRMWARE BUILD PASS ONLY. Legacy Momentum
HAL/service TIM1 and GPIO callers still bypass the lease,
Monitor's other seven pins are not firmware-claimed, and
device contention/correct measurement tests have not occurred.
E11.1 mandatory global ownership, E10 historical CSV integrity,
and operator-approved physical acceptance remain OPEN.
No firmware/FAP upload or Stable action performed.

## E11.1f — All-eight GPIO Monitor opt-in pin-only claims (2026-10-15)

**Actual integrated DEV code; still not firmware-wide mandatory GPIO
ownership.** The pinned Momentum resource-lease source patch now
defines *eight exact single-pin masks* with shared pin bits:
PC0, PC1, PC3, PB2, PB3, PA4, PA6, PA7. The first six
overlap applicable existing EXTI/TIM2/I2C/1-Wire leases, PA7
overlaps PWM TIM1, and PC3/PA6 have distinct non-EXTI bits.
The firmware C implementation continues to enforce unique
nonzero exact-mask handles under its critical section and
refuses overlapping claims. No generic arbitrary bit claim is
accepted and legacy GPIO HAL callers are **not** intercepted.

`src/labmate_monitor_gpio.c` now requests the pin-only lease
**before** changing any GPIO pin to input; only an acquired
Monitor pin can be read as a valid level or configured back to
analog. A different selected pin cannot release that owner.
On a denied lease or unmatched stock SDK, the driver performs
zero GPIO mode writes and zero pin reads; the Monitor's
`monitor_blocked` status displays BUSY, not a synthetic
LOW sample. Release failure retains a sticky handle and
`monitor_release_fault`; no new pin is claimed.
The app-thread measurement and HOLD-resume code now check
whether a sample was actually acquired before recording logic
level or edge counts. PA7 local exclusion when PWM RUN,
BUSY, or release-fault remains.

`tests/test_v18_monitor_pa7_protection.py` now instruments
the **actual** production Monitor C file in stock/matched SDK
modes: all 8 pin masks; occupied pin; successful sample; wrong
pin STOP; duplicate START; STOP/release; sticky release
fault; and no pin writes on a denied/missing lease.
`tests/test_v18_firmware_lease_primitive.py` additionally
extracts and executes the **exact patched firmware C source**
to validate all eight pin aliases against TIM1, TIM2, EXTI,
I2C3, OneWire, incorrect releases and 24-thread ownership
races. Host mocks do not simulate independent legacy GPIO
services or real electrical signals.

Evidence:
- [E11.1e combined Monitor/PWM full pinned Momentum/FAP build,
  CI 38808169801](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38808169801):
  **SUCCESS**, code SHA `97b4a562ce761064d1033ceeaeac104c0b2536a2`.
- [E11 firmware lease actual-C mutex/concurrent alias host
  CI 38808426053](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38808426053):
  **SUCCESS**, SHA `c25328931fde966d9b9567701c27ec5ecca2fa86`.
- Standard SDK Source CI for subsequent static boundary change
  `7de7d5412b9dbe50f81730f7e76c3473265621ee`
  has a separate run
  [38808259776](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38808259776);
  do not claim SUCCESS until concluded.

**Unfinished global E11:** the pinned native Momentum GPIO,
input, TIM1, TIM2 and EXTI users still do not honor these
voluntary pin-only claims, so some existing services can modify
a claimed pin; mandatory interception/caller migration and
physical conflict acceptance remain OPEN. PC3/PA6 are only
separate GPIO bits; their shared-number EXTI pin multiplexing
is **not** globally safe merely because they have masks.
Stock firmware lacks exported API; DEV app must fail closed
rather than attempting unsafe GPIO writes. Never install this
FAP without its exact separately-approved matching firmware.
Original Stable, `main`, historical tags and SD backup data
are untouched.

### E11.1f normal source/stock SDK checkpoint

[Normal LabMate source + Windows installer mock CI
38808259776](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38808259776):
**SUCCESS** at exact code/static-guard SHA
`7de7d5412b9dbe50f81730f7e76c3473265621ee`.
This includes the eight-pin Monitor implementation, safe sample
handling and strengthened static boundaries, and confirms the
normal stock SDK source compile remains valid with the new
conditional fail-closed GPIO path. This was not a real hardware
GPIO capture test.

## E11.1g — OneWire PA4 firmware lease before OneWireHost (DEV)

The actual `src/labmate_onewire_hw.c` now keeps its original
local LabMate communication-owner exclusion and additionally
tries an exact firmware
`FURI_HAL_LEASE_ONEWIRE_PA4` **before**
`onewire_host_alloc(&gpio_ext_pa4)` or GPIO operations.
An unpatched SDK, a busy firmware lease or a conflicting
Pulse/Monitor PA4 cooperative owner refuses START without
host allocations, pin writes or electrical resets. Successful
operation holds the lease through the full 800-ms conversion
wait, result polling and host STOP/FREE. Only then is the
firmware handle released, followed by the local comm owner.
If release fails, the opaque handle and local communication
owner remain held, `firmware_release_fault` becomes sticky,
and a repeated START/STOP cannot silently reconfigure PA4.
The status is BUSY with no valid retained temperature.

The existing **real production source** native harness
`tests/test_onewire_hw.c` now includes firmware-claim mocks,
denied-before-allocation checks, STOP before release and
failed-release blocking. The special TEST_NO_LEASE mode checks
old-SDK no-device-side-effects. Original 1-Wire CRC,
DS18B20 decoding, +85°C suppression and rollover tests remain
intact. This is a **fake OneWireHost**; it is **NOT**
evidence of a physically connected DS18B20 or a positive
temperature reading. External 3.3V VDD and DQ pull-up
requirements are unchanged.

[Dedicated OneWire PA4 source + host + matched firmware/FAP
workflow](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/workflows/check-v18-onewire-pa4-lease.yml)
runs both firmware-API and missing-API native harness modes,
compiles the pinned patched Momentum firmware and one FAP,
and verifies exported ELF ABI / APPCHK. Exact passing
run/SHAs should be recorded only on success. Standard
source/Windows mock CI
[38808883732](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38808883732)
**SUCCESS** on exact code SHA
`6a9aff955c6186b834630ff21e7c6b91cb9a3fd3`.

**Firmware-global limitation:** independent Momentum 1-Wire,
GPIO and EXTI services still bypass this opt-in table.
E11 remains OPEN until native service migration, mandatory
arbitration and physical conflict/device acceptance. E10
missing historical CSV IDs remain OPEN. No device, USB,
Stable or `main` changes.

### E11.1g exact combined OneWire + firmware success (2026-10-15)

[Dedicated run 38808937140](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38808937140)
**SUCCESS**, source SHA
`ae6764074fddad014b8e538c4218024579a7c6f2`.
Both *actual production* OneWire PA4 C native harness
variants passed: experimental lease-enabled SDK and unmatched
old SDK (zero OneWireHost/pin writes). The harness validated
CRC, DS18B20 +85°C suppression, 800-ms conversion, rollover,
STOP cleanup, claimed pin before host allocation, lease
conflict, retained local/firmware owner on failed release and
no repeated release. Real pinned patched Momentum
`firmware_all fap_labmate`, `APPCHK`, ABI exports all passed.

Exact **CI-only** experimental firmware DFU SHA256:
`fa25f61010a3106b61a78443cee39eaa47cf4b5e822c2b88ccf742663c14e848`.
Exact paired **CI-only** FAP SHA256:
`1f795ff23533c3f9f03c063d231a032fa6ce88c37edb3f43e687a513cedee9bc`.
This pair is distinct from earlier Monitor/PWM experimental binaries:
**never mix different commit output pairs**, and no approval to
flash or install any of them was granted.

All host/device assertions here are against a fake OneWireHost,
not a real connected sensor, and legacy firmware services
remain uncoordinated. The follow-on static OneWire source-order
checker change SHA `56fb9c60245e1d3853eef7358e7df7d8cc10e262`
is source-only; passing run 38808937140 is tied specifically
to the earlier SHA above.

## E11.1h — I2C3 PC0/PC1 shared lease and bounded HAL mutex

**Change:** The actual `src/labmate_i2c_momentum.c` adapter now
requires *both* the exported
`FURI_HAL_I2C_HAS_EXTERNAL_ACQUIRE_TIMEOUT` API and the
firmware E11 `FURI_HAL_RESOURCE_LEASE_API_V1`. A stock SDK
or a timed-only SDK cannot initiate a hardware transaction.

The `FURI_HAL_LEASE_I2C3_EXT` claim is obtained **before**
the 50 ms external I2C HAL mutex acquisition. This mask
contains I2C3 + both PC0 and PC1; a cooperative Monitor or
IRQ lease on either physical pin rejects the claim without
touching HAL. A busy HAL mutex returns BUSY and releases
only the previously acquired firmware lease. No probe is
possible unless the adapter still holds its matching lease.
On a successful scan or STOP-after-acquire the worker
releases the HAL mutex **before** its own firmware lease.
A failed firmware release leaves its handle held and marks
a sticky `release_fault`: the runtime reports FAILED instead
of successful results, retains the local communication owner,
and refuses subsequent START. No stock/unbounded HAL fallback.

**Actual-C host evidence:** three native configurations —
stock SDK, timed-only SDK, matching timed+lease SDK —
plus wrong-order probe rejection, busy pin claim, HAL mutex
denial, STOP-before-claim, STOP-after-HAL-acquire, full
112-address ACK-model scan, and failed release.
[Dedicated E11 I2C3 CI run 38812503680](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38812503680)
has a **host job SUCCESS** at code SHA
`362a06e3df6f98ac66480a3836d60c2a4aabd0dd`.
The matched pinned Momentum firmware/FAP build job has now also
completed **SUCCESS**; native host job and full firmware job both
passed for exact code SHA
`362a06e3df6f98ac66480a3836d60c2a4aabd0dd`.
The full build verified `firmware_all fap_labmate`, `APPCHK`
and exported timed I2C+lease API. Exact **CI-only, never
deployed** matched firmware DFU SHA256:
`fa25f61010a3106b61a78443cee39eaa47cf4b5e822c2b88ccf742663c14e848`.
Exact **paired I2C E11 FAP** SHA256:
`d5841525da19f906a4663bd223c7630446100e9be42782842dbf6c52edd51cdc`.
Never use a FAP from another CI run with this firmware without a new
explicit fingerprint check. The full firmware build establishes no
firmware-global mandatory owner coverage or physical I2C acceptance.

**Pinned native Momentum source review:** 
`targets/f7/furi_hal/furi_hal_serial_control.c` already
uses a centralized serial-control queue and serial
`handle->in_use` guard, and LabMate UART explicitly obtains
its handle via `furi_hal_serial_control_acquire`. That is
real native UART ownership among participating clients,
unlike direct TIM1 and GPIO paths. Unrelated drivers that
write registers without serial control can still bypass it;
do not treat this as all-hardware ownership. Pinned
`targets/f7/furi_hal/furi_hal_pwm.c` calls
`furi_hal_gpio_init_ex(PA7)` then TIM1 bus enable
without consulting an E11 claim; native GPIO init and EXTI
callback paths similarly do not recognize these leases.
**E11 global protection remains OPEN** pending chosen
mandatory interception/cooperative-service strategy and
actual physical conflict/restore acceptance. No electrical
test, deployment, new Stable, USB install or firmware flash.

## E11.1i — Native Momentum PWM service now joins lease contract (2026-10-16)

**Original v1.6 promise:** peripheral safety must coordinate outside
LabMate too. Merely adding an opt-in firmware lease table to LabMate
did not constrain native Momentum services. This stage migrates the
actual upstream native `furi_hal_pwm.c` paths, not another LabMate FAP.

The exact pinned 2026-08-18 Momentum source
`d3f89dfe2ef6b01839201598e9be1590cba80322`
is modified *only in an ephemeral CI checkout* by
`scripts/patch_momentum_native_pwm_lease.py`, after the existing
bounded I2C3, E11 firmware lease and GPIO try-add patches. The
source-patch preflight checks pinned commit, an exact allowlist of
previous changes and the supported mask definitions. It has a
read-only mode and no install or USB effects.

Actual native `furi_hal_pwm_start` now requests a shared firmware
lease **before** changing GPIO or enabling timer clocks:
`FURI_HAL_LEASE_PWM_PA7` protects TIM1+PA7 and
`FURI_HAL_LEASE_MONITOR_PA4` protects the PA4 pin on the native
LPTIM2 output. The PA4 mask intentionally has **no LPTIM2 timer bit**
in E11 v1 experimental schema; it is **pin-only arbitration**.
Denied leases or already enabled native buses cause a no-register-write
return (the old `void` start API cannot signal BUSY). Native
`set_params`/STOP refuse operations without the relevant
service-held lease. STOP cleans GPIO/bus **while still holding its
lease**, then releases the exact firmware handle. Failure to release
is sticky: retains the opaque handle and disables further
starts/set-params/stop cleanup rather than falsely surrendering
ownership. `is_running` reports this native service's own
successfully claimed active timer, not merely an unrelated TIM1
bus clock that may belong to another tool.

**Evidence:** dedicated
[run 38816202945](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38816202945)
**SUCCESS** at exactly LabMate source SHA
`382827d62618e7b07f392c2c88888b3098327fef`.
`tests/test_v18_native_pwm_lease.py` compiled and executed the
**actual patched Momentum `furi_hal_pwm.c`** against fake HAL:
native PA7 denied by Monitor, successful TIM1 claim excludes
LabMate/Monitor and allows only its own set_params/STOP, unrelated
legacy-enabled timer bus refused, PA4 denied by OneWire,
successful native LPTIM2/PA4 excludes OneWire/Monitor, and
failed release remains sticky without a second hardware write.
It also built `firmware_all fap_labmate` with `APPCHK` and
exported APIs. This **does not** prove physical output or
firmware-global arbitration.

Exact **CI-only paired firmware.dfu SHA256**:
`0b66de611dbbdaa5e360deeaedab50c23314fd15fef878f4d14b6b72847031d0`.
Exact **CI-only paired labmate.fap SHA256**:
`d5841525da19f906a4663bd223c7630446100e9be42782842dbf6c52edd51cdc`.
These two refer to this specific successful run and are
**not an install approval**. The FAP bytes may match another
non-PWM CI build, but its firmware image will NOT: never
use an old firmware fingerprint merely because FAP hashes match.

**Remaining limitations:** other direct Momentum
`furi_hal_bus_enable(TIM1/TIM2)` callers and GPIO/EXTI services
still bypass opt-in lease claims; the native PWM public API
has no per-external-client owner parameter, so this patch
does not provide full cross-caller isolation when native
clients themselves race. The already-installed firmware
does not contain this native-PWM migration. Full-system
device stress and safe rollback acceptance are still OPEN.
The archived hardware-dependent tests remain DEFERRED, not PASS.
