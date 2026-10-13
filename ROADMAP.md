# LabMate Master Roadmap — v1.0 to v2.0

**Status:** Updated 2026-10-13: v1.7 Stable remains published. v1.8 coordinator refactor (PR #5), Counter STOP/RESUME (PR #6), and the UART minimum milestone (PR #7) are merged into development `main`; **I²C Explorer is next**. UART physical DROP/independent timing are documented limitations; no v1.8 release yet. v1.9 remains mandatory before v2.0.  
**Current published Stable:** [v1.7 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.7), original tag `d0e1bc6a95b257841533f0aa8745e3a79bbc8dcd`; updated, on-device-tested PWM Studio label FAP from source `0aeb0ca7ceba092c8adb6e44add0a2212cae1a74`, SHA256 `A0B305E5FD8D71C85C51480EE06A8B7E5EBD5BEE0E82935B0ED3B7E74E7EBCEA`. No new version or tag was created.  
**Previous Stable fallback:** [v1.6.1 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.6.1), [v1.6 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.6), and older unchanged releases.  
**Previous pre-release:** [v1.7 RC1](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.7-rc1) remains available at unchanged source `d55eec03`.
**Validation:** v1.7 refactored Stable Candidate passed 36/36 user-reported device regressions (7B screenshots); exact final `v1.7` FAP passed Test 7G 4/4 device smoke; Test 7H PowerShell `-Channel RC1 -VerifyOnly` passed; approved Stable release CI passed. Published `-Channel Stable -VerifyOnly` and actual `-Channel Stable -Port COM7` USB installation both passed on Windows 2026-10-12; a separate post-reinstall on-screen/data smoke passed 4/4 user-reported Flipper checks (v1.7 label, PWM STOP, Profile S1, historical CSV). No new version was created. **Current development: v1.8 Communication Tools**, coordinator refactor, Counter STOP/RESUME and first UART milestone all integrated into `main`; I²C Explorer is next. No v1.8 release has been published; next **v1.9 Logic Scope and Signal Compare**, then **v2.0 Ultimate**.

## Vision

Turn LabMate into an **electronic technician's digital pocketknife** on Flipper Zero: a practical, portable instrument for measuring, recording, visualizing and diagnosing 3.3 V digital signals. Prioritize real troubleshooting value, reliable measurements, readable controls, and small-device performance over unnecessary feature count.

## Official version milestones

### v1.0 — First GPIO diagnostic toolkit (Stable published 2026-10-01)

- **Delivered:** First LabMate Stable release for Flipper Zero with GPIO Monitor (HIGH/LOW, edge count and LIVE/HOLD), Frequency Meter, Pulse Analyzer and Signal Generator.
- **Delivered:** PC1 rising-edge frequency input with high-resolution `DWT->CYCCNT` timing; Pulse Analyzer HIGH/LOW/PERIOD/DUTY readings; TIM2-based PA7 square-wave generation at fixed 50% duty and 1/2/5 Hz presets.
- **Validated:** On-device PA7-to-PC1 loopback gave 1.00, 2.00 and 5.00 Hz readings for the respective generator presets; Pulse Analyzer functionality was also checked.
- **Stability decision:** Runtime frequency input switching was deliberately disabled in v1.0; PC1 was the fixed input.
- **Published:** [LabMate v1.0](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.0) with the original `labmate.fap`.

### v1.1 — Hardware frequency counter and PWM expansion (Historical milestone 2026-10-05)

- **Delivered:** Dual Frequency Meter inputs: LOW on PC1 using GPIO period timing, and HIGH on PB3 using the TIM2_CH2 hardware edge counter.
- **Delivered:** LEFT/RIGHT mode selection and mode-specific GPIO cleanup/reset.
- **Delivered:** PA7/TIM1 hardware PWM Signal Generator with 15 frequency presets from 1 Hz through 50 kHz at fixed 50% duty, replacing per-edge generator interrupts.
- **Validated:** Development/build and device checks were recorded with Momentum Firmware API 87.1; 3.3 V-compatible GPIO signals only.
- **Release status:** Described in [CHANGELOG.md](CHANGELOG.md); unlike v1.0 and v1.2, no separate v1.1 GitHub Release is currently listed.

### v1.2 — Dashboard and UI polish (Stable published 2026-10-05)

- **Delivered:** Compact dashboard-style menu, per-tool icons, clearer selection highlighting and a visible application version indicator.
- **Delivered:** LIVE/HOLD and RUN/STOP badges, improved key hints and redesigned Frequency Meter, Generator and About screen layouts.
- **Retained:** LOW PC1 / HIGH PB3 measurement paths, PC1-based Pulse Analyzer functionality and PA7 hardware PWM presets from 1 Hz to 50 kHz.
- **Published:** [LabMate v1.2 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.2) with a prebuilt FAP for the tested Momentum Firmware environment.

### v1.3 — Interrupt capture and stability (Stable published 2026-10-08)

- **Delivered:** Rising/falling GPIO interrupt capture for Pulse Analyzer HIGH/LOW/PERIOD/DUTY, plus averaged high-frequency readings and improved display refresh.
- **Delivered:** Pulse capture pin choices PC0, PC1, PB2 and PA4, avoiding conflicting or reserved interrupt lines.
- **Delivered:** Faster HIGH PB3 hardware-counter refresh (about 100 ms), GPIO interrupt edge cleanup, and running Generator frequency changes without stop/restart freezes.
- **Validated:** Flipper loopback functionality up to 50 kHz with 3.3 V-compatible signals; observations were functional checks, not independent calibration.
- **Published:** [LabMate v1.3 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.3).

### v1.4 — MIN/MAX statistics and UI stability (Stable published 2026-10-08)

- **Delivered:** Frequency Meter LOW PC1 and HIGH PB3 measured MIN/MAX, UP reset and HOLD/LIVE history preservation; input loss no longer erased previous extrema.
- **Delivered:** Pulse Analyzer MIN/MAX statistics for HIGH/LOW/PERIOD/DUTY with reset controls and five-sample median filtering of high-frequency extrema.
- **Delivered:** Clearer 128×64 screen layout and rate-limited redraws to reduce USB-connected UI stalls.
- **Validated:** Device loopback checks at 1, 20 and 50 kHz, selected statistics/hold controls, and a five-minute USB-connected navigation session; not an external calibrated accuracy claim.
- **Published:** [LabMate v1.4 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.4), with FAP and SHA-256 file.

### v1.5 — Data Logger and Log History (Stable published 2026-10-09)

- **Delivered:** CSV logging to microSD for FREQ/PC1 LOW, FREQ/PB3 HIGH and PULSE/PC1 with one sampled measurement per second.
- **Delivered:** START/STOP and BACK-to-save controls, file finalization, periodic synchronization and status/error feedback where failures are detected.
- **Delivered:** Read-only Log History browser for up to 32 recent numbered CSV sessions.
- **Validated:** A recorded CSV imported successfully in LibreOffice Calc; **Microsoft Excel was not independently tested**.
- **Delivered:** Rate-limited records, with no microSD file writes from GPIO interrupt handlers or on each high-frequency signal edge.
- **Deferred:** Microsoft Excel CSV open/analysis was not verified because Excel
  is not available in the current operator environment. LibreOffice Calc import
  succeeded; see [deferred compatibility checks](docs/DEFERRED_HARDWARE_TESTS.md).
  No paid Excel purchase is required for the current Stable maintenance.
- **Published:** [LabMate v1.5 Stable release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.5), with FAP, release notes and SHA-256. Physical-device tests were performed on the preceding development build; the final CI-produced FAP was installed afterward.
- **Known untested scenario:** Real microSD failure/recovery (e.g. read/write failures, full/corrupt/unmounted media or long blocked I/O) was **not** hardware-validated; see [v1.5 release notes](docs/releases/RELEASE_NOTES_v1.5.md). This is a documented limitation, not an outstanding condition requiring further v1.5 tests.

### v1.6 — Navigation, resource safety and Profiles (Stable published 2026-10-10)

- **Delivered:** Grouped navigation and modular display, resource-policy, profile and frequency-gate source modules; additional extraction of the main app core remains a future refactoring option.
- **Delivered:** GPIO/PA7 resource ownership, PWM RUN/STOP protection and release on app exit.
- **Delivered:** Adaptive HIGH PB3 TIM2 gate corrections, with real-device functional low-Hz and kHz testing.
- **Delivered:** Three CRC-validated redundant microSD Profile slots with SAVE/LOAD/DELETE and active-generator LOAD safety guard.
- **Delivered:** GitHub Actions plus checksum-verified one-command PowerShell/USB installation; normal CSV logging/history from v1.5 retained.
- **Validated:** Menus, capture, STATS/HOLD, profiles, Data Logger/History and final Stable FAP startup smoke on a physical Flipper.
- **Published:** [LabMate v1.6 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.6). Independent reference calibration and destructive SD fault-injection remain outside the demonstrated test coverage.

### v1.6.1 — Maintenance and verified Stable (published 2026-10-10)

- **Delivered:** Additional capture ownership, GPIO/EXTI release and low/high frequency reliability hardening, plus modular logger and pulse/frequency math extraction.
- **Validated:** Physical Gate A (8/8) and Gate B (6/6) on RC1 source; final INFO follow-up (3/3) on Stable source. These were not independent metrology calibration.
- **Published:** [v1.6.1 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.6.1) from `bc63271a`; release assets and checksum remain unchanged.
- **Version label maintenance:** A later `v1.6.1-dev` build corrected the device display/manifest version without replacing the published Stable artifact. That locally installed build is the source baseline for `v1.7-dev`.
- **Deferred to v1.7:** extraction of remaining physical capture drivers and stronger centralized GPIO/TIM/EXTI ownership, alongside the official v1.7 functional scope.

### v1.7 — PWM Studio and Counter (Stable published 2026-10-12)

- **Delivered in RC1:** adjustable PWM duty (5–95%), STOP-only CUSTOM
  1–50,000 Hz, persistent in-app generator RUN and STOP on full exit.
- **Delivered:** genuine PB3/TIM2 edge Event Counter, PC1 Button Analyzer,
  and four visual Threshold Alert sources.
- **Validated:** user-reported 3.3 V Flipper loopback checks for representative
  frequencies/duty, Pulse timing, Counter, Threshold, Logger/History and
  Profiles. Specific Profiles issue fixed and 16/16 targeted device checks PASS.
  Final release FAP SHA256 matches the tested Profiles-fix artifact.
- **Still NOT TESTED:** real mechanical button bounce/settle,
  independent calibrated PWM voltage/frequency/duty/OFF measurement,
  destructive SD failure cases and exhaustive extremes. These stay on the
  living [hardware test backlog](docs/DEFERRED_HARDWARE_TESTS.md).
- **In-place UI label maintenance, 2026-10-12:** changed displayed
  OUTPUT tool and About guide from Signal Generator to PWM Studio;
  device-tested 4/4 PASS, CI 2/2 PASS, published FAP and SHA256 replaced
  in the existing v1.7 release. The original v1.7 tag stays unchanged;
  asset provenance and the superseded hash are in the release notes.
- **Stable delivered:** measurement/logger/alert code modularization,
  release-verified GitHub-to-USB installer, 36/36 user-reported candidate
  regressions plus 4/4 exact final FAP smoke checks and real Windows
  RC1 verify-only installer PASS. Official non-prerelease `v1.7` tag,
  `labmate.fap` and checksum published; previous releases untouched.
  Missing physical contact, calibrated scope and destructive SD tests
  remain explicitly deferred.

### v1.8 — Communication Tools

- **Completed groundwork (PR #5, no release):** Split the old ~1,200-line
  `labmate.c` into a thin app coordinator, capture transitions, view,
  deferred storage and per-screen input modules. R1–R10 operator-reported
  Flipper device regression and main CI both passed.
  [Refactor test record](docs/V1_8_DEV_NOTES.md).
- **Merged development milestone (PR #7, not released):** UART Terminal USART
  13/14, bounded RX and explicit TX editor. SDK/host CI PASS; operator
  reports U1–U8 8/8, ESP32 external E1–E6 6/6, baud-retention SR1-R1,
  high-rate ST2 and controlled real-HAL UART BUSY Probe 2/2 PASS.
  Physical UART RX buffer overflow `D>0`, same-screen baud recovery,
  independent calibration and external-service contention remain
  unverified. [UART test plan](docs/V1_8_UART_PLAN.md) ·
  [device evidence](docs/V1_8_UART_ESP32_TEST.md) ·
  [integration risk acceptance](docs/V1_8_UART_ACCEPTANCE.md).
- **Next new instrument after UART device PASS:** I²C Explorer.
- 3.3 V-compatible **UART Terminal** for development and diagnostics.
- **I²C Explorer** for suitable, owned test peripherals on a safe bus.
- If feasible, basic **1-Wire sensor reading** (e.g., a supported temperature sensor).
- Test bus conflicts, input safety, timeouts and resource release.

### v1.9 — Logic Scope and Signal Compare

- Limited **digital** HIGH/LOW waveform visualization, respecting Flipper CPU/RAM/timer limits; not an analog oscilloscope.
- Timestamp/event capture with explicit memory limits, triggering and overflow indications.
- Reference signal profiles and tolerance-based comparison of real measurements.
- Do performance tests before claiming multi-channel or high-speed sampling capabilities.

### v2.0 — LabMate Ultimate

- **Signal Doctor:** rule-based and measurement-grounded digital signal diagnostics, identifying symptoms without pretending to certify a board fault.
- Unified measurement dashboard and practical troubleshooting workflows.
- Advanced signal statistics and analysis drawing on logging, event detection, and comparison.
- Integrate and polish the proven tools as one coherent professional UI.
- Release only after device-level stability, measurement and regression validation.

## Development rules

1. **One change, one test.** Implement and validate features incrementally on a development branch. Never silently change published Stable tags/releases.
2. **PowerShell + USB:** updates should build and deploy directly from the console to a single `/ext/apps/Tools/labmate.fap`; no repeated ZIP downloads or duplicate app files.
3. **Honest measurements:** show actual captured values and document when statistics are filtered. Do not artificially force ideal frequencies or duty percentages.
4. **Safety:** Flipper GPIO is for compatible **3.3 V digital signals only**. Never directly connect mains, automotive power lines, 5 V or other unknown/unsafe levels; separate conditioning/protection is required.
5. **Performance:** benchmark interrupt load, peripheral sharing, RAM usage, logging throughput and redraw latency. High-frequency measurements must not trigger SD writes at every edge.
6. **Compatibility:** verify Momentum firmware/API versions and builds; existing self-loopback tests do not constitute independent calibration.
7. **Release discipline:** compile, test on physical Flipper, review UI, run regression tests, document known limitations, then publish Stable with source, FAP and SHA-256.

## Release status

| Version | Theme | Status |
| --- | --- | --- |
| v1.3 | Foundational digital instruments | Stable published |
| v1.4 | Frequency and pulse MIN/MAX, signal-loss behavior, UI stability | Stable published |
| **v1.5** | **Data Logger, CSV recording and Log History** | **Stable published 2026-10-09** |
| v1.6 | Code/UI refactor | Stable published; v1.6.1 remains a previous Stable fallback |
| **v1.7** | **PWM Studio and Counter** | **Stable published 2026-10-12; current Stable** |
| v1.8 | Coordinator cleanup → Counter resume → UART → I²C → optional 1-Wire | PR #5/#6/#7 merged into development `main`; UART scope accepted with disclosed DROP/calibration limits; I²C not yet implemented; no v1.8 Stable |
| v1.9 | Logic Scope and Signal Compare | Planned |
| v2.0 | LabMate Ultimate / Signal Doctor | Planned |

The sequence above remains the agreed project roadmap. The 2026-10-09 documentation update records the completed v1.5 milestone **without changing any future version goals**. Subsequent scope changes should be explicit and agreed.
