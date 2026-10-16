# LabMate v1.8 — Combined Software Regression Acceptance

**Date:** 2026-10-16  
**Branch:** `dev/v1.8-completion` · [Draft PR #13](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/13)  
**Decision:** **INTEGRATED HOST SOFTWARE REGRESSION PASS — RELEASE / ON-DEVICE FINAL ACCEPTANCE PENDING**.

## Reproducible test execution, source and evidence

- Verified actual GitHub Actions [run #38958856924](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38958856924), `completed / success`, on commit `111372c4772bfaa1e4579f583c931dde822808ff`.
- Run `bash scripts/run_v18_final_host_regressions.sh` from the repository on Linux with Python3 and a C11 compiler; the shell script uses only a temporary host directory and deletes it after the run.
- The [new integrated host workflow](../.github/workflows/check-v18-final-integrated-host.yml) is a branch-only `contents: read`, no-flash runner. If *any* command fails, the overall regression fails.
- The one combined suite runs the already reviewed portable native C tests and project-specific structural guards covering v1.5–v1.8 in a single green run, rather than equating their historical independent results with a modern integration test.
- The [full pinned Momentum + ONE real LabMate FAP + JS GPIO + full MNTM-012 updater build #38955881504](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38955881504) was `completed / success` on `349d717f6cde7d1a117edea0db0058e9f2a5748f`. GitHub compare from that exact source to the latest integrated test commit `111372c` showed **no changed runtime `src/`, app manifest or native firmware patch files**, only documentation, repo policy, the *new* integrated test runner and its workflow. Therefore the full FAP compilation is applicable to unchanged production-source bytes; it does not make the newer integration workflow a new firmware build or constitute on-device proof.
- Existing [E11 narrow supported-scope software sign-off](E11_SUPPORTED_SOFTWARE_SIGNOFF_2026-10-16.md) remains operative. Third-party plugin and optional-pin exceptions have not disappeared.

## Included software acceptance domains

| Development milestone | Genuine automated evidence in final green host run | What is NOT proven |
|---|---|---|
| v1.5 Data Logger + History + Profiles | Production C CSV/filename codec, persistent profile codec, menu navigation/selection, source guards for deferred SD I/O and safe history teardown | Actual microSD power-loss/full-card/corruption, Excel desktop import, preservation/restoration of specific historical deleted logs |
| v1.6 Refactoring and resource policy | Source-coordinator/module tests, app-local resource policy, capture STOP, native E11 software-evidence checks | Universal ownership of all firmware/unknown third-party hardware, physical timing and exceptional recovery |
| v1.7 Frequency/Pulse/PWM/Counter | Original C model tests for adaptive frequency, pulse math, PWM settings, counter overflow/saturation and resource isolation | Calibrated physical frequency/duty and oscilloscope measurements |
| v1.7/1.8 Button Analyzer + Alerts | Original C bounce/debounce/tick-wrap and threshold models, Button STOP/RESUME source lifecycle | Actual dry-contact bounce on latest firmware/FAP pair |
| v1.8 UART | Real UART driver C with HAL/Expansion host shims, RX queue/drop tests, bounded display text, UART resource/ISR source guard | Real new-pair 3.3V peer traffic, physical sustained overflow/serial coexistence |
| v1.8 I²C Explorer | Real bounded scan control, result paging, cancel, error, stock-firmware safe refusal and matched timed-I²C interface host shims | Physical positive ACK from a verified 3.3V I²C slave, on-device STOP/contended acquisition |
| v1.8 1-Wire Temp | Genuine PA4 session/owner driver with host OneWire HAL shims, DS18B20 CRC/resolution/temperature negative-path decoding | A real externally powered 3.3V DS18B20 conversion/CRC and timing |
| Package/provenance | Full updater archive parser/rejection unit tests, prior single matched package compile/ZIP/hash/provenance CI | New device installation, ROM boot, validated rollback |

This PASS is not evidence that every error branch of every production
tool is physically exercised, nor permission to modify user CSVs or
restore missing historical files.

## Required remaining release / hardware decisions

1. **Safe, operator-approved matched hardware acceptance:** first review exact package SHA256, provenance, rollback media and boot safety; then only with explicit separate device-operation approval, test the same exact firmware/FAP pair on Flipper with existing data backed up. The current workflow never flashes or transfers anything.
2. **Real instrument/data gate:** preserve the positive ACK and DS18B20 CRC tests as HW-06/07 pending equipment; keep calibrated PWM/button/contact, microSD failure/Excel and native cross-service RF/EXTI tests in `DEFERRED_HARDWARE_TESTS.md`. Never mark them PASS from host emulation.
3. **Operator's final integration acceptance:** test the new paired build's entire menu `MEASURE → OUTPUT → RECORDS → COMM → INFO` (About bottom), functional STOP/BACK, profiles/CSV/history preservation, logger and UART/COMM navigation, button RESUME and system EXIT, with a written pass/fail record. Earlier user-observed physical tests of a *different* candidate are historical evidence only.
4. **Only after the agreed gates:** restore the production UI label `v1.8`, record exact tested source, old vs new FAP SHA256, rebuild/verify the exact SDK-paired package, obtain explicit publication approval, and consider a controlled in-place Stable asset update. Keep the original tag ancestry, older release evidence, and published `v1.7` intact. Never silently release from a development host PASS.

**Decision now:** the full *currently feasible, equipment-free integration
test suite* is complete and green. The v1.8 **Stable promotion itself is
NOT yet authorized** by the software-only results, and v1.9 remains frozen
until the original v1.8 gate is approved or its remaining physical
limitations are explicitly dispositioned.

**Preservation:** no `main` merge, stable asset/tag mutation, microSD
modification, USB activity, firmware flash, or automatic reboot.
