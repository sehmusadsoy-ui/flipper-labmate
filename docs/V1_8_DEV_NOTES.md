# LabMate v1.8 development — Coordinator refactor first

**Status:** work in development, NOT a published v1.8 Stable or RC.
Base: clean organized `main` after PR #4; official v1.7 release/tag/assets stay unchanged.
Development branch: `dev/v1.8-coordinator-refactor`.
Screen/manifest identification: `v1.8dev` / `1.8` (test builds only).

## Why refactor first?

Earlier v1.6 and v1.7 releases extracted renderers, measurements,
GPIO drivers, CSV codec/storage and Profiles, but `src/labmate.c`
still contained roughly 1,200 lines of menu dispatch, capture lifecycle,
SD scheduling and redraw policy. Additional UART/I2C screens would
otherwise worsen a fragile coordinator.

## New owners

| Path | Responsibility |
| --- | --- |
| `src/labmate.c` | ~183-line entry, resources/queue, tick polling, stop-on-exit |
| `src/labmate_capture_session.c/.h` | Mode selection, GPIO release, stop-all capture |
| `src/labmate_input.c/.h` | Small, single dispatcher with original press vs short/long semantics |
| `src/labmate_input_menu.c` | Menu tool entry, About paging |
| `src/labmate_input_profiles.c` | Profile load/confirm/save/delete UI state |
| `src/labmate_input_history.c` | History list/detail/delete and Logger button input |
| `src/labmate_input_measure.c` | Button, Counter, Frequency, Pulse, GPIO user input |
| `src/labmate_input_output.c` | PWM Studio and Threshold Alerts input |
| `src/labmate_input_tools.h` | Typed declarations of the eleven screen handlers |
| `src/labmate_view.c/.h` | Passive draw/input queue callbacks and redraw throttling |
| `src/labmate_deferred.c/.h` | Per-tick work requests and mutex-free SD actions |

No change to TIM1 PA7, TIM2 PB3, EXTI capture, PWM duty/frequency math,
profile v1 codec, or Logger CSV record format was intended. Generator STOP
on exit and background PWM navigation behavior must remain identical.
The drawing path must never write SD or configure a peripheral.

## CI checks

- Momentum dev SDK API 87.1: compile candidate external FAP
- Portable C module and navigation tests
- Static guards: `scripts/check_v16_boundaries.py`,
  `scripts/check_v17_ui_layout.py`,
  `scripts/check_repo_layout.py`, and
  `scripts/check_v18_coordinator.py`
- Windows PowerShell mocked USB installer tests
- **No automatic publication** to Stable and no mutation of the v1.7 tag

## Real Windows/Flipper USB install: PASS (operator logs, 2026-10-12)

- Tested **exact development artifact** from CI [38294967172](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38294967172), source commit `f9bac4d30330428792bafee6df8732af46ddb273`.
- Artifact SHA256 was verified both by `Get-FileHash` and installer `-VerifyOnly`:
  `08B830A6D7FB07D065663E2BEDEBA65E389801CED5A018F6CBF54871D446B2D0`.
- `install-labmate.ps1 -Port COM7` verified the same FAP, transferred it to
  `/ext/apps/Tools/labmate.fap` (8/8 chunks at 100%), requested app close
  and relaunch, returned `SUCCESS: runfap.py exited 0` and exit code 0.
- **Result: operator-provided install/launch command PASS**, **not** the
  R1–R10 on-device functional regression. No screenshots or hardware
  measurements supplied with this installation log.
- First `gh run download` in a pre-existing temp directory returned
  `error extracting "SHA256SUMS.txt": ... file exists`. This was a
  destination collision rather than a binary checksum failure: the
  already-existing FAP passed explicit SHA256 checks before installation.
  For any fresh artifact download, use a new directory per invocation:
  `$dir = Join-Path $env:TEMP ("labmate-v18-" + [guid]::NewGuid().ToString("N"))`.
  Never ignore a failed download without independently verifying
  the exact binary hash.
- Official published v1.7 release assets and original tag unchanged.

## Physical regression checkpoint A: 4/4 PASS (user-reported, 2026-10-12)

**Exact installed candidate:** CI `38294967172`, FAP SHA256
`08B830A6D7FB07D065663E2BEDEBA65E389801CED5A018F6CBF54871D446B2D0`.
The tester submitted all four PASS responses to the initial on-device
regression screen; this is an operator report, not independent instrument
calibration or a fresh CI build.

- **A1 PASS:** `v1.8dev` version label and MEASURE, OUTPUT, RECORDS, INFO
  groups navigable. Individual access to all 11 tools remains for R10.
- **A2 PASS:** PWM Studio starts STOP; 100 Hz, 50% duty RUN/STOP works.
- **A3 PASS:** PWM RUN persists when backing into in-app menu and reopening
  PWM Studio; leaving LabMate fully stops it before next launch.
- **A4 PASS:** existing saved Profiles S1 and earlier Log History CSV
  records remain visible after install. Full profile write guards, Logger
  capture, CSV open/delete confirmations remain to test in R8/R9.

**Remaining:** complete R3 through R10 (and all 11 tool entry checks in
R10); neither overall refactor validation nor a v1.8 release is yet PASS.
Do not merge the draft PR until device regression is complete.

## Operator-required regression before merging/using as baseline

The v1.8dev FAP must be installed to a physical Flipper by a tester.
Use safe internally generated 3.3 V GPIO signals only and remove any
GPIO wiring while switching tools; no unknown voltages, 5 V or mains.

- [ ] R1: `v1.8dev` label and 4 groups **PASS** (A1); all 11 original tools reachable **PENDING** (R10)
- [x] R2: PWM Studio starts STOP, 100 Hz/50% RUN and STOP; leaving
      Studio via BACK keeps intentional in-app RUN; exiting LabMate
      stops output (**PASS** A2/A3, user-reported)
- [ ] R3: Pulse PC1 100 Hz/50% with compatible PA7 loopback; HOLD/LIVE;
      5%/95% duty cases if available
- [ ] R4: Frequency Meter PC1 low mode and PB3 high mode after selection;
      Timer/capture STOP on BACK
- [ ] R5: Event Counter PB3 RUN/STOP/RESET, no cross-tool resource leakage
- [ ] R6: Button Analyzer enters STOP, details/debounce screen without
      unexpected IRQ; no real-contact bounce claims without hardware
- [ ] R7: Threshold Alerts source, limit, ARM/ACK without crashes
- [ ] R8: Data Logger each of 3 sources records CSV, STOP closes the file;
      History opens existing/new records and BACK returns safely
- [ ] R9: Profiles S1 survives install (**PASS** A4); LOAD/SAVE/DELETE confirmation;
      active PWM/capture guard blocks profile writes
- [ ] R10: About pages, menu navigation, repeated tool entry/exit and
      application exit work without freeze; saved CSVs remain present

Tests requiring mechanical switch, calibrated timing instrumentation,
Excel or destructive SD errors remain in `docs/DEFERRED_HARDWARE_TESTS.md`.
No one should claim this refactor has passed a real device regression until
the tester submits results.

## Next features once coordinator baseline passes

1. **UART Terminal:** usable RX/TX with 3.3 V-compatible UART;
   bounded buffers, configurable baud, read-only reception by default,
   explicit TX action and deterministic resource/STOP cleanup.
2. **I2C Explorer:** compatible peripheral address scan with line/
   voltage checks, bus timeouts and deterministic release.
3. **Optional 1-Wire sensor:** only if the firmware SDK and GPIO
   ownership model support it cleanly.
4. Keep v1.9 Logic Scope and Signal Compare, then v2.0 Ultimate on roadmap.

No feature is marked delivered merely for appearing in these notes.
