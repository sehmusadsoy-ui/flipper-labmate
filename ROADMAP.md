# LabMate Master Roadmap — v1.0 to v2.0

**Status:** Updated 2026-10-10 after publication of v1.6 Stable.  
**Current Stable baseline:** [v1.6 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.6), published 2026-10-10 (FAP and SHA256).  
**Previous Stable fallback:** [v1.5 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.5); v1.4 and older tags remain available.  
**Next development milestone:** v1.7 — PWM Studio and Counter. v1.6 measurement and storage logic is now frozen in the `v1.6` release tag.

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
- **Published:** [LabMate v1.5 Stable release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.5), with FAP, release notes and SHA-256. Physical-device tests were performed on the preceding development build; the final CI-produced FAP was installed afterward.
- **Known untested scenario:** Real microSD failure/recovery (e.g. read/write failures, full/corrupt/unmounted media or long blocked I/O) was **not** hardware-validated; see [v1.5 release notes](RELEASE_NOTES_v1.5.md). This is a documented limitation, not an outstanding condition requiring further v1.5 tests.

### v1.6 — Navigation, resource safety and Profiles (Stable published 2026-10-10)

- **Delivered:** Grouped navigation and modular display, resource-policy, profile and frequency-gate source modules; additional extraction of the main app core remains a future refactoring option.
- **Delivered:** GPIO/PA7 resource ownership, PWM RUN/STOP protection and release on app exit.
- **Delivered:** Adaptive HIGH PB3 TIM2 gate corrections, with real-device functional low-Hz and kHz testing.
- **Delivered:** Three CRC-validated redundant microSD Profile slots with SAVE/LOAD/DELETE and active-generator LOAD safety guard.
- **Delivered:** GitHub Actions plus checksum-verified one-command PowerShell/USB installation; normal CSV logging/history from v1.5 retained.
- **Validated:** Menus, capture, STATS/HOLD, profiles, Data Logger/History and final Stable FAP startup smoke on a physical Flipper.
- **Published:** [LabMate v1.6 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.6). Independent reference calibration and destructive SD fault-injection remain outside the demonstrated test coverage.

### v1.7 — PWM Studio and Counter

- Adjustable PWM duty cycle, custom frequency selection, and safe persistent generator control.
- Genuine event/pulse counting appropriate to the available GPIO and hardware timers.
- Push-button bounce/response testing and configurable threshold alerts.
- Validate output frequency, duty cycle, and switching behavior on device.

### v1.8 — Communication Tools

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
| v1.6 | Code/UI refactor | In progress on `v1.6-dev` (development only) |
| v1.7 | PWM Studio and Counter | Planned |
| v1.8 | UART, I²C, possible 1-Wire tools | Planned |
| v1.9 | Logic Scope and Signal Compare | Planned |
| v2.0 | LabMate Ultimate / Signal Doctor | Planned |

The sequence above remains the agreed project roadmap. The 2026-10-09 documentation update records the completed v1.5 milestone **without changing any future version goals**. Subsequent scope changes should be explicit and agreed.
