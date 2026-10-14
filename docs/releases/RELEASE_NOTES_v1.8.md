# LabMate v1.8 Stable — Communication Tools

**Release date:** 2026-10-14
**Device / firmware:** Flipper Zero, compatible Momentum firmware
**App:** LabMate (`appid=labmate`), one `labmate.fap` in
`/ext/apps/Tools/labmate.fap`
**Developer:** Sehmus (SauronLAB); MIT License

This is the real integrated LabMate application, **not a preview FAP**.
The final Flipper on-screen version reads **v1.8**. Older v1.7 Stable
releases and historical data are retained.

## v1.8 additions

- **UART Terminal (COMM):** Flipper external USART 3.3 V UART pins
  13 (TX) / 14 (RX); selectable **9600 / 38400 / 115200 baud**, 8N1.
  Bounded receive queue and ASCII display, visible received/dropped/
  errored byte counters, explicit 12-character TX editor and CRLF,
  STOP/RUN and BACK resource release. Serial resource acquisition
  refuses an unavailable/occupied USART instead of commandeering it.
- **Counter STOP/RESUME:** preserve the live event count across
  pause/resume and keep meaningful elapsed-time handling.
- **Internal modularity:** previously monolithic coordinator was split
  into focused application, capture, GUI, input and deferred-storage
  modules without changing the single-app distribution.
- **Existing tools preserved:** GPIO Monitor, Frequency Meter,
  Pulse Analyzer, PWM Studio, Event Counter, Button Analyzer,
  Threshold Alerts, Data Logger, Log History and Profiles. Existing
  CSV logs and Profile S1 were retained in on-device tests.

## Validated release artifact

- **Exact compiled source (Git commit):**
  `02b05639364d6dd71f5eb70456eca379c59218cb`.
  The `v1.8` tag should point to this **tested source commit**;
  historical acceptance documentation merged later is not part of
  the binary and should not be interpreted as a different FAP build.
- **GitHub Actions CI:** [run 38546662091](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38546662091).
  Momentum SDK build, portable/native regressions, structural checks
  and Windows installer mock **PASS**.
- **Release asset:** `labmate.fap` from Actions artifact `labmate`
  (artifact ID `11884807062`), accompanied by `SHA256SUMS.txt`.
- **Final binary SHA256:**
  `119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0`.
  This is the **FAP SHA**, not the GitHub Actions ZIP digest.
- **Real Flipper acceptance, operator-reported (2026-10-14):**
  RC1 UI 6/6 PASS; external ESP32-S2 115200 UART TX/RX 4/4 PASS;
  PWM/Counter/Profiles/History regression 5/5 PASS; then final
  **`v1.8`-labeled FAP** smoke 4/4 PASS. Total **19/19 functional
  checkpoints**, on the physical Flipper. The final FAP was SHA256-
  verified and installed over the existing app via COM7; installer
  returned exit code 0 and requested launch. Final F1 verifies the
  displayed v1.8 label, F2 UART RX of `ESP32_READY` and STOP/BACK,
  F3 PWM START/STOP and Counter STOP/RESUME, F4 Profile S1 and old CSV
  History retained.
- **Acceptance details:** [v1.8 Stable Candidate test record](../V1_8_STABLE_CANDIDATE.md)
  and [UART device evidence](../V1_8_UART_ESP32_TEST.md).

## Explicit deferrals — NOT present in v1.8 Stable

- **I²C Explorer: deferred/not implemented.** Firmware external
  I²C acquisition can wait indefinitely on an existing bus lock
  (`FuriWaitForever`); a public bounded/cancellable ownership path
  was not validated for LabMate. Research PR #8 was closed **without
  merge**. No disconnected mock scan, disabled I²C menu item or
  separate demo is presented as a working instrument.
- **Optional 1-Wire/DS18B20: deferred/not implemented.** Exclusive
  ownership of the shared PB14 pin with other firmware uses was not
  verified. Research PR #9 was closed **without merge**.
- Prior UART aspirational features (dedicated HEX terminal, RX PAUSE
  mode, user-selectable CR/LF line endings, arbitrary editor, and
  PC bridge) are not included in this accepted minimal UART scope.

## Known limits

- Hardware UART RX queue DROP `D>0` was not observed physically;
  host stubs tested bounded overflow handling. Independent UART baud
  calibration, an unrelated active serial-owner conflict,
  long-duration endurance and exhaustive SD fault recovery were
  **not independently validated**.
- The ESP32-S2 ST2 peer treats `AT` as both an `ESP32_OK` response
  request and an **explicit bounded stress burst trigger**.
  Previously reported high-rate tests did not establish physical
  queue overflow; no new stress byte counts are attributed to
  final `v1.8` FAP testing.
- PWM/signal timing and voltage are **not independently oscilloscope
  calibrated**. Previously acknowledged limits of button mechanical
  bounce and CSV desktop import remain unless separately tested.
- **3.3 V DIGITAL GPIO ONLY.** Do not attach unknown, 5 V,
  automotive, mains or other incompatible voltages to Flipper GPIO.

## Installing / upgrading

Download **both** `labmate.fap` and `SHA256SUMS.txt` from the
[`v1.8` GitHub Release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8)
*once that release has been published*. Verify the SHA256 above,
exit any running LabMate session on Flipper, and install **only**
to `/ext/apps/Tools/labmate.fap`. The Momentum installer
`scripts/install-labmate.ps1` accepts an explicit expected SHA256
and `-Port COM7` (or the actual detected Flipper port). This FAP
does not flash or modify Flipper firmware, stored Profiles or CSV logs.
If the running LabMate cannot be closed automatically, exit it
manually and rerun the same checksum-verified installer.

Previous verified [v1.7 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.7)
remains available for rollback. No further preview/demo application
is required.

## Next milestone

**v1.9 Logic Scope and Signal Compare**, only after this v1.8 Stable
GitHub Release is actually published and verified. Deferred I²C or
1-Wire features are not silently declared complete or automatic v1.9
requirements.

© 2026 Sehmus (SauronLAB), released under the repository's MIT License.
