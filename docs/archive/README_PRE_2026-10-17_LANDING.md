<!-- Archived byte-for-byte copy of the root README before the 2026-10-17 documentation landing redesign.
     Historical version- and test-specific claims remain as originally written; use root README for current releases.
     The following content after this comment matches the former root README exactly. -->

# LabMate

**Pocket-sized digital signal diagnostics for Flipper Zero on Momentum Firmware.**

[![Latest release](https://img.shields.io/github/v/release/sehmusadsoy-ui/flipper-labmate?label=stable%20release)](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-Flipper%20Zero-orange)
![Firmware](https://img.shields.io/badge/firmware-Momentum-blueviolet)

**Current Stable: [LabMate v1.8 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8)** (published 2026-10-14; UART Terminal and Counter STOP/RESUME, with all existing v1.7 instruments retained).
**Verified v1.8 FAP SHA256:** `119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0`.
**Exact tagged source:** `02b05639364d6dd71f5eb70456eca379c59218cb`; Momentum CI [38546662091](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38546662091) and post-merge identical-FAP build [38548200859](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38548200859) PASS. **Real Flipper acceptance: 19/19 user-reported PASS** (RC1 15/15 plus final v1.8 binary 4/4). GitHub Release asset digest was verified after publication.

**[Download v1.8 labmate.fap](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/download/v1.8/labmate.fap)** ·
[SHA256SUMS.txt](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/download/v1.8/SHA256SUMS.txt) ·
[v1.8 Release notes](docs/releases/RELEASE_NOTES_v1.8.md) ·
[Acceptance record](docs/V1_8_STABLE_CANDIDATE.md) ·
[Roadmap](ROADMAP.md)

## Public download choices — 2026-10-17

Choose a build **by firmware compatibility**, not simply by the highest tag number:

| Channel | Download | Firmware scope |
| --- | --- | --- |
| **Latest ordinary Stable: v1.8** | [v1.8 Stable + SHA256](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8) | Compatible Momentum SDK/API; not guaranteed to load on official Flipper firmware or every third-party build |
| **v1.8 E11 — Custom Momentum Edition** | [E11 compatibility-limited pre-release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8-e11-custom-momentum) | **Only matching E11-patched Momentum firmware and native resources**; do not install its FAP on stock/unpatched Momentum |
| **Historical versions** | [All published Releases](https://github.com/sehmusadsoy-ui/flipper-labmate/releases) | v1.0, v1.2, v1.3, v1.4, v1.5, v1.6, v1.6.1, v1.7, v1.8 remain downloadable; v1.1 was a development milestone without an independent public v1.1 tag/release |

The E11 pre-release contains the integrated application (including I2C
Explorer and optional 1-Wire features) and a **separately marked expert-review
matched firmware package**. Owner-reported on-device UART, digital PWM,
STOP/RESTART, fresh CSV Logger and Profile SAVE/reopen/LOAD passed on one
already-matched E11 setup. Actual external I2C ACK, DS18B20 temperature,
independent calibration, global third-party peripheral coexistence and exact
firmware rollback **remain unverified**. The full updater may replace
firmware, SD resources/apps and settings; read the release's warnings
before any installation. It is **not** a universal one-click update.
The ordinary `v1.8` Stable remains GitHub's **Latest**.

Older FAPs were built against their respective Momentum API/SDK versions:
**Stable means tested for the documented environment, not compatible with
every official/custom firmware or with every later SDK**. Preserve CSV and
profile backups before changing versions.

Previous [v1.7 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.7), [v1.6.1 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.6.1) and older published releases remain preserved for rollback. No change was made to their tags or binaries. Real hardware observations do not constitute independent electrical or timing calibration.

> [!IMPORTANT]
> **3.3 V GPIO ONLY.** Never connect unknown voltage, 5 V, automotive,
> mains or other high-voltage signals directly to Flipper Zero GPIO.
> Use only verified, compatible digital signals and safe equipment.

## v1.8 Stable — published 2026-10-14

The old ~1,200-line coordinator refactor has **passed R1–R10 device
regression** (user-reported) and was merged to `main` in
[PR #5](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/5).
The app now has focused capture, input, GUI and deferred-SD modules.
**The final, physically accepted `v1.8` `labmate.fap` is published** in the
[official GitHub Release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8).
Tag `v1.8` is pinned to exact compiled source `02b05639364d6dd71f5eb70456eca379c59218cb`;
CI/host/USB verified and the user reported **19/19 physical functional
PASS** including UART receive/STOP, PWM, Counter, saved Profile S1 and
historical CSV Log History. [Acceptance evidence](docs/V1_8_STABLE_CANDIDATE.md)
· [v1.8 release notes](docs/releases/RELEASE_NOTES_v1.8.md).
Counter STOP/RESUME also passed C1–C8 real-device regressions and
merged in [PR #6](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/6).
**UART Terminal development milestone merged into `main` in [PR #7](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/7)**:
COMM menu, USART pins 13/14, bounded RX display, 9600/38400/115200 baud
and an explicit 12-character TX editor. This feature was then
physically verified in the v1.8 release candidate.
**Operator-reported device checkpoints PASS:** local U1–U8,
external ESP32-S2 UART E1–E6 at 9600/115200, corrected SR1-R1,
bounded ST2 high-rate receive and controlled USART BUSY Probe 2/2.
Physical RX overflow `D>0`, independent baud calibration and a
simultaneous unrelated serial-owner conflict are **not** claimed.
UART's first feature milestone is integrated into development `main`; its
physical RX queue overflow, calibrated timing and advanced HEX/PAUSE UI
remain explicitly outside the verified baseline. After operator review,
**I²C Explorer and optional 1-Wire were explicitly deferred** from this
v1.8 release scope because firmware-wide bus/pin ownership could not
be verified safely. Neither is presented as a functioning tool or
claimed PASS. Historical research PRs #8/#9 are closed unmerged, and
the sequential Stable gate for v1.9 is now OPEN; implementation of
v1.9 has not yet started or been merged.
No demo FAPs are required or included in v1.8.
[Refactor test record](docs/V1_8_DEV_NOTES.md) ·
[UART acceptance plan](docs/V1_8_UART_PLAN.md) ·
[real-device test log](docs/V1_8_UART_ESP32_TEST.md) ·
[UART integration acceptance/limitations](docs/V1_8_UART_ACCEPTANCE.md).

## Repository layout

The top level is intentionally short; development resources live in grouped folders.

| Path | Contents |
| --- | --- |
| [`src/`](src/) | LabMate app entry point and all C/header measurement, UI, storage and GPIO modules |
| [`docs/releases/`](docs/releases/) | Historical and current release notes; downloadable binaries remain in GitHub Releases |
| [`docs/archive/`](docs/archive/) | Old v1.5 development/draft planning notes, retained for reference |
| [`docs/`](docs/) | Hardware QA backlog, architecture, installation guide and device test records |
| [`tests/`](tests/) | Portable native C regression fixtures (not compiled into Flipper FAP) |
| [`scripts/`](scripts/) | SHA256-verified Windows USB installers and static checks |
| [`.github/workflows/`](.github/workflows/) | CI and historical release automation |
| [`dist/`](dist/) / [`screenshots/`](screenshots/) | Historical build examples and UI screenshots |

The app manifest [`application.fam`](application.fam) remains at the root and builds
`src/*.c`. The current binary is distributed from the official [v1.8 Stable release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8);
moving source folders does **not** modify any previously published tag or release asset.

## What's new in v1.7 Stable

- **PWM Studio (PA7/TIM1):** 5–95% duty in 5% steps; 15 presets
  plus STOP-only custom 1–50,000 Hz; PWM can continue across menu
  navigation, but application exit stops it.
- **Event Counter (PB3/TIM2):** actual rising-edge count, RUN/STOP/RESET
  and elapsed time (not a frequency-derived estimate).
- **Button Analyzer (PC1):** digital press/release, configurable
  5/10/20/50 ms debounce, bounce/settling/hold readouts. **Real
  mechanical contact bounce has not yet been tested.**
- **Threshold Alerts:** visual latch and acknowledgement for Frequency,
  Pulse Duty, Event Count and Button Settling.
- **Records:** read-only CSV History with explicit selected-file DELETE
  confirmation; enhanced Profiles confirmation/cancel protection.
- **Code quality:** measurement aggregation, CSV sampling, and Threshold
  validation separated from the application coordinator, alongside
  existing driver/UI/storage modules.
- **Installation:** `scripts/install-v17-from-github.ps1` selects
  published Stable or RC1, checks release/tag provenance and FAP SHA256,
  then updates only `/ext/apps/Tools/labmate.fap` over USB. On-device
  Stable-channel VerifyOnly and actual COM7 USB installation both passed
  on Windows 2026-10-12, in addition to Windows CI mock tests.
  [Installer guide](docs/V1_7_INSTALL_GUIDE.md).

On-device tests cover the Flipper's own 3.3 V digital loopback, not
independent calibrated measurements. External oscilloscope, real
mechanical switch and destructive microSD fault testing are deferred.
Keep important CSV/profile backups. Existing v1.6/v1.6.1 downloads
remain available.

## What changed in v1.6

- **Grouped navigation:** MEASURE, OUTPUT, RECORDS and INFO with clear
  input/output ownership across screens.
- **Improved HIGH PB3 Frequency Meter:** hardware TIM2 counter and
  adaptive/edge-aligned frequency gate fixed the original low-rate
  ~10× readout problem. LOW PC1 remains for low-frequency measurements.
- **Pulse Analyzer:** PC1 timing checks and HIGH/LOW/PERIOD/DUTY,
  MIN/MAX statistics plus HOLD/LIVE controls were verified on-device.
- **Profiles:** three microSD-backed slots to SAVE, LOAD or DELETE
  preferred frequency pin, pulse pin, generator preset and logger
  source. Redundant CRC32-protected A/B records safeguard normal
  saves; LOAD is refused while Generator RUN is active.
- **CSV Logger and History:** retained compatible records and
  read-only history, including older v1.5 CSV files.
- **Safer generator/resource handling:** PA7 is reserved when PWM is
  running, and a stopped generator releases the pin.

See the [v1.6 release notes](docs/releases/RELEASE_NOTES_v1.6.md) and
[physical test record](docs/V1_6_FIRST_DEVICE_TEST.md) for
test coverage, limitations and detailed outcomes.

## Instruments and pins

| Instrument | Function | GPIO |
| --- | --- | --- |
| **GPIO Monitor** | Digital HIGH/LOW, edge activity, LIVE/HOLD | Selectable GPIO; active PWM pin is reserved |
| **Frequency Meter** | Frequency with LIVE, MIN/MAX and HOLD | LOW **PC1** / HIGH **PB3** |
| **Pulse Analyzer** | HIGH/LOW time, period, duty, STATS and HOLD | **PC0, PC1, PB2, PA4** |
| **PWM Studio** | 5–95% duty, 15 presets (1 Hz–50 kHz), STOP-only CUSTOM 1–50 kHz | **PA7 output** |
| **Data Logger** | One record per second into numbered microSD CSV files | LOW PC1 / HIGH PB3 / PULSE PC1 |
| **Log History** | Read-only browsing of up to 32 recent CSV logs | microSD |
| **Profiles** | SAVE / LOAD / DELETE in 3 slots, with CRC-checked redundant storage | microSD |
| **Event Counter** | Hardware rising-edge count, elapsed time, RUN/STOP/RESET | **PB3 / TIM2** |
| **Button Analyzer** | Digital contact, press/release, debounce and metrics | **PC1** |
| **Threshold Alerts** | Visual alarm latch/acknowledge for four measurements | Measurement sources |

### Controls

- **Frequency Meter:** LEFT/RIGHT to select LOW PC1 or HIGH PB3,
  OK to toggle HOLD/LIVE, UP to reset MIN/MAX.
- **Pulse Analyzer:** LEFT/RIGHT to switch supported capture pins,
  OK HOLD/LIVE, UP STATS page, DOWN reset STATS while LIVE.
- **PWM Studio:** LEFT/RIGHT select preset, UP/DOWN adjust duty,
  OK RUN/STOP; hold OK while STOP for CUSTOM frequency editor.
  BACK may leave intentionally running PWM active in-app;
  fully exiting LabMate stops it.
- **Data Logger:** LEFT/RIGHT select logging mode while stopped,
  OK REC/STOP, BACK saves/returns.
- **Log History:** UP/DOWN select, LEFT/RIGHT switch OPEN/DELETE;
  selected-file DELETE requires an explicit second OK, BACK cancels.
- **Profiles:** UP/DOWN slot, LEFT/RIGHT LOAD/SAVE/DELETE,
  OK selects and confirms destructive actions, BACK cancels.

## Install previous v1.7 Stable (rollback)

Download the published `labmate.fap` and `SHA256SUMS.txt`
from the [v1.7 Stable release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.7),
verify the FAP hash, and install to `/ext/apps/Tools/labmate.fap`.
The device should show `v1.7`.

**Windows / PowerShell + USB (verified release channel):** download the
installer from immutable `v1.7` source, review it and run:

```powershell
$script = "$env:TEMP\install-labmate-v17-stable.ps1"
Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/v1.7/scripts/install-v17-from-github.ps1" -OutFile $script
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -Channel Stable -VerifyOnly
if ($LASTEXITCODE -ne 0) { throw "Stable verification failed" }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -Channel Stable -Port COM7
if ($LASTEXITCODE -ne 0) { throw "Stable USB installation failed" }
```

The installer is release/checksum-verified and replaces one FAP,
not the device firmware. `-VerifyOnly` never installs. The
**Stable-channel live-USB installation PASS** on operator-provided Windows
logs (2026-10-12). Subsequent user-reported post-reinstall Flipper
checks passed 4/4: version `v1.7`, PWM STOP, Profile S1 and CSV History
persistence. Historical
`scripts/install-from-github.ps1` is pinned to v1.6 for rollback
and should not be used as the v1.7 installer.

Requires `gh auth login` once, a matching local Momentum Firmware
checkout (default: `$HOME\Momentum-Firmware`) and a USB-connected
Flipper. Review downloaded scripts before execution. No manual ZIP
extraction is required.

Existing `/ext/apps_data/labmate/` CSV/Profile data paths are
unchanged. Back up important microSD files before maintenance or
software upgrades. Do not remove the microSD card during data access.

## Technical and validation notes

- LOW PC1 uses GPIO rising edges and the `DWT->CYCCNT` timing
  source; HIGH PB3 uses a TIM2 hardware edge counter with an
  adaptive gate.
- Pulse Analyzer captures compatible GPIO edge timings, with a
  five-sample median for high-speed MIN/MAX observations.
- Generator PA7/TIM1 PWM supports 5–95% duty in 5% increments,
  15 presets and STOP-only CUSTOM frequency from 1–50,000 Hz.
- Data Logger supports one processed sample per second.
  Log History displays recent sessions read-only.

**Device-tested:** the refactored candidate was validated through
7A–7F (36/36 operator-reported PASS) and the exact final v1.7 binary
through 7G (4/4 PASS). Published assets match the final tested FAP
SHA256. Real mechanical switch, calibrated scope and destructive SD
tests remain deferred. **Microsoft Excel CSV import is NOT TESTED;**
LibreOffice Calc import succeeded.

**Limitations:** Built-in Flipper signal generation and measurement
share timing references; agreement does **not** constitute
independent calibration or certified accuracy. External inputs and
all duty/frequency combinations are not exhaustively verified.
Deliberate full/corrupt/unmounted microSD and abrupt power loss
fault tests remain undone. See [v1.7 release notes](docs/releases/RELEASE_NOTES_v1.7.md)
and [deferred checks](docs/DEFERRED_HARDWARE_TESTS.md).

## Build from source

The **current v1.8 source on `main`** is modular: keep
`application.fam`, `labmate_10px.png` and the entire `src/` folder
together; `application.fam` compiles `src/*.c`. Historical
`v1.7` instructions can describe an older file layout. The
published E11 Custom Momentum binary requires a **matched patched firmware
ABI** and must not be rebuilt against an unrelated stock SDK.

In a matching Momentum Firmware checkout, place the sources at
`applications_user/labmate/` and build with:

```powershell
.\fbt APPSRC=applications_user\labmate
```

For reproducible Linux/Windows CI compilation, see
[the v1.7 source workflow](.github/workflows/build-v1.7.yml).
The release FAP was compiled against the Momentum **dev** SDK.
Firmware/API mismatches may require a rebuild.

## Project links

- [LabMate v1.7 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.7) ·
  [Stable release notes](docs/releases/RELEASE_NOTES_v1.7.md) ·
  [Previous v1.6.1 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.6.1)
- [Master roadmap](ROADMAP.md) ·
  [Changelog](CHANGELOG.md) ·
  [v1.6 device test report](docs/V1_6_FIRST_DEVICE_TEST.md)
- [Source code](src/labmate.c) · [App manifest](application.fam) ·
  [Historical v1.2 screenshots](screenshots/v1.2/)

## Author and license

Created by **Sehmus (SauronLAB)** — [GitHub: sehmusadsoy-ui](https://github.com/sehmusadsoy-ui). Licensed under the [MIT License](LICENSE).
