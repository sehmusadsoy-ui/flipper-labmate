# LabMate v1.8 — I²C Explorer: Compatibility and Safety Gate

**Status (2026-10-13): HAL-free scan/lifecycle models (G2/G2b) CI PASS; passive result presentation and paging model (G2c) committed with CI PENDING. No connected I²C hardware driver, real Flipper UI screen, actual scan, installed I²C-capable app or physical I²C PASS exists.**  
**Development isolation:** `dev/v1.8-i2c-explorer` branched from `main` after [UART PR #7](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/7) merged. The published v1.7 Stable release is excluded from this work.

## Goal and initial testable scope

An explicit, **read-only device-address explorer** for a user-owned, known-safe **3.3 V I²C peripheral**. Do not advertise generic device identification or arbitrary write/register access. The first milestone is **bounded manual scan → results → STOP/BACK → resource cleanup**, not a simulated list of detected devices.

### Source/compatibility facts checked

- Upstream Flipper firmware `dev` uses `furi_hal_i2c_handle_external`, acquires/releases it via `furi_hal_i2c_acquire/release`, and exposes `furi_hal_i2c_is_device_ready(handle, encoded_addr, timeout_ms)`: [upstream I²C HAL header](https://github.com/flipperdevices/flipperzero-firmware/blob/dev/targets/furi_hal_include/furi_hal_i2c.h) and [implementation](https://github.com/flipperdevices/flipperzero-firmware/blob/dev/targets/f7/furi_hal/furi_hal_i2c.c).
- External I²C peripheral is configured on **I2C3**, pins **PC0 (SCL)** and **PC1 (SDA)**, GPIO alternate-function open-drain, nominal **100 kHz** by upstream firmware [bus config](https://github.com/flipperdevices/flipperzero-firmware/blob/dev/targets/f7/furi_hal/furi_hal_i2c_config.c). External header mapping is **pin 16 / C0 = SCL; pin 15 / C1 = SDA** ([official Flipper Wi-Fi Devboard header schematic](https://cdn.flipperzero.one/Flipper_Zero_WI-FI_Module_V1_Schematic.PDF), connector pins 15=PC1 and 16=PC0; [Flipper app wiring corroboration](https://catalog.flipperzero.one/application/6a78beb42c28780510a289df/page)).
- **Important:** the above is upstream reference source, **not proof of exact Momentum SDK API 87.1 ABI**. Check the actual Momentum development headers/external symbol export and compile a dedicated isolated candidate before producing scanner hardware calls.
- In upstream `furi_hal_i2c_acquire`, the bus uses a mutex with **FuriWaitForever**. The `is_device_ready` timeout applies to transaction waiting **after** acquisition; it is **not** an ownership-lock timeout. Never promise an immediate BUSY refusal or implement the scanner on the GUI thread with this blocking acquire until a verified bounded ownership strategy exists.

## Momentum firmware source verification — G1 partial, physical/SDK build not yet tested

**Confirmed in public [Next-Flip/Momentum-Firmware `dev`](https://github.com/Next-Flip/Momentum-Firmware)** on 2026-10-13 (source review only):

- [Momentum F7 I²C config header](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/targets/f7/furi_hal/furi_hal_i2c_config.h) explicitly declares external `furi_hal_i2c_handle_external`, **I2C3**, **PC0 SCL**, **PC1 SDA**, nominal **100 kHz**, and floating pins on release.
- [Momentum I²C HAL header](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/targets/furi_hal_include/furi_hal_i2c.h) declares `acquire`, `release`, and `is_device_ready`. [Momentum F7 API export list](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/targets/f7/api_symbols.csv) marks these **+ exported for external apps** and exports `furi_hal_i2c_handle_external`.
- [Momentum built-in GPIO I²C scanner](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/applications/main/gpio/gpio_i2c_scanner_control.c) loops seven-bit device addresses, calls `is_device_ready(&furi_hal_i2c_handle_external, i << 1, ...)`, and pairs acquire/release. This corroborates address encoding **`address_7bit << 1`** in this firmware family. **The firmware already offers a basic I²C scanner**; LabMate Explorer needs value beyond a copy of that page (e.g., integrated, bounded results, safe lifecycle, later read-only inspection).
- [Momentum I²C external bus code](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/targets/f7/furi_hal/furi_hal_i2c_config.c) confirms the external bus mutex uses `FuriWaitForever`. The official `furi_hal_i2c_acquire()` contract does **not** offer a caller-supplied timeout. This remains the **critical ownership/cancellation blocker** for a responsive integrated UI.

**Status:** source-level pin + signature + external symbol export checks **PASS**; compatibility against the *exact downloaded development SDK snapshot* and a bounded/cancelable resource-acquisition design are **PENDING**. No scan is implemented, no FAP compiled, and no device test passed.

## G2 — HAL-free scanner model implemented, local tests PASS

Files in the **I²C development branch only**:

- `src/labmate_i2c_scan.h/.c`: pure C state machine; **no I²C HAL calls**, register access, GPIO configuration, UI entry or scan timer. This file is picked up by the existing `src/*.c` build glob, but its functions are not invoked by the app yet.
- `tests/test_i2c_scan.c.inc`: native C tests for 7-bit reserved-range rejection, Momentum address encoding `addr7 << 1`, all **112** addresses from `0x08` to `0x77`, strict request/result pairing, duplicate/out-of-order rejection, empty scan completion, known sparse detection, **16** stored-result cap with accurate **112** total counter, cancel, error and fresh-start reset.
- `scripts/check_v18_i2c.py`: static guard forbidding HAL/GUI/storage/thread coupling in pure scan model.
- `.github/workflows/build-v1.7.yml`: adds the isolated I²C tests and pure-source guard to the existing Momentum FAP + Windows installer CI, and enables the dedicated I²C branch.

**GitHub Actions CI VERIFIED:** run [38450601990](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38450601990) built source commit `ebae61fc5de0d5ec2a24080bc448c03467238f56`. Development FAP build **PASS** (including native I²C scanner strict C11 compile/run, the no-HAL isolation check, legacy UART tests and Momentum SDK compile); Windows installer safety job **PASS**; v1.7 publishing job **SKIPPED**. Artifact provenance independently resolves to exactly the same source SHA. No separate local UBSan execution has been independently evidenced; an earlier claim of local UBSan PASS was not substantiated and is **withdrawn**. This build includes the HAL-free model only and does **not** link/call the actual I²C HAL. Physical I²C implementation remains blocked by G1 acquisition semantics.

**State semantics:** `IDLE` has never scanned, `RUNNING` requests exactly one address before accepting its matching result, `COMPLETE` with zero hits means no device detected only once a *real* worker has traversed all addresses, `CANCELLED` and `ERROR` retain partial results but reject further reports. A full result list displays 16 stored addresses with `total_found` and `truncated`; it never pretends the first 16 are the whole bus. This is **pure simulated state testing**, not a device discovery result.

## G1 follow-up — isolated Momentum SDK external-symbol ABI build

A new **compile/link-only** ABI probe is committed on the I²C Draft branch:

- `tests/flipper_i2c_api_probe/application.fam` builds a separate
  `labmate_i2capiprobe.fap`, not the production `labmate.fap`.
- `tests/flipper_i2c_api_probe/api_probe.c` takes typed addresses of the
  external I²C bus handle, `furi_hal_i2c_acquire`, `furi_hal_i2c_release`
  and `furi_hal_i2c_is_device_ready` for SDK import/link validation.
  Its app entry **does not call any HAL I²C function**, acquire a bus,
  touch a pin, or scan an address.
- `.github/workflows/v18-i2c-api-probe.yml` downloads the Momentum
  development SDK, compiles the isolated probe, and verifies the
  resulting separate FAP/manifest without publishing any release.

**G1 ABI-link build PASS:** GitHub Actions
[38451777836](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38451777836)
completed the inert **separate** Momentum SDK external I²C symbol
link step and checksum proof **SUCCESS**. Artifact
`labmate-i2c-sdk-abi-probe` (ID `11840776165`) records exact
build-source SHA `14fb8be53d14f63310c8f7c1e1c064e3cf817d8e`.
This confirms the public external I²C handle/acquire/release/ready
symbols resolve with that SDK. It **does not** acquire a real bus,
exercise a connected device, or establish that the HAL acquisition is
cancelable. G1's **unbounded FuriWaitForever ownership hazard remains
OPEN** and the proof FAP must **not** be installed as a scanner.

## G1 acquisition architecture checkpoint — still blocked

Momentum's existing GPIO scanner also invokes `furi_hal_i2c_acquire`
directly. Source review found the external mutex
`furi_hal_i2c_bus_external_mutex` is an implementation variable
**not exported in the F7 API symbol list**. Thus there is currently no
verified public, timed `try_acquire` operation to use for guaranteed
responsive STOP/BACK. Checking `current_handle` is racy and **not**
sufficient, invoking bus callbacks directly would bypass ownership
invariants, and killing an indefinitely blocked worker could leak
mutex/ISR/pin resources. **None are accepted solutions.**

**Next design work:** keep all bus I/O disabled; develop an isolated
worker/UI state model with cancellation semantics that never lies
about successful hardware ownership, while investigating whether an
SDK-supported timed acquire or a documented single-owner restriction
is feasible. If no safe strategy exists, disclose the limitation and
keep hardware Explorer gated instead of adding a freezing scan button.

## G1 decision record — no public bounded-acquire API verified

A second exact-source review of **Next-Flip/Momentum-Firmware `dev`**
confirmed the following implementation facts:

- [`targets/f7/furi_hal/furi_hal_i2c.c`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/targets/f7/furi_hal/furi_hal_i2c.c):
  `furi_hal_i2c_acquire()` invokes the bus lock callback unconditionally,
  does not take a timeout parameter and then assumes exclusive handle
  ownership. It performs no caller-configurable timed wait.
- [`targets/f7/furi_hal/furi_hal_i2c_config.c`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/targets/f7/furi_hal/furi_hal_i2c_config.c):
  the external I²C3 bus lock calls
  `furi_mutex_acquire(furi_hal_i2c_bus_external_mutex, FuriWaitForever)`.
- [`targets/f7/api_symbols.csv`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/targets/f7/api_symbols.csv):
  external bus handle and public I²C acquire/release are exported, but
  **the external mutex object is not**. No exported public
  timeout/try-acquire counterpart was identified.
- Our inert Momentum development SDK ABI probe already **PASS**
  ([run 38451777836](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38451777836));
  it confirms exported symbols resolve, **not** that acquire is cancellable.

**Decision:** for the currently examined FAP/SKD API, a guaranteed
bounded/cancellable hardware acquire cannot be implemented through
these public calls alone. Accessing private mutex state, checking
`bus->current_handle` without locking, overriding bus callbacks,
forcibly terminating a blocked worker or taking raw PC0/PC1 without
I²C ownership are **rejected** as race/resource-hazard workarounds.
The bounded STOP-and-exit guarantee required for LabMate Explorer's
integrated live hardware scan remains **G1 BLOCKED**.

The built-in Momentum GPIO scanner is a separately maintained firmware
feature; the presence of that existing scanner does not grant LabMate
a timed I²C bus-acquisition API. Any future change to firmware or
supportable SDK API requires a **separately reviewed compatibility
decision**, not a silent modification to the published v1.7 Stable
or to the user's Momentum installation.

Until that blocker changes, build **HAL-free UI presentation and
regression tests only**. Do not expose a functioning-looking SCAN
button, open the I²C data bus, fake detected addresses, or treat host
scan simulation as Flipper physical PASS.

## G2c — passive results/pagination model (CI PENDING)

The dedicated I²C branch now contains `src/labmate_i2c_present.h/.c`,
a **read-only view snapshot** generated from an app-thread-owned
`LabMateI2cControl` state. It contains **no Flipper Canvas/UI
binding, physical bus access, thread synchronization or hardware
scanner**. Planned 128×64 screen implementation is separate.

- Distinguished statuses: **NOT SCANNED / WAIT BUS /
  STOP PENDING / SCANNING / RELEASING / RESULTS / NO DEVICES /
  CANCELLED / ERROR**. Importantly **NO DEVICES** only occurs
  when a logically completed scan has also reported actual release,
  not when an unrun/empty/pending scan contains zero results.
- Preserve measured model counts and show at most **four stored
  addresses per page**; page selection clamps to an existing page
  and an overfull count cannot read beyond 16 saved results.
  Keep total found count and a truncation indicator; never pretend
  those 16 saved entries are the full bus when `total_found > 16`.
- A `model_quiescent` flag indicates only logical state, **not proof
  that a real worker joined or physical HAL bus release occurred**.
- `tests/test_i2c_present.c.inc` tests idle/wait/STOP states, full
  112-address negative result only *after* completion, paging,
  truncation, partial cancellation, and error/restart.
  `scripts/check_v18_i2c_present.py` forbids HAL/Canvas use and
  any premature app input/render integration. Dedicated native
  C11 compile/run and guard were added to branch CI.

**G2c GitHub CI has not yet been checked.** No I²C-capable FAP,
physical I²C read or real device detection is claimed.

## G2b — lifecycle/STOP model (HAL-free, CI PASS)

The isolated worker/UI **lifecycle state model** is now committed in
`src/labmate_i2c_control.h/.c`. It composes the already-tested pure
scanner without acquiring an I²C bus, creating threads, opening a GUI,
calling firmware services, or touching physical pins.

- Explicit states: **IDLE → AWAIT_ACQUIRE → SCANNING →
  AWAIT_RELEASE → FINISHED/CANCELLED/FAILED**.
- A STOP request during **AWAIT_ACQUIRE** leaves the operation **pending**.
  It neither reports "BUS FREE" nor permits a new scan, because the
  real SDK's `furi_hal_i2c_acquire()` can still be blocked indefinitely.
  If acquisition *subsequently returns success*, the modeled worker
  must enter **AWAIT_RELEASE without probing** and call the physical
  release path. Only a confirmed release event clears ownership.
- STOP during an in-flight probe waits for that probe's completion,
  forbids further address probes, and retains partial results.
  Errors likewise lead through confirmed release rather than
  claiming immediate success or freeing memory under a worker.
- Explicit generation tokens reject stale out-of-order events after
  restart. New START is rejected while acquire, probe or release remains
  pending. Result mapping distinguishes acknowledgment/no-ack/error.
- `tests/test_i2c_control.c.inc` covers late acquire after STOP,
  acquire refusal, full 112-address completion, in-flight cancellation,
  cancellation between probes, explicit error/release, restart,
  incorrect generation/address and invalid result values.
- `scripts/check_v18_i2c_control.py` guards the pure model and checks
  that **LabMate UI, inputs and coordinator have not hooked it up yet**.
  The v1.8 dev CI workflow was extended with a native strict C11 test
  and static guard. **GitHub CI PASS:** [run
  38459459959](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38459459959)
  completed both development FAP build and Windows installer mock with
  `success`; v1.7 release job appropriately `skipped`. Within the build,
  native G2b lifecycle tests, pure source guard, prior I²C model,
  legacy UART regressions and Momentum SDK compilation were all
  `success`. Artifact provenance source SHA is
  `a806b138ae47fd882cd8ae1394602c952f83ab6e`.
  Only this plan document changed on the branch after that tested source.
  **No physical I²C bus or HAL resource acquisition was exercised.**

**Why earlier runs displayed X:** [38459243163](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38459243163)
failed an overly literal **static-guard assertion** that looked for the
`LabMateI2cControlAwaitAcquire` token in the STOP function. The actual
native G2b lifecycle test already passed in that run; the guard was
corrected to inspect the STOP-pending semantics. Subsequent
workflows 38459271725 and 38459401288 were cancelled while newer
commits arrived; the latest complete 38459459959 is clean PASS.
Do not label the cancelled runs as hardware/software feature failures.
No attempt to mutate the v1.7 Stable release occurred.

**Crucial safety boundary:** This is a **single-threaded event protocol
model**, not an actual worker or mutex wrapper. Production work would
need to marshal worker events into the app-owned state thread; calling
these functions from unsynchronized threads is not safe. The model's
construction-time reset function is not a physical release and MUST
NOT be called on a live worker. An actual indefinitely blocked HAL
acquire would *never deliver an acquire completion*, leaving the
state **AWAIT_ACQUIRE** and preventing safe app shutdown. Thus it
**does not solve G1** or justify enabling a hardware scan. It only
specifies and tests what safe success, late cancellation and release
would look like once a bounded HAL acquire strategy exists.

## Hardware/resource rules

1. **Only known-safe 3.3 V open-drain I²C**. No 5 V pull-ups or unknown voltage on PC0/PC1. Common ground when using a supported independently powered 3.3 V peripheral. The first tests must not energize unverified accessories.
2. A valid I²C bus requires suitable 3.3 V SDA/SCL pull-ups, but their presence, value and module voltage must be **verified for the exact peripheral**. No invented wiring or claim that Flipper automatically supplies safe pull-ups.
3. PC0/PC1 are also legacy LabMate GPIO/pulse/frequency capture pins, particularly PC1. **Never run a capture owner on either pin concurrently with external I²C**, and never silently seize a pin or interrupt in use. Ensure capture STOP/release before any I²C acquisition, and restore normal GPIO availability on exit.
4. If independent PWM is still RUN, enforce a conservative explicit **SCAN DISABLED / STOP PWM FIRST** policy for the initial version; never silently stop the user's generator. Do not change TIM1 PA7, TIM2 PB3, previous UART USART 13/14 or stored Profiles/CSV.
5. ESP32 Wi-Fi Devboard and other expansion modules should be **detached** before initial I²C tests, with the Flipper/board powered off before physical removal. The previously flashed UART stress firmware does not constitute an I²C slave/test fixture.
6. Do not write to I²C device registers, flash peripherals, change firmware, or touch microSD as part of an address scan.

## Proposed scan behavior (subject to SDK and ownership gate)

- UI opens in **STOP / NOT SCANNED**; an explicit OK starts only if bus/pin ownership policy is satisfied. Back/STOP must remain responsive; no scanning or acquiring in the render/ISR callback or while holding the UI mutex.
- Only normal **7-bit addresses 0x08–0x77** in the initial scan. The upstream HAL uses the encoded address byte; verify `addr7 << 1` against actual Momentum symbols/tests **before** touching a real peripheral. Ignore reserved address space.
- Finite per-address timeout (e.g., **2 ms**, to confirm after SDK review) and bounded total scan work. No claims of precise scan latency until actual measurement. Display **NO DEVICES** rather than a fabricated PASS if no address responds. Keep maximum results bounded and page the 128×64 UI.
- Distinguish **SCAN NOT RUN**, **SCAN PASS / N found**, **NO DEVICES**, **BUSY / CANNOT ACQUIRE**, and **TIMEOUT/ERROR**. Avoid writing to peripheral memory.
- **Blocking-acquire hazard is an explicit architecture blocker:** a background worker alone does not solve cancellation if `furi_hal_i2c_acquire` waits forever. Find a safe SDK-supported limited-wait path or a documented safe restriction with no competing bus owners before building the hardware scanner. Never edit HAL internals or forcibly unlock a foreign owner.

## Ordered implementation gates

- **G0 (now):** source, header, connector and collision review; dedicated branch and Draft PR; no physical scan claim.
- **G1:** validate exact Momentum SDK `furi_hal_i2c` API/export, address encoding and bounded acquire strategy. Report unsupported patterns as blockers, not workarounds.
- **G2:** independent host tests for pure 7-bit scan progression, result bounds, stop/cancel handling, duplicate filtering and UI state.
- **G3:** isolated SDK FAP build plus static ownership checks; all existing UART/PWM/Counter/Profile/CSV regression tests stay green.
- **G4:** physical Flipper **no-peripheral** control run; no fabricated device detected. STOP/BACK, UART reentry, old tool regression PASS only when operator reports them.
- **G5:** one verified 3.3 V read-only I²C peripheral; correct address detected, result display and repeated clean STOP/exit. This requires real hardware evidence; none exists yet.
- **G6:** complete final regression and reviewed risk acceptance before I²C merge. v1.8 Stable release is separate.

**Last UART checkpoint:** [device log](V1_8_UART_ESP32_TEST.md); [accepted limits](V1_8_UART_ACCEPTANCE.md). These remain valid; do not re-run UART stress tests merely to begin I²C development.
