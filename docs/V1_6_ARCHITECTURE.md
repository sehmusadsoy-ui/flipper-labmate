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

### Step 0 — Freeze baseline and build gate
- [x] Create a separate `v1.6-dev` branch from the latest `main` after v1.5 Stable.
- [x] Add GitHub Actions dev-only Momentum SDK build; artifact is **not** a release.
- [x] Record architecture, stable invariants and regression expectations.

### Step 1 — Extract low-risk UI primitives
- [ ] Move stateless badge, footer-key and menu icon rendering to
      `labmate_ui_primitives.c/.h`; keep menu-to-icon mapping exactly as before.
- [ ] Keep all measurement, capture, IRQ, resource and storage functions intact.
- [ ] Compile the resulting **multi-file** FAP in GitHub Actions.

### Step 2 — Extract state-aware UI drawing
- [ ] Introduce a shared internal app-state header before relocating
      state-dependent renderers.
- [ ] Move screen renderers in small groups; compare visible labels, control
      hints and fonts. Keep the UI mutex and event loop unchanged initially.

### Step 3 — Centralize resource ownership
- [ ] Create explicit ownership and cleanup rules for PC1 EXTI, PB3 TIM2 and
      PA7 TIM1, protecting against pin/timer contention and stale callbacks.
- [ ] Extract capture code without changing timing behavior; exercise
      entry/exit, HOLD/LIVE, mode changes and signal loss on hardware.

### Step 4 — Logger/history boundaries
- [ ] Separate logger and history read/write operations behind documented APIs.
- [ ] Preserve monotonic non-overwriting CSV numbering, row schema, periodic
      sync, background-UI responsiveness and bounded history enumeration.
- [ ] Do not change the on-SD `/ext/apps_data/labmate/` format.

### Step 5 — Navigation, profiles and one-command install
- [ ] Plan grouped navigation and saved measurement profiles, with backward
      compatibility and clear reset semantics.
- [ ] Supply a PowerShell + USB install script that checks its inputs and
      updates a single `/ext/apps/Tools/labmate.fap`.
- [ ] Compile, compare screens and run on-device regressions before proposing
      v1.6 Stable.

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

A root-level external app with `application.fam` includes `*.c` sources by
default, so `labmate_ui_primitives.c` will be compiled into the same FAP
without manually editing source-file masks.

GitHub Actions: `.github/workflows/build-v1.6.yml` builds Momentum dev SDK,
verifies a nonempty FAP, checks SHA-256 and uploads `labmate-v1.6-dev-fap`.
It deliberately never tags/publishes releases.

**Do not deploy development FAPs to the user's Flipper Zero without a request.**
