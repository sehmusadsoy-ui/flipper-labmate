# LabMate v1.6 — Architecture and incremental refactor plan

**Branch:** `v1.6-dev` (forked from the published v1.5 Stable `main` baseline).  
**Status:** Work in progress; **not Stable**, no device validation claimed.  
**Release baseline:** [LabMate v1.5 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.5).  
**Main rule:** preserve measurement and logger behavior until a dedicated regression test passes.

## Observed architecture at kickoff

The original `labmate.c` contains roughly 3,089 lines and one `LabMateApp`
structure coordinating UI state, IRQ capture, timers, pulse/frequency
statistics, PWM generator, SD logging, read-only history and the event loop.

| Component | Current implementation | Important constraints |
| --- | --- | --- |
| GPIO Monitor | Polling selected 3.3 V GPIO | Eight visible pins; no high-speed edge counting |
| Frequency LOW | PC1 GPIO rising-edge IRQ, DWT cycle timestamps | Clear stale EXTI falling trigger when switching from Pulse |
| Frequency HIGH | PB3 TIM2_CH2 hardware external counter | Keep the timer and pin ownership consistent |
| Pulse Analyzer | GPIO IRQ, average/median stats | Interrupt-capable inputs only: PC0, PC1, PB2, PA4; do not use PC3/PB3/PA6 EXTI |
| Signal Generator | TIM1/PA7 hardware PWM | 50% fixed duty; live frequency reconfiguration must not stop/restart hardware |
| Data Logger | App-loop snapshots into microSD CSV | Once per second, sync every 10 rows, all SD I/O outside IRQ and GUI mutex |
| Log History | Read-only latest 32 CSVs | Stream file reads in small chunks, no deletion |
| UI | Seven menu entries, Canvas drawing | 128×64 screen, UI mutex, pulse redraw throttling |

## Implementation sequence

The v1.6 development build is labeled `v1.6d` in the UI, with manifest version `1.6`.
This is a development designation, **not** a published v1.6 Stable release.

### Step 0 — Freeze baseline and build gate
- [x] Create a separate `v1.6-dev` branch from the latest `main` after v1.5 Stable.
- [x] Add GitHub Actions dev-only Momentum SDK build; artifact is **not** a release.
- [x] Record architecture, stable invariants and regression expectations.

### Step 1 — Extract low-risk UI primitives
- [x] Move stateless badge, footer-key and menu icon rendering to
      `labmate_ui_primitives.c/.h`; keep menu-to-icon mapping exactly as before.
- [x] Keep all measurement, capture, IRQ, resource and storage functions intact.
- [x] Compile the resulting **multi-file** FAP in GitHub Actions (first UI-only extraction passed build + SHA-256 check; final version-label build verified separately).

### Step 2 — Extract state-aware UI drawing
- [x] Introduce `labmate_internal.h` to share the exact existing app-state
      structure and enums between modules, without changing member layout or IRQ/storage ownership.
- [x] Extract About, Log History and Log Detail drawing to
      `labmate_ui_screens.c/.h` with their existing labels, fonts and read-only behavior.
      The shared `ui_draw_header()` helper now lives in `labmate_ui_primitives.c`.
- [x] Move Main Menu, GPIO Monitor and Frequency Meter drawing (including
      display-only frequency formatting) to `labmate_ui_screens.c`.
- [x] Move Signal Generator drawing to the same UI module, retaining the
      single existing preset-frequency array as shared immutable data.
- [x] Move Pulse Analyzer LIVE and MIN/MAX drawing plus display-only pulse
      formatting to `labmate_ui_screens.c`.
- [x] Move Data Logger status dashboard drawing to `labmate_ui_screens.c`.
      Preserve the existing `pulse_cycles_to_us()` calculation in the core and
      expose a single shared declaration; no duplicate conversion routine.
- [ ] Run device-level visual and navigation regression: labels, font sizes,
      control hints, HOLD/LIVE transitions and logger/history screens. Keep the
      existing UI mutex and event loop unchanged.

### Step 3 — Centralize resource ownership
- [x] Perform source audit of TIM1/PA7, TIM2/PB3, PC1 and Pulse EXTI
      ownership; document potential background-PWM versus GPIO Monitor
      PA7 reconfiguration conflict in [`V1_6_RESOURCE_OWNERSHIP.md`](V1_6_RESOURCE_OWNERSHIP.md).
- [x] Implement pure, host-testable PA7 policy in `labmate_resource_policy.c/.h`:
      reserve PA7 for background PWM, skip it during GPIO Monitor navigation,
      fall back to PC1 on entry and guard `gpio_release()` from overriding PWM.
- [x] Display `PA7 BUSY` in the GPIO Monitor while PWM is active; preserve
      the generator's existing background RUN/STOP semantics.
- [x] Add host-native test cases for both directions, wraparound, generator
      ON/OFF and old PA7 selection; keep the device regression pending.
- [x] Consolidate the existing capture teardown into `capture_stop_all()`
      for Frequency switching, Pulse pin changes, Logger capture shutdown,
      BACK and app exit. Preserve the old active flags, IRQ timing and
      independent PWM background behavior; compile-only until device tests.
- [ ] Create explicit ownership and cleanup rules for PC1 EXTI, PB3 TIM2 and
      PA7 TIM1, protecting against pin/timer contention and stale callbacks.
- [ ] Extract capture code without changing timing behavior; exercise
      entry/exit, HOLD/LIVE, mode changes and signal loss on hardware.

#### Capture ownership: initial exclusive-claim stage

- [x] Add `LabMateCaptureOwner` state for Frequency LOW (PC1), Frequency
      HIGH (PB3/TIM2), and Pulse (PC0/PC1/PB2/PA4).
- [x] Reject overlapping capture starts and wrong-pin requests before
      reconfiguring GPIO/EXTI/TIM2; clear capture ownership in each stop path
      and the shared teardown.
- [x] Extend native C tests with pin/owner/active-flag matrices and add CI
      static checks for the three capture start paths.
- [x] Keep a separate `capture_pin_index` for the GPIO actually armed by
      LOW/Pulse callbacks, so IRQ read/detach cannot accidentally follow the
      on-screen GPIO selection.
- [x] Display `ERR` on Frequency/Pulse when the capture policy rejects a
      request; display `CAPTURE BLOCKED` in Logger. Do not mislabel policy
      refusal as a microSD failure.
- [x] Require owner, selected pin, armed pin and active flags to match before
      creating a new Logger CSV. Lack of a signal is still recordable as
      `valid=0` and does not trigger this rule.
- [x] Test pin/owner/active-flag consistency in host-native C tests; compile
      source and run SHA-256 check in Momentum SDK CI.
- [ ] Physical device verification of all transitions, Pulse HOLD/LIVE,
      128x64 status badges and Data Logger recording is still pending.
- [ ] Real low-level acquisition failure reporting and recovery remain
      unresolved: Momentum GPIO callback add/enable, GPIO init and TIM2
      bus enable return `void`, so the policy gate does NOT detect hardware
      failures or provide automatic hardware rollback.

### Step 4 — Logger/history boundaries
- [ ] Separate logger and history read/write operations behind documented APIs.
- [ ] Preserve monotonic non-overwriting CSV numbering, row schema, periodic
      sync, background-UI responsiveness and bounded history enumeration.
- [ ] Do not change the on-SD `/ext/apps_data/labmate/` format.

### Step 5 — Navigation, profiles and one-command install
- [x] Add four-level root categories (MEASURE, OUTPUT, RECORDS, INFO)
      with nested access to the original seven tools; keep the same tool IDs
      and instrument START/STOP paths. BACK from a tool returns to its group,
      BACK from a group returns to root, BACK from root exits the app.
- [x] Cover all seven unique tool routes, selection wrapping and invalid
      groups with a host-native C test and a shared renderer/input mapping.
- [x] Define and test a portable, CRC32-protected 32-byte profile codec:
      three named-by-slot future presets, explicit v1 schema, generation
      counter, input validation and strict corruption rejection.
- [ ] Integrate actual microSD dual-copy load/save, UI slot selection,
      confirmation and safe overwrite/reset semantics. The codec alone
      does NOT save or restore settings on the Flipper.
- [ ] Perform real-device visual/navigation regression before v1.6 Stable.
- [x] Add a SHA256-verified local-FAP PowerShell installer (scripts/install-labmate.ps1)
      with a fixed /ext/apps/Tools/labmate.fap USB destination.
- [x] Add Windows mock transport tests for hashes, argument order and errors.
- [ ] Independently validate installer and updated development FAP on Flipper.
- [ ] Compile, compare screens and run on-device regressions before proposing
      v1.6 Stable.

## Automated development guards

`scripts/check_v16_boundaries.py` runs before the Momentum SDK compile in
`.github/workflows/build-v1.6.yml`. It verifies the nine renderer interfaces,
absence of direct hardware/SD calls from the screen drawing module, and
presence of the expected measurement, GPIO and logger entry points. This is
static inspection only, **not a hardware-level guarantee**. Build jobs still
produce a development FAP and a matching SHA-256; they do not publish
Stable artifacts.

## PA7 ownership test limitation

The PA7 conflict is now guarded at the C source level, with tests that run
on a desktop compiler and a static source boundary check. Only the policy
logic can be verified without the Flipper hardware; confirming that PWM
continues running while GUI navigation avoids PA7 still requires a
real-device regression. Remaining centralized ownership for PC1 IRQ, PB3
TIM2 and Pulse EXTI is not implemented yet. See
[`V1_6_RESOURCE_OWNERSHIP.md`](V1_6_RESOURCE_OWNERSHIP.md).

## Regression gate for every device-changing step

1. GPIO Monitor reacts to a 3.3 V test signal and BACK releases resources.
2. Frequency Meter PC1 LOW, PB3 HIGH, MIN/MAX, HOLD/LIVE, and mode switching.
3. Pulse Analyzer HIGH/LOW/PERIOD/DUTY and MIN/MAX, including UP/DOWN and BACK.
4. Generator PA7 RUN/STOP, frequency changes while running and safe cleanup.
5. Logger START/STOP/BACK, two distinct files, CSV data rows and ten-row sync.
6. Log History selection and read-only details, existing files preserved.
7. No crashes, frozen menus, duplicate FAP entries or unexpected GPIO reconfiguration.

**Known limitation carried forward:** physical microSD failure recovery
(full/corrupt/unmounted media, I/O blocking and unexpected power loss) was not
validated on the v1.5 release. Do not claim this is solved by a refactor.
**Electrical safety:** Flipper digital GPIO signals must remain 3.3 V-compatible.

## Build

The explicit `sources=["*.c"]` in `application.fam` compiles only
root-level C app modules into the FAP, including
`labmate_ui_primitives.c`, `labmate_ui_screens.c` and
`labmate_resource_policy.c`. This intentionally excludes
`tests/test_resource_policy.c.inc` from firmware linking. The firmware
manifest's original default wildcard was `*.c*`, which also matched
the host-only test fixture and caused an intermediate development
link failure.

GitHub Actions: `.github/workflows/build-v1.6.yml` builds Momentum dev SDK,
verifies a nonempty FAP, checks SHA-256 and uploads `labmate-v1.6-dev-fap`.
It deliberately never tags/publishes releases.

**Do not deploy development FAPs to the user's Flipper Zero without a request.**

## Step 2 initial source-boundary audit

The internal state types, `LabMateScreen` / `LabMateLoggerSource` enums and
the state layout have been transferred verbatim into `labmate_internal.h`.
The app lifecycle, UI mutex and all measurement, logger and history file I/O
logic remain in `labmate.c`. The new screen-rendering module only **reads**
the snapshot displayed by the existing canvas callback; no storage or timer
operations are performed from `draw_about`, `draw_history` or
`draw_history_detail`.

The UI section shrank from 2,964 to approximately 2,677 lines in
`labmate.c`.
The subsequent extraction of all nine screens leaves the current app core at
2,098 lines, with 704 lines in the screen renderer module.
The displayed numbers are line counts, not proof of code correctness. Purely moving code does not prove behavior is identical: the
CI build is a compile/link check; **Flipper on-device screen regression
remains pending for v1.6-dev**.

Main Menu, GPIO Monitor, Frequency Meter and Signal Generator rendering
have now been moved as independent read-only screens. Frequency MIN/MAX
formatters stay with the display. GPIO labels use a single shared immutable
table, and the PWM generator preset table remains owned by `labmate.c` but
is exposed read-only to the display; no hardware-generation call was moved.
A brief intermediate CI failure (legacy Pulse renderer still referring to
its old private `gpio_names`) was corrected by sharing that table. The
corrected three-screen build passed the Momentum SDK CI compile and FAP
checksum checks.

Pulse Analyzer and Data Logger rendering are now also migrated: all nine
screen renderer entry points are in `labmate_ui_screens.c`, with declarations
in `labmate_ui_screens.h`. The screen drawing module is passive; the IRQ,
timer, generator controls, CSV writes and history reads remain in the app core.
The original `pulse_cycles_to_us()` calculation stays in `labmate.c` and is
shared via `labmate_internal.h` to avoid diverging numeric conversions.

**Next major milestone:** audited GPIO/EXTI/timer ownership and module
boundaries, with on-device regressions before claiming v1.6 stability.
Do not pull IRQ handling or storage writes into the render module.

## Most recent development verification

Commit `fd42a8c` (not a Stable release) completed the CI pipeline at
[Actions run 37991404581](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/37991404581):
- Architectural boundary validation, including IRQ pin tracking.
- Host-native C pin/owner/flag mismatch tests.
- Momentum development SDK multi-file FAP compilation.
- FAP existence/SHA-256 validation and dev-only artifact upload.

**What CI does not prove:** correct signal frequencies/duties on a real
Flipper, complete interrupt cleanup during all mode transitions, absence
of physical resource conflicts, actual SD-failure behavior, and correctness
of 128x64 text layout. A firmware HAL call returning `void` cannot be
converted into a reliable rollback-capable success/failure result without
a supported additional signal.

## Verified local FAP installation helper (development)

Run one command in PowerShell from the v1.6-dev checkout with a local FAP
and a trusted matching SHA256SUMS.txt beside it:

    .\scripts\install-labmate.ps1 -FapPath 'C:\path\labmate-v1.6-dev.fap'

Alternatively pass -ExpectedSha256 followed by a trusted 64-digit hex SHA256.
-VerifyOnly checks its contents without firmware or USB. -FirmwareRoot
specifies a custom Momentum checkout (default: $HOME\Momentum-Firmware);
-Port may be auto, COM7, etc. No automatic download, building, firmware
flashing, CSV deletion or other application installation is performed.

The script rejects missing/empty/wrong-extension FAPs, absent or ambiguous
checksum entries, malformed hashes, SHA256 mismatches, unsafe cmd.exe paths,
missing Momentum scripts and nonzero runfap.py exits. The USB target is
always /ext/apps/Tools/labmate.fap, never a newly named duplicate.
It calls fbtenv.cmd to select Momentum's Python dependencies before runfap.py.

GitHub Actions includes a Windows mock transport test. It confirms script
argument order and failure propagation WITHOUT a connected Flipper. Physical
Flipper install and app regressions remain pending; this script has NOT
been deployed to the user's device.

## Windows mock transport CI caveat

The initial Windows test run verified all intended cases, including a
SHA256 mismatch and a mocked Python transport exit code 23, but GitHub
marked the job failed because the intentionally nonzero final native
exit status remained in PowerShell's LASTEXITCODE. The test now resets
that native process status **after checking** the failure is nonzero.
This does not suppress any failed assertion and does not alter the
installer's failure reporting. Check the latest CI for final results.

## Grouped navigation (v1.6-dev, physical regression pending)

Root groups: MEASURE (GPIO Monitor, Frequency Meter, Pulse Analyzer),
OUTPUT (Signal Generator), RECORDS (Data Logger, Log History), INFO (About).
The original seven entry IDs are unchanged and reused by the renderer
and input handler through labmate_navigation.c/.h.

UP/DOWN wrap in the current group; OK enters the selected group or launches
the selected instrument; BACK leaves a group or exits at the root. A tool's
existing BACK-to-menu behavior now lands inside its current group.
Generator background PWM policy, frequency capture ownership, logger SD
writes and stored CSV files are unchanged by the grouping code.

Portable test tests/test_navigation.c.inc exhaustively verifies mappings,
invalid group/index behavior and wrapping on groups with 1, 2 or 3 items.
The 128x64 row/padding/font result and back-navigation must still be
verified on the physical device. Saved profiles remain **not implemented**.

## Saved measurement profiles: format-only groundwork

`labmate_profiles.c/.h` provides a deterministic 32-byte binary codec
for three future profile slots. Each populated slot stores preferred Frequency
pin (PC1/PB3), Pulse EXTI pin (PC0/PC1/PB2/PA4), Generator frequency-preset
index (0..14) and Data Logger mode (LOW/HIGH/PULSE); it deliberately does not
store or auto-start any active PWM or capture. The header includes magic,
schema version, slot count, generation and reserved bits; CRC32 detects
truncated or corrupted data. The decoder rejects wrong/unknown versions,
invalid pins, out-of-range values, noncanonical empty slots and bad CRC.
Decoding never partially updates the caller's profile state when invalid.

Potential future persistence: alternating `profiles_a.bin` and
`profiles_b.bin` files, keeping one previously valid copy when updating the
other, with generation comparison and recovery rules. This design is NOT YET
connected to microSD APIs; no such files are currently created by LabMate.
Never claim saved profiles are usable until atomic-ish file load/save,
error handling, UI confirmation and on-device testing are completed.
