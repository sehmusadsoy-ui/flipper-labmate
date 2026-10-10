# LabMate

**Pocket-sized digital signal diagnostics for Flipper Zero on Momentum Firmware.**

[![Latest release](https://img.shields.io/github/v/release/sehmusadsoy-ui/flipper-labmate?label=stable%20release)](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-Flipper%20Zero-orange)
![Firmware](https://img.shields.io/badge/firmware-Momentum-blueviolet)

**LabMate v1.6 Stable is published.** The app combines a GPIO Monitor,
Frequency Meter, Pulse Analyzer, Signal Generator, CSV Data Logger,
Log History and three saved Profiles.

**[Download v1.6 Stable FAP](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/download/v1.6/labmate.fap)** ·
[SHA256 checksum](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/download/v1.6/SHA256SUMS.txt) ·
[Release notes](RELEASE_NOTES_v1.6.md) ·
[Official GitHub Release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.6) ·
[Previous v1.5 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.5) ·
[Changelog](CHANGELOG.md)

> [!IMPORTANT]
> **3.3 V GPIO ONLY.** Never connect unknown voltage, 5 V, automotive,
> mains or other high-voltage signals directly to Flipper Zero GPIO.
> Use only verified, compatible digital signals and safe equipment.

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

See the [v1.6 release notes](RELEASE_NOTES_v1.6.md) and
[physical test record](docs/V1_6_FIRST_DEVICE_TEST.md) for
test coverage, limitations and detailed outcomes.

## Instruments and pins

| Instrument | Function | GPIO |
| --- | --- | --- |
| **GPIO Monitor** | Digital HIGH/LOW, edge activity, LIVE/HOLD | Selectable GPIO; active PWM pin is reserved |
| **Frequency Meter** | Frequency with LIVE, MIN/MAX and HOLD | LOW **PC1** / HIGH **PB3** |
| **Pulse Analyzer** | HIGH/LOW time, period, duty, STATS and HOLD | **PC0, PC1, PB2, PA4** |
| **Signal Generator** | 50% duty hardware PWM with 15 presets (1 Hz–50 kHz) | **PA7 output** |
| **Data Logger** | One record per second into numbered microSD CSV files | LOW PC1 / HIGH PB3 / PULSE PC1 |
| **Log History** | Read-only browsing of up to 32 recent CSV logs | microSD |
| **Profiles** | SAVE / LOAD / DELETE in 3 slots, with CRC-checked redundant storage | microSD |

### Controls

- **Frequency Meter:** LEFT/RIGHT to select LOW PC1 or HIGH PB3,
  OK to toggle HOLD/LIVE, UP to reset MIN/MAX.
- **Pulse Analyzer:** LEFT/RIGHT to switch supported capture pins,
  OK HOLD/LIVE, UP STATS page, DOWN reset STATS while LIVE.
- **Signal Generator:** LEFT/RIGHT select preset, OK RUN/STOP.
  BACK may leave the intentionally running PWM active in the
  app; exiting LabMate turns it off.
- **Data Logger:** LEFT/RIGHT select logging mode while stopped,
  OK REC/STOP, BACK saves/returns.
- **Log History:** UP/DOWN select, OK opens read-only details.
- **Profiles:** UP/DOWN slot, LEFT/RIGHT LOAD/SAVE/DELETE,
  OK selects and confirms destructive actions, BACK cancels.

## Install v1.6 Stable

Download `labmate.fap` from the [v1.6 Stable release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.6)
and place it at `/ext/apps/Tools/labmate.fap` on a Flipper Zero
running a compatible Momentum Firmware SDK/API. Open
**Apps → Tools → LabMate**. The application shows `v1.6`.

**Optional automated PowerShell/USB install (Windows, GitHub CLI):**
`scripts/install-from-github.ps1` on `main` downloads the **published
v1.6 Stable release assets**, validates the pinned v1.6 tag and
SHA256, then installs over COM7 by default. This updates only the
external app FAP, not the Momentum firmware. Example:

```powershell
$script = "$env:TEMP\install-labmate-stable.ps1"
Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/main/scripts/install-from-github.ps1" -OutFile $script
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -Port COM7
if ($LASTEXITCODE -ne 0) { throw "LabMate Stable install failed" }
```

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
- Generator PA7 hardware PWM uses a fixed 50% duty at
  `1, 2, 5, 10, 20, 50, 100, 200, 500` Hz and
  `1, 2, 5, 10, 20, 50` kHz.
- Data Logger supports one processed sample per second.
  Log History displays recent sessions read-only.

**Device-tested:** HIGH PB3 at 1/2/10 Hz and 1/5/10/20/50 kHz
discrete generator presets; PC1 Pulse Analyzer at 100 Hz and 1 kHz
50% duty; PA7 BUSY/STOP protection; profile operations and persistence;
CSV Logger and History. The precise released v1.6 build passed a
physical startup/screen/profile/history/STOP smoke test plus
[CI regression tests](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38007158577).

**Limitations:** Built-in Flipper signal generation and measurement
share timing references, so their agreement does **not** constitute
independent calibration or certified accuracy. Measurements on every
possible external frequency, pin and duty cycle have not been
verified. Deliberate full/corrupt/unmounted microSD or abrupt power
loss fault testing has not been performed. Refer to the
[release notes](RELEASE_NOTES_v1.6.md) for details.

## Build from source

The v1.6 app is modular: keep `application.fam`, the app icon and
**all** root-level `labmate*.c` / `labmate*.h` files together.
Do not copy only `labmate.c`; it depends on the other modules.

In a matching Momentum Firmware checkout, place the sources at
`applications_user/labmate/` and build with:

```powershell
.\fbt APPSRC=applications_user\labmate
```

For reproducible Linux/Windows CI compilation, see
[the source workflow](.github/workflows/build-v1.6.yml).
The release FAP was compiled against the Momentum **dev** SDK.
Firmware/API mismatches may require a rebuild.

## Project links

- [LabMate v1.6 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.6) ·
  [Stable release notes](RELEASE_NOTES_v1.6.md) ·
  [v1.5 previous Stable](RELEASE_NOTES_v1.5.md)
- [Master roadmap](ROADMAP.md) ·
  [Changelog](CHANGELOG.md) ·
  [v1.6 device test report](docs/V1_6_FIRST_DEVICE_TEST.md)
- [Source code](labmate.c) · [App manifest](application.fam) ·
  [Historical v1.2 screenshots](screenshots/v1.2/)

## Author and license

Created by **sehma**. Licensed under the [MIT License](LICENSE).
