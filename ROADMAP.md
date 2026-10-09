# LabMate Master Roadmap — v1.5 to v2.0

**Status:** Agreed development roadmap as of 2026-10-08.  
**Stable baseline:** v1.4 (published and kept unchanged while new features are developed).  
**Active development branch:** `v1.5-dev`.  
**Release candidate:** `v1.5-rc` (tested dev functionality, RC build pending final installation).

## Vision

Turn LabMate into an **electronic technician's digital pocketknife** on Flipper Zero: a practical, portable instrument for measuring, recording, visualizing and diagnosing 3.3 V digital signals. Prioritize real troubleshooting value, reliable measurements, readable controls, and small-device performance over unnecessary feature count.

## Official version milestones

### v1.5 — Data Logger

- Record Frequency Meter and Pulse Analyzer measurements in **CSV** format to the microSD card.
- START/STOP controls; safe file finalization and useful status/error feedback.
- Browse previously saved recording sessions.
- Validate that the CSV can be opened and analyzed in Excel.
- Avoid writing to microSD from GPIO interrupt handlers or at each 50 kHz signal edge; use rate-limited sampled records.

### v1.6 — Code and UI Refactoring

- Split the current monolithic `labmate.c` into maintainable measurement, display, storage, and communication modules.
- Create centralized GPIO and peripheral-resource management so tools do not conflict over pins/timers/EXTI lines.
- Introduce a clearer grouped navigation menu and saved measurement profiles.
- Provide a reliable **one-command PowerShell + USB update/install** procedure; update the single `labmate.fap` rather than creating duplicates.
- Run freeze, resource-cleanup, and screen layout regression tests.

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
| **v1.5** | **Data Logger** | **Release candidate: final build/installation gate** |
| v1.6 | Code/UI refactor | Planned |
| v1.7 | PWM Studio and Counter | Planned |
| v1.8 | UART, I²C, possible 1-Wire tools | Planned |
| v1.9 | Logic Scope and Signal Compare | Planned |
| v2.0 | LabMate Ultimate / Signal Doctor | Planned |

The sequence above is the agreed project roadmap; changes to the roadmap should be explicit and agreed before changing version goals.
