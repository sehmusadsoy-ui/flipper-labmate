# LabMate v1.8 E11 — Custom Momentum Edition

Compatibility-limited LabMate v1.8 release for Flipper Zero.

**Firmware requirement:** An independently verified, matching E11-patched Momentum firmware and native resources. Ordinary stock Momentum/MNTM-012 is **not supported** by this FAP. The existing [v1.8 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8) remains the default choice for other users.

## What's included

One fully integrated LabMate v1.8 application: Frequency Meter, Pulse Analyzer, PWM Studio, Counter, Button Analyzer, GPIO Monitor, Logger/History, Profiles, UART Terminal, I2C Explorer and 1-Wire temperature. Menu groups: MEASURE, OUTPUT, RECORDS, COMM, INFO (About last). No v1.8.1 or separate demo app.

## Actual acceptance scope

On the owner's paired E11 custom Momentum/Flipper: application/UI, UART with ESP32-S2 at 115200, 100 Hz and 1 kHz 50% PWM PA7-to-PC1 Frequency/Pulse loopback, STOP/RESTART, a new CSV Logger entry readable from History, and Profile SAVE/reopen/LOAD with existing S1 and earlier records preserved — all operator-reported PASS.

Not verified on external test hardware: positive I2C device ACK, DS18B20 temperature conversion, real simultaneous foreign-client resource arbitration, independent calibration, extreme microSD fault behavior or custom firmware restoration.

## Exact source and binary hashes

Build: LabMate commit `99cb65d0194dc59d423cfa439c90618ac6b9f114`, [Actions run 39035056937](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39035056937). The final `v1.8` display label was applied in ephemeral CI staging, leaving the historical public v1.8 source tag unchanged.

- `labmate.fap` — 81,528 bytes — SHA256 `393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61`
- `firmware.dfu` — SHA256 `e7460ab56d72a77bca1c096496ee6dd6d59044bd314ad4cb78559c3aeff72c8b`
- `js_gpio.module` — SHA256 `fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a`
- `firmware-full-update.tgz` — SHA256 `cd12be2a85512dcd360e6b93e027fa2ad9136a76602ba01036dc235b7a804dee`

## Compatibility, data and recovery

Before installing, users must determine whether their firmware provides the matching E11 native ABI. A normal Momentum firmware version name alone is insufficient. An unmatched application may not work.

Users considering a compatible installation should independently back up and verify their files and settings, including historical Logger CSV and Profiles, and retain the original working FAP. The full Momentum update path can replace bundled microSD resources and unrelated apps. **An exact restoration of the previous custom firmware has not been demonstrated.** The ordinary Momentum MNTM-012 recovery package is not byte-identical to the previously running patched firmware. Do not assume recovery or universal safety.

The E11 full updater artifact is intended for expert review of the matching build, not an unattended installer. If the compatibility or recovery risk is unacceptable, continue using the existing public v1.8 Stable.

References: [E11 test record](https://github.com/sehmusadsoy-ui/flipper-labmate/blob/dev/v1.8-completion/docs/V1_8_E11_FINAL_RELEASE_GATE_2026-10-17.md) and [scope decision](https://github.com/sehmusadsoy-ui/flipper-labmate/blob/dev/v1.8-completion/docs/V1_8_E11_DISTRIBUTION_SCOPE_DECISION_2026-10-17.md).

**Release channel:** `v1.8-e11-custom-momentum`, GitHub prerelease for custom firmware compatibility. The published original v1.8 and v1.4 Stable tags and binary assets stay unchanged.
