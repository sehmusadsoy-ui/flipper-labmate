# LabMate v1.9 — first Logic Scope capture resource gate

**Status 2026-10-18: SOURCE/DESIGN REVIEW + INDEPENDENT HOST TESTS ONLY.**
No 1.9 GUI, Flipper EXTI callback or waveform capture has yet been enabled on-device.
No v1.9 FAP has been installed or published. The final E11 matched custom
Momentum FAP and ordinary v1.8 Stable remain unchanged.

## Verified existing E11 ownership rules

Actual source read from `dev/v1.9-logic-scope`:
- `src/labmate_capture_session.c`: Pulse allowed indices
  `0/1/3/5` = **PC0/PC1/PB2/PA4**. PC3 and PB3 share EXTI3 with
  a system button path; PA6 uses EXTI6 for another system button.
  **Do not register a new interrupt on PC3, PB3 or PA6.**
- `src/labmate_resource_policy.[ch]`: a single local capture owner
  among Frequency LOW, Frequency HIGH, Pulse, Counter and Button.
  `LabMateCaptureScope` **does not exist yet**. Adding it requires
  explicit allowed-pin rules and tests, not assuming there is a free owner.
- `src/labmate_frequency_capture.c` and `labmate_button_capture.c`:
  **PC1/EXTI1** uses `FURI_HAL_LEASE_IRQ_PC1`, a non-asserting
  `furi_hal_gpio_try_add_int_callback` and a cleanup path that only
  changes GPIO/EXTI after checking its own saved firmware lease handle.
  The matching firmware must export
  `FURI_HAL_RESOURCE_LEASE_API_V1` and
  `FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK`. No safe stock-Momentum
  fallback may register the IRQ with the older assert-based API.
- `src/labmate_pulse_capture.c`: lease bits for PC0, PC1, PB2, PA4
  differ and are not interchangeable. Independent custom firmware
  clients may still bypass the experimental leases.
- `src/labmate_capture_session.c`: ownership teardown deliberately
  **does not automatically stop background PWM** on PA7/TIM1.
- `src/labmate_monitor_gpio.c`: pin-only leases protect Monitor
  against participating native clients; old foreign GPIO users may
  still ignore that lease table.

| Proposed capture input | Existing known conflicts | First v1.9 implementation decision |
| --- | --- | --- |
| **PC1 / EXTI1** | Frequency LOW, Button, Pulse, Logger Pulse/LOW; I2C PC1 SDA, pin Monitor; native JS GPIO | **Candidate for single-channel first**, but DISABLED until firmware lease+callback, I2C denial, existing local capture owner enum/STOP integration and tests are implemented |
| PC0 / EXTI0 | Pulse, I2C PC0 SCL, native serial expansion LPUART1 callback | Later after PC1 accepted; no assumed independence |
| PB2 / EXTI2 | Pulse, native NFC PA2/EXTI2, external CC1101, ICM42688P | **Do not enable** without foreign owner arbitration |
| PA4 / EXTI4 | Pulse, OneWire DS18B20, Accessor Wiegand | **Do not enable** before exclusive 1-Wire/Wiegand conflicts resolved |
| PB3 / TIM2, shared EXTI3 | Frequency HIGH, Counter, native TIM2 clients; system EXTI3 | **No scope EXTI3** |
| PC3 / EXTI3 | System button/shared EXTI3 | **No scope EXTI3** |
| PA6 / EXTI6 | System button/shared EXTI6 | **No scope EXTI6** |
| PA7 / TIM1 PWM | Active generator and native PWM; EXTI7/accessor Wiegand | **Not an input to scope** |

## First implemented unit — isolated pure-C edge recorder

`src/labmate_scope_buffer.[ch]` is a bounded producer-append buffer,
compiled by the normal `src/*.c` manifest but **not hooked to application
UI, state or GPIO IRQ** at this stage.

- Caller-supplied storage, capacity **1..256** edges, no dynamic
  allocation and no file writes.
- A real callback must pass the actual observed edge timestamp and
  level; identical consecutive levels are ignored, never fabricated.
- Trigger policies **RISING / FALLING / EITHER**. Starts ARMED,
  stores first matched edge with zero relative duration; subsequent
  edges store raw 32-bit tick and delta from preceding stored edge.
- On full capacity, retains all recorded edges unchanged, sets FULL,
  increments a **saturating** dropped-edge counter for subsequent real
  transitions. Re-arm requires STOP and an owned-IRQ teardown.
- 32-bit wrap is accounted for with unsigned modulo subtraction for
  short intervals. Zero/ambiguous gap over `0x7fffffff` ticks
  fails closed with ERROR. Since an entire counter wrap with no
  observed edge cannot be detected from two samples, a **separate
  app-thread bounded capture timeout is mandatory before hardware
  integration**.
- **Concurrency contract:** single interrupt writer. App-thread
  snapshot and arm/stop must exclude the writer's IRQ/ensure callback
  detach. A GUI mutex is **not** a replacement for EXTI IRQ masking.
- Keep heap- or static-allocated event arrays, **not** a 256-edge
  array on Flipper's small application stack. On conventional ABIs
  `LabMateScopeEdge` is around 12 bytes, so 256 events are about
  3 KiB; confirm exact `sizeof()` and available SRAM/stack in the
  actual Momentum toolchain before selecting the allocation pattern.

## Phase 1B — PC1 fail-closed resource model (2026-10-18)

Added new **pure-C-only**, host-testable model modules (the existing
v1.8/E11 capture, I2C, PWM, menu and UI sources were **NOT edited**):

- `src/labmate_scope_gate.h`, `src/labmate_scope_gate.c`:
  `labmate_scope_gate_pc1()` consults the *current* E11 local capture
  policy's **PC1 EXTI1** rule, other capture owners/active flags,
  application I2C/1-Wire communications ownership, GPIO monitor,
  active Logger/UART/counter/button and sticky release faults.
  Unsupported native `resource_lease` or non-asserting GPIO
  `try_add_int_callback` API yields **UNSUPPORTED**, not an assert-based
  callback fallback. Wrong pin yields **BUSY/INVALID**; system button
  EXTI3/EXTI6 and unreviewed other candidate pins are never offered.
  Independent PA7/TIM1 PWM intentionally remains permissible for a
  future PA7→PC1 loopback *only when other resources are free*.
- The model separates a real, nonzero firmware token, a successfully
  registered callback, configured GPIO and actual RUNNING state.
  Each state transition is allowed only after a hypothetical caller has
  **confirmed** the respective native operation. This model does not
  invoke the native operation itself and does not grant physical ownership.
- `labmate_scope_owner_stop_plan()` lists owned resources that would
  require cleanup; `stop_confirmed()` clears the handle only after
  successful callback detach, pin restoration and native lease release
  are **reported by the future driver**. A missing result latches
  `RELEASE_FAULT`, preserving the recorded handle and denying a
  subsequent capture. An incomplete cleanup must not be retried
  blindly or used to erase a foreign callback; native recovery will
  require separately verified handling.
- `tests/test_labmate_scope_gate.c` covers foreign Frequency/Counter/
  Pulse/Button ownership, I2C/1-Wire, Logger, GPIO Monitor, UART,
  stale active flags, invalid PC0/PC3/PA6/PB3/PA7 pins, missing firmware
  features, illegal lifecycle transitions, STOP/restart, failed
  callback registration cleanup, and sticky release failure.
- CI workflow `.github/workflows/check-v19-scope-buffer-host.yml`
  now includes **actual repository** E11 `labmate_resource_policy.c`
  and `labmate_comm_resource.c` in its C11 and ASAN/UBSAN link tests.

**Evidence classification:** Exact newly committed GitHub file blobs
match local C/header/test working bytes; a local strict C11 + ASAN/UBSAN
unit run **PASSED** with signature-compatible local policy doubles.
The **new live Actions job against the complete real E11 policy modules
has NOT been independently observed finishing**, so no CI PASS is claimed.
No firmware, FAP, S1 profile, historical CSV or application menu was
modified. This source-only gate does **not** constitute a native PC1
IRQ lease, physical BUSY or STOP/BACK on a device.

**Next:** add independent no-signal timeout/timebase validity gates to
bounded capture; then write the actual matched-native firmware acquire /
nonasserting callback and owned IRQ teardown path with explicit
low-level failure simulation. New FAP/hardware work needs a separate
owner-approved install scope and compatibility check.

## 2026-10-18 final local regression — exact existing E11 code, partial STOP retry

After the first ownership model, a STOP/BACK review identified two
cases that could inadvertently touch a *foreign* resource if the
application lost track of its completed cleanup steps:

1. A native lease failed **before** any GPIO callback had been registered:
   a retry must only release the held lease, not remove a nonexistent
   callback or reconfigure the unowned pin.
2. The callback was successfully detached and the owned GPIO pin
   restored, but firmware lease release failed: the next attempt must
   **only retry lease release**, not touch the already-returned pin or
   old callback a second time.

The model now stores `fault_cleanup_phase`,
`callback_detached` and `pin_restored` confirmations. Failed cleanup
retains the nonzero handle and `RELEASE_FAULT`, preventing START.
Positive cleanup confirmations are kept between attempts, and steps
not owned or already completed are excluded from subsequent plans.
This is still a **software protocol model**; future real firmware code
must obey the sequence and confirm each actual operation under IRQ
exclusion.

**Exact local source provenance (no stand-ins for this final regression):**

- New `labmate_scope_gate.h` Git blob `12d6339feb1016d200aea17a8776062659cd7ae3`
- New `labmate_scope_gate.c` Git blob `0cace12ab474aef3583e8c698b9e6173c6be9b76`
- New `test_labmate_scope_gate.c` Git blob `bf3d632296095033ecbd33dc0faae83c5df1ada4`
- Existing E11 `labmate_resource_policy.h/.c` Git blobs
  `1e9a17d3dae3d281970faf6495715056cc028709` /
  `bb3653de485878d859ffb433d8c8e023aa4d93ce`
- Existing E11 `labmate_comm_resource.h/.c` Git blobs
  `aa5ae54020c4700e5a8814ec85a16ef0820189f2` /
  `3f2e6106d3cf480f66bfc645f940ff54cf9c5cff`

All seven files were reproduced byte-for-byte locally and their Git
blob identities confirmed. The real-source gate tests ran with
`cc -std=c11 -Wall -Wextra -Werror -Wpedantic` and separately with
`-fsanitize=address,undefined`: **LOCAL HOST PASS in both modes**.
This proves the pure policy/stop model against the actual E11 C rules;
it does **not** prove real firmware lease/callback behavior. GitHub
Actions conclusion is separately **not verified** by the current
GitHub connector.

**No device write, EXTI registration, v1.9 FAP publication, Stable
replacement, source tag move, S1 Profile or historical CSV changes.**

## Phase 1C — bounded capture time supervision (2026-10-18)

The independent v1.9 buffer is now accompanied by a **pure-C app-thread
timeguard**. Added `src/labmate_scope_timeguard.[ch]` and
`tests/test_labmate_scope_timeguard.c`; the previous E11 app,
IRQ/PWM, Logger/Profile, menu and firmware files remain unchanged.

- **NO TRIGGER**, not automatically `NO SIGNAL`: after waiting for
  the first accepted real triggering edge, an expired trigger window
  reports `LabMateScopeGuardNoTrigger` (which avoids claiming there
  were no untriggered transitions).
- **QUIET**: after actual stored edges, a bounded quiet period without
  *new* edges reports `LabMateScopeGuardQuiet`. No synthetic waveform
  samples, false jitter or fake frequency values are generated.
- **DURATION LIMIT**: every capture session must terminate within
  **5,000 ms maximum**; the app must then stop and detach its own
  native IRQ callback. Until real firmware integration, this is a
  watchdog *decision only* and not a physical STOP implementation.
- **CLOCK UNSAFE**: app-thread polling gaps over **100 ms**, backwards
  or out-of-order 32-bit millisecond timestamps, or ambiguous gaps
  fail closed. Native code must independently verify DWT edge-timer
  frequency and a session duration shorter than its half-wrap period.
  An *entire* 32-bit millisecond counter wrap between missed polls
  remains fundamentally undetectable without an independent monotonic
  clock; never claim this algorithm solves that case.
- **FULL / CAPTURE ERROR / STOPPED / INVALID** remain distinct
  terminal outcomes and sticky once detected. Unexpected count
  rollback or inconsistent ARMED/RECORDING snapshots are rejected.
- All polling receives a **consistent IRQ-excluded snapshot**, runs
  on the application thread, and NEVER changes GPIO, firmware leases
  or FAP storage. Native STOP/BACK has to explicitly detach/quiesce
  the owned callback before mutating the underlying buffer. GUI
  mutex alone is insufficient for ISR synchronization.

**Local independently executed evidence (exact GitHub file blobs):**

| File | Git blob |
| --- | --- |
| `src/labmate_scope_timeguard.h` | `24496b1f7378ad78c4c73626c199e7f77cd81dc7` |
| `src/labmate_scope_timeguard.c` | `677e0baa40383167bdb0d1bbe39c831e54f46042` |
| `tests/test_labmate_scope_timeguard.c` | `0f69ef514600ae4e2d8cfbfa909cf62a15ce6ccc` |

The exact current source/test bytes were compiled against the earlier
**actual** `labmate_scope_buffer.c` in three configurations, all
**LOCAL HOST PASS**: GCC strict C11 `-O2`; GCC AddressSanitizer +
UndefinedBehaviorSanitizer `-g -O1`; and Clang strict C11 `-O2`.
Tests cover max limits and rejected bad configuration, NO TRIGGER,
QUIET after real edges, multiple accepted event snapshots, 32-bit
millisecond wrap, invalid clock gaps, backwards timestamps,
capture maximum duration, overflow/ERROR/STOPPED, invalid state and
**integration with real stored edge timestamps**. No native Flipper
SDK build, on-device timebase verification or GitHub Actions
successful conclusion is claimed.

`.github/workflows/check-v19-scope-buffer-host.yml` was extended to
compile the watchdog together with the existing edge buffer in strict
C11 + ASAN/UBSAN on the development branch. **GitHub Actions status
is still unverified** with the available connector.

**Next implementation gate:** a native **PC1/EXTI1** adapter with
version-pinned matched Momentum `resource_lease` and non-asserting
`try_add_int_callback`, sample/run/STOP under proper IRQ exclusion,
status UI and integrated host/matched-FAP build tests. A deliberate,
backed-up FAP-only Flipper test may follow **after** those pass and the
owner has reviewed the exact artifact/hash. No full firmware flash
is required or authorized as part of this host-only phase.

## Phase 1D — staged real E11 PC1/EXTI1 native adapter (2026-10-18)

**Source implementation committed, not yet linked into the app UI or
verified by a matched-Firmware FAP build.** This is an explicit
engineering checkpoint, not a physical-test PASS.

- `src/labmate_resource_policy.[ch]`: appended the distinct
  `LabMateCaptureScope` owner **after** all historical enum values.
  PC1 is the only permitted pin. Legacy Frequency, Pulse, Counter and
  Button ownership rules and indexes remain unchanged.
- `src/labmate_scope_gate.c` now checks
  `LabMateCaptureScope`, not a fake `LabMateCaptureFrequencyLow`
  request. A foreign Frequency/Pulse/Button/Counter capture blocks
  Scope acquisition; no owner is stolen.
- `src/labmate_scope_native.[ch]` stages a real PC1 callback using
  `furi_hal_resource_lease_try_acquire(FURI_HAL_LEASE_IRQ_PC1)`,
  `furi_hal_gpio_try_add_int_callback`, the owned GPIO's
  `GpioModeInterruptRiseFall`, and the actual `DWT->CYCCNT`
  timestamp. **Both patched E11 ABI compile-time feature macros
  are mandatory**. There is **NO** call to the old asserting GPIO
  callback API and **NO** safe stock-Momentum fallback.
- Callback uses only O(1) edge capture on the ISR thread. No screen,
  file, heap, locks or logging calls in the callback.
- Before starting, validates actual DWT cycle counter enablement and
  `SystemCoreClock` against the full **5-second** capture window.
  Capture duration must remain shorter than 32-bit DWT half-wrap.
  Application-thread watchdog receives IRQ-excluded snapshots.
- Source reserves **256 events** in a state object that must be
  allocated as **zero-initialized static/heap storage**, not as a
  local 3 KiB stack temporary. Native STOP quiesces the owned callback,
  clears the PC1 EXTI1 trigger, restores analog mode and releases the
  **matching** lease handle. A failed lease release remains sticky
  and cannot be erased by repeated initialization.
- `tests/mock_v19/` adds header-mocked Momentum/Furi/EXTI
  functions and intentionally injected native failures. Tests cover
  successful two-edge capture + timing, STOP/RESTART, 1-second no-trigger
  auto-STOP, 256-edge saturation auto-STOP, foreign callback, busy native
  lease, I2C ownership refusal, disabled DWT, unsafe DWT frequency,
  unsuccessful lease release and stable sticky failure. Separate
  **UNPATCHED SDK** test verifies no HAL pin mutation or IRQ
  callback registration when the native ABI is absent.
- `.github/workflows/check-v19-scope-buffer-host.yml` includes strict
  C11 and sanitizers for the matched mocked native adapter and a
  separate stock/unpatched negative build.

**Evidence classification:** GitHub *source files and test definitions*
are committed and readable on branch `dev/v1.9-logic-scope` (Draft
PR #15). **There is NO confirmed CI run on this current head.**
Do not claim mock native test PASS, matched Momentum SDK compile PASS,
GUI visibility or Flipper physical PASS until each independent gate
has been observed. The original E11 Custom prerelease, v1.8 Stable,
source tags, ordinary `main` and physical device contents are
unchanged.

**Remaining gates before asking the owner to install a new FAP:**
1. CI job actual conclusion for native fake HAL including unpatched ABI.
2. Matched Momentum SDK/FAP build including the new source module with
   `application.fam` `src/*.c`, and reproduce binary SHA256.
3. Integrate dedicated guarded local owner into old STOP/BACK/exit flow,
   128×64 live timeline renderer, START/BUSY/ERROR status and UI tests;
   keep INFO/About last.
4. Verify on-device no-signal/edge/STOP with a **separately approved,
   FAP-only** reversible test, never a forced full firmware updater.
5. Later independent waveform accuracy at the university with instructor
   and the remaining real BME280/DS18B20/SD tests as material arrives.

## Phase 1E — 128×64 real-edge plot + stateless Canvas (2026-10-18)

Added **source-only, UI-hardware-isolated** modules on the **Draft v1.9
branch**. No `labmate.c`, `labmate_internal.h`, navigation,
menu, Profile, Logger or existing E11 callbacks were changed.

- `src/labmate_scope_plot.[ch]`: choose at most the **last 64
  consecutive actually recorded edges** out of the native 256-edge
  buffer, and make at most **126 line segments**. The projector uses
  verified delta ticks to derive X coordinates in [5,122], and only
  one of two logical Y levels (HIGH=23, LOW=43). It draws each
  observed high/low interval between two real edges followed by its
  actual transition. It **does not extrapolate a waveform before the
  first or beyond the last edge**. One isolated edge is insufficient
  for a pulse duration and therefore draws no waveform.
- Full 32-bit modulo counter wrap is checked against individual
  `tick` and `delta_ticks`. Invalid/zero deltas, duplicate
  logical levels, cumulative ambiguous spans and insufficient
  capacity fail closed. Cropped windows are explicitly labeled
  `LAST64`, not represented as complete capture history.
- `src/labmate_scope_display.[ch]` is a **view-only** 128×64 Canvas
  renderer. Receives consistent, app-thread prepared geometry,
  validates its bounds **before** any waveform draw, separates
  `WAIT REAL EDGE` (live armed) from `NO TRIGGER` (terminal),
  and displays real counts plus `LIVE/HOLD/BUSY/ERR/FULL` states.
  `BUSY`, unsupported and error states cannot paint stale live
  traces; no drawing routine claims ownership of GPIO or storage.
- `tests/test_labmate_scope_plot.c` checks empty/single-edge
  behavior, exact unequal duty geometry, modulo tick wrap,
  corrupt delta/logic transitions, 64-edge maximum and array bounds.
- `tests/mock_v19/gui/gui.h` +
  `tests/test_labmate_scope_display.c` check Canvas line coordinates,
  header/footer, a real two-edge trace, BUSY suppressing trace,
  terminal NO TRIGGER without fabricated waveform, and refusal
  before drawing any malformed geometry.
- CI `check-v19-scope-buffer-host.yml` includes the two module
  suites with GCC strict C11 and ASAN/UBSAN; it is **authored, not yet
  confirmed to run** on this branch.

**Verification:** The exact GitHub blob objects were compared with
the local source bytes and matched. Local GCC -O2 strict C11,
Clang -O2 strict C11 and GCC -g -O1 ASAN/UBSAN runs all reported
**PASS** for both projector and mocked Canvas renderer, including
after the NO TRIGGER wording fix. This is neither a matched Momentum
SDK build nor a Flipper screen capture; **physical v1.9 PASS is NOT
claimed**.

**Final pending linkage:** The future app adapter must (1) take an
IRQ-excluded `labmate_scope_native_read` copying at most 64 latest
real edges, (2) project them OUTSIDE the IRQ into bounded geometry,
(3) retain coherent display status even after STOP, (4) call the
Canvas view on its normal UI draw path, and (5) use dedicated
`LabMateCaptureScope` START/STOP/EXIT routing without renumbering
historical persisted IDs or moving INFO/About from the last group.
The available exact-matched native SDK build is the next essential
gate; **do not ask the owner to replace the working E11 FAP yet**.

## Phase 1F — app menu / input / owned STOP / Canvas routing (2026-10-18)

**Latest source-stage status: integrated on Draft PR #15, NOT built as a
matched E11 firmware FAP, NOT installed or accepted on device.**

- Added `src/labmate_scope_bridge.[ch]` as an **application-thread-only**
  adapter. Source pin PC1 is fixed for the first channel; OK starts/
  stops the matched-native lease/callback, BACK stops the *owned* callback
  before returning to menu, and the existing app poll calls the native
  watchdog with actual `furi_get_tick()` converted to milliseconds by
  `furi_kernel_get_tick_frequency()`. Zero tick frequency denies start.
  Underlying edge/plot functions remain pure C. No direct GPIO/SD
  operations happen from Canvas or the bridge.
- The app mutex protects the cached screen state, and the native
  `FURI_CRITICAL_ENTER/EXIT` section takes a bounded **copy of the latest
  at most 64 IRQ-recorded edges** before the pure C plot projection.
  `scope_recent`, `scope_lines` and the 256-edge native storage are
  **embedded in `LabMateApp` allocated on heap**; not on the 4 KiB
  application call stack. Exact heap/SRAM budget still needs a real
  matched-SDK build and on-device instrumentation.
- `src/labmate_internal.h` **appends** `LabMateScreenScope` after
  legacy screens. `src/labmate_navigation.[ch]` **appends**
  `LabMateToolScope=14` after existing ID 13; the MEASURE group
  now has six tools and root **INFO/About is still last**.
  `src/labmate_input_menu.c`, `src/labmate_input.c`,
  `src/labmate_view.c` route dedicated navigation, key presses and
  Canvas. The About guide has a Scope entry; no historical Profile
  bytes or menu IDs are renumbered.
- `src/labmate_capture_session.c` calls Scope's own STOP **before**
  resetting generic capture ownership. A failed/unreleased lease
  remains sticky and blocks others; safe STOP preserves previously
  observed waveform in HOLD. The root app exit also calls the
  existing shared capture STOP, so a Scope-owned IRQ must be detached
  before application state can be freed.
- The **development-only** UI label is `v1.9DEV`, manifest FAP
  version `1.9`; the public v1.8 Stable and E11 prerelease bytes,
  tags and manifest remain entirely untouched.
- `tests/test_labmate_scope_navigation.c` pins historical IDs 0..13,
  requires Scope ID 14, checks all 15 tools occur once and verifies
  Measure scroll and final INFO/About. The development host workflow
  now compiles this test and includes explicit source-link checks
  for menu, run/poll, IRQ copy, BACK/STOP and version labeling.
  **GitHub Actions conclusion is not available** (zero visible
  runs for this development branch at the time of writing).

**Additional independent execution evidence:** The three **exact GitHub blob
bytes** for the navigation header `8e2a3cd99f364bbce6930e639640313fcc2371b0`,
navigation implementation `762571cb1b03d168330a99194929ba79a994a527`,
and navigation regression `7fce8dd497da1534ca03a1544205032b828967a4`
were reproduced in a separate local host directory, compared using
`git hash-object` (all 3 matched), then **actually compiled and run**
with GCC strict `-std=c11 -Wall -Wextra -Werror -Wpedantic -O2`
and with **ASAN/UBSAN**: BOTH **LOCAL HOST PASS**.
This is a real compiled test of the v1.9 menu ID and INFO order policy.
No Flipper firmware files or user data were written.

**Review classification:** An independent readback of current GitHub
source blobs passed **19/19 text-and-routing invariant checks** for
the staged integration, including no SD operations in the bridge and
backward-stable navigation indices. Those checks are **static code
consistency**, not a firmware build, a passed device test, a dynamic
on-device BUSY/STOP proof, or a claim all patched Momentum APIs link.

**Do NOT replace the owner's working E11 FAP yet.** Mandatory before
first FAP-only hardware installation:
1. Real Actions strict-GCC/mocked-native/Canvas/navigation tests PASS
   (not just authored workflow YAML).
2. Real **exact matched E11 Momentum patched SDK** compile + linkage,
   no ABI/API mismatches, FAP SHA256 and a complete provenance record.
3. Native ownership/live IRQ/draw regression plus memory/stack budgets
   independently reviewed; verify backing up current FAP, occupied
   Profile S1 and historical CSV. If a source issue is found, fix in
   Draft PR and re-run both gates.
4. First device trial: a distinct **v1.9DEV FAP-only** replacement on
   the existing verified matched firmware, PA7→PC1 at safe 100 Hz
   and 1 kHz/50% (or independent 3.3 V source), LOW/NO TRIGGER,
   buffer FULL, STOP/RESTART/BACK with no BUSY/ERR and data intact.
   No full firmware flash, no automatic SD migration.

## Phase 1G — reproducible exact E11 FAP-only review CI (2026-10-18)

New workflow:
`.github/workflows/build-v19-e11-fap-review-only.yml`

- Checks out **only** the v1.9 Draft application source and the exact
  already-used Momentum source commit
  `d3f89dfe2ef6b01839201598e9be1590cba80322`.
  Both checkouts disable persisted Git credentials.
- Reuses the **115 lines of real E11 source patch/testing steps**
  from the previous matched-firmware build (no floating Momentum
  `main`, no arbitrary ABI upgrade, no unreviewed firmware patch).
- Stages `application.fam`, the genuine icon and every
  `src/*.c`/`src/*.h` into
  `momentum-src/applications_user/labmate` and asserts both v1.9
  version labels and the git source SHA.
- Requests only `./fbt fap_labmate`, then independently hashes the
  non-empty `.extapps/labmate.fap`. It **does not** request a
  firmware updater, DFU, SD resource pack, USB, serial connection,
  installation, flash or any GitHub Release tag mutation.
- A successful build would create an expiring 7-day **REVIEW ONLY**
  Actions artifact with the FAP, SHA256SUMS, exact source+Momentum
  provenance and an explicit `DO NOT INSTALL` warning. A nonzero
  compiler/link result prevents artifact upload.
- This is **not** a tested or authorized release/install path.
  As of this document update, the live v1.9 Actions run count
  **remains 0 in the connected GitHub Actions listing**, even though
  a separate older E11 Actions job (run `39035056937`) can still be
  inspected as completed/success. The exact new FAP build and SHA256
  therefore remain **UNVERIFIED / NO-GO**.

**Operator gate:** Do not use the review FAP on the Flipper merely
because the YAML exists. First obtain actual build logs, successful
host/mocked-IRQ tests, binary hash and matched ABI review. Only
after that, back up the installed E11 FAP and preserve S1/CSV, then
authorize a reversible **FAP-only** trial. Full firmware flash is
out of scope.

## Phase 1H — E11 SDK exported-symbol and FAP ELF guard (2026-10-18)

Implemented a new **read-only, fail-closed verifier**:
`scripts/verify_v19_e11_sdk_fap.py`, plus
`tests/test_verify_v19_e11_sdk_fap.py`. This gate is wired **after**
the real `./fbt fap_labmate` step and **before** the workflow may
produce any review artifact.

- Requires **exact Momentum git baseline**
  `d3f89dfe2ef6b01839201598e9be1590cba80322`.
- Parses the actual `targets/f7/api_symbols.csv` as CSV (not a grep
  that might accept commented or disabled exports). Both the firmware
  lease acquire/release APIs and nonasserting GPIO callback API must
  have the **Function,+** exported entry. Missing or disabled exports
  yield **NO-GO**.
- Checks the patched native feature macros plus PC1 lease mask in
  native HAL headers. The staged app must display `v1.9DEV`, its
  manifest must say `fap_version="1.9"`, and its real scope driver
  must call both patched APIs without a legacy asserting callback
  fallback.
- Rejects empty, too-short, oversized, non-ELF, non-32-bit-LE and
  non-ARM FAP payloads; calculates SHA256 on the actual generated
  artifact. This is still NOT a physical RAM budget or device proof.
- The exact GitHub verifier and test blobs were re-read and compared
  to locally executed source, and **all six unit tests PASS**. Negative
  tests explicitly reject an unexported lease, missing callback macro,
  wrong app version, legacy asserting GPIO fallback, invalid ELF and
  wrong CPU architecture.
- The byte format was independently checked against the **already
  published E11 v1.8 custom FAP** (81,528-byte 32-bit ARM ELF, known
  SHA256 `393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61`).
  This verifies the parser against a real prior FAP, **NOT** that a new
  1.9 FAP was compiled.
- Existing host regression suites for navigation, plot, edge buffer,
  timeguard and PC1 gate were freshly compiled/run locally in strict
  C11: **all 5 PASS**. CI Actions runtime results for this branch are
  **not returned by the available GitHub Actions listing**, so do
  not equate these local successes with Actions PASS.

**Result:** v1.9 development source and review verification improved,
but **1.9 FAP COMPILE/LINK remains UNVERIFIED**, no 1.9 binary SHA256
exists and device installation stays **NO-GO**. No main/Stable/E11
publication, S1, CSV, firmware or device files were modified.

## Phase 1I — historical E11 failures triaged; 128-pixel UI hardening (2026-10-18)

User screenshots showed two **historical Oct 17 v1.8 E11 CI failures**
on `dev/v1.8-completion`, NOT a v1.9 build failure. Subsequent
runs of the SAME respective workflows were verified via GitHub:
- Safe two-rename audit failed on `8a5ad1e...`, then completed
  **SUCCESS** at run **39048792386** (`d68cafb...`), with a
  still later SUCCESS at run **39049675255** (`452fd48...`).
- Guarded non-app staging / CLI handshake failed on
  `34b0c87...`, then the same host-mocks workflow completed
  **SUCCESS** at run **39046391251** (`7867945...`).
These outcomes resolve the specific pictured red-history concerns,
**not** a claim all untested firmware/hardware conditions passed.

Also updated the new `src/labmate_scope_display.c` and
`tests/test_labmate_scope_display.c` in the v1.9 DRAFT branch:
- Short `NO TRG` / `UNSUP` indicators keep the longest possible
  live footer within 128 pixels even with `LAST64`; the OK/BACK
  hint is also width-bounded. The longest real status line
  (`E:256 NO TRG LAST64`) uses 19 × 6 + x=3 = **117 pixels**.
- Reject impossible total count >256, negative/invalid state tags,
  more than 64 visible entries, more than 126 line segments,
  READY plots missing any observed edge/transition, and stale
  non-READY line geometry **before drawing any pixel**.
- The mock Canvas now asserts string-cell bounds, not merely
  in-bounds start coordinates. Added negative tests for inconsistent
  edge counts, underflowed enums and stale geometry, and reinforced
  the host workflow's source-policy assertions.

**No new real Actions build result has been observed for v1.9.**
The UI changes are committed and host test code is in place; a fresh
post-change GCC/ASAN execution result still requires a run. The
prior v1.8 E11 public FAP, v1.8 Stable, `main`, and device data
remain unchanged.

## Objective acceptance before exposing the scope in menu

1. Existing FAP menu and old screen identifiers stay unchanged until
   a dedicated gated UI change is reviewed. The menu stays
   **MEASURE → OUTPUT → RECORDS → COMM → INFO** with About last.
2. Add new `LabMateCaptureScope` local owner enum **only** with
   tests for PC1 selection, denied mixed captures, release-fault sticky
   conditions, native PC1 firmware IRQ lease and owned callback teardown.
3. START must acquire required **firmware lease** before touching
   GPIO registers; use `try_add_int_callback` before pin config, fail
   closed on refusal and ensure no modification of another client.
   EXTI3 and EXTI6 must not be available.
4. Use a verified timebase and **timeout** independent of edge input,
   then test wrap and long idle. Snapshot under IRQ exclusion, render
   on app thread, never UI/storage work in IRQ.
5. Explicit RUN/ARMED/HOLD/STOP/BUSY/ERR and visible FULL/drop counter
   are required; false real-time signal values are prohibited.
6. Run strict C11 host tests with sanitizers and actual CI conclusion
   before claiming build PASS; afterward run matched Momentum FAP build
   and request separate owner approval before a device write.
7. Add regression checks for old Logger/Profile/Counter/PWM/UART paths,
   preserving user's S1 and historical CSV. Do not redo physical tests
   without shared-source changes/actual need.

**Near-term status:** First unit implemented and locally executed in a
sandbox with strict C11 and Address/Undefined sanitizers, PASS; the
new GitHub CI workflow is authored but its live result must be checked
separately. No E11 existing source files were modified by the buffer
implementation. This file is a capability/collision matrix, not a
declaration that firmware-global native service arbitration is solved.
