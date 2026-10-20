# LabMate v1.9 Stable — Logic Scope & Signal Compare

**Compatibility-limited Stable · Flipper Zero · E11-patched Momentum firmware ONLY**

> **IMPORTANT — NOT for ordinary/stock Momentum, stock Flipper firmware, Unleashed, Xtreme or unknown firmware builds.** This `labmate.fap` requires the custom E11 native firmware lease and nonasserting GPIO-interrupt callback APIs. A mismatch may make the app fail to start or operate safely. Verify firmware/native-resource compatibility **before** installing; never flash custom firmware or replace microSD resources merely to try this FAP. The compatible E11 custom edition is documented in [v1.8 E11 Custom Momentum](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8-e11-custom-momentum), which is explicitly **expert-review-only** for whole-firmware updates. Ordinary Momentum users should stay on [v1.8 ordinary Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8).

## Release identity

- **Tag:** `v1.9` (non-prerelease Stable **within this exact E11 compatibility profile**; deliberately **not** GitHub's default *Latest* ordinary Stable).
- **App:** LabMate `appid=labmate`, on-device path `/ext/apps/Tools/labmate.fap`; FAP-only release; **no firmware or resource updater**.
- **Exact compiled app source:** `72eb58d6c65d31f510acf6f532ee23c543a9149d` (tag MUST point to this commit, not to a later documentation-only commit).
- **E11-patched Momentum SDK source base:** `d3f89dfe2ef6b01839201598e9be1590cba80322`; SDK declared API 87.1 with additional E11 exports. This is a compatibility constraint, **not independent attestation of every deployed firmware binary**.
- **Release app asset:** `labmate.fap`; **101,468 bytes**; **SHA-256 `d8bb04cf6de6ebaa466e7487e619d9f68af21dac49df2aa51e91dfae1f9f55c2`**. Verify the exact asset before installation. `SHA256SUMS.txt` accompanies the asset.

## v1.9 — Logic Scope and Signal Compare

- **Single-channel PC1 digital Logic Scope:** bounded actual HIGH/LOW edge waveform in a separate framed 128×64 LCD viewport with dotted graticule. **Not an analog oscilloscope.** Grid is only a visual guide, not calibrated time/div or voltage/div.
- **Timestamped digital event capture:** native DWT cycle-counter timestamps for observed PC1 transitions; **256-edge static capacity**, guarded IRQ capture; automatically finishes a useful continuous capture after **32 observed edges** when polling is healthy; max **5 s** capture session, 1 s trigger wait, 200 ms quiet timeout, 100 ms maximum allowed app poll gap. Ambiguous clock, missed scheduling, buffer FULL/dropped edges and teardown faults are rejected/indicated, not used for false PASS. Current application uses trigger-on-either-edge; source buffer additionally supports rising/falling trigger filters. Does not promise independently selectable trigger mode in the UI.
- **A/B capture & Signal Compare:** two **sequential**, separately completed PC1 captures (not simultaneous channels); real frequency, duty, averaged HIGH/LOW/PERIOD and B-minus-A frequency/duty differences. Overflow/truncated or incomplete samples cannot produce valid A/B comparisons.
- **Reference compare:** 100 Hz / 50% and 1 kHz / 50% targets, frequency tolerance ±1% and duty tolerance ±2 percentage points. Uses full precision before rounding; wrong target returns FAIL, matching validated capture returns PASS, invalid/no signal never fabricate PASS.
- **UI:** Scope / Compare / Details / Reference four-page workflow; parenthesized key labels. Major application-wide visual redesign planned for **v2.0**, not claimed in v1.9.

## What was actually validated

- **Native Windows isolated SDK:** `fbt.cmd fap_labmate` linked, APPCHK and E11 SDK exported-API/FAP reviewer **PASS**. Five strict C host gates run before SDK source sync and build by the pinned build-only runner. GitHub Actions CI was disabled during this Windows cycle; **do not claim new CI PASS**.
- **Real Flipper Zero with matching E11 firmware (operator-reported screenshots):** PC1 100.00 Hz / 50.0% and 1.00 kHz / 50.0% square-wave capture; correctly measured A/B HIGH 5.00 ms and 500 µs, LOW 5.00 ms and 500 µs, PERIOD 10.00 ms and 1.00 ms; compare delta +900 Hz, 0.0% duty difference; matching-target reference PASS and wrong-target FAIL.
- **Operator-reported final resource checks:** Frequency Meter and Pulse Analyzer after Scope exit, Scope START/STOP/re-enter, BACK and resource cleanup **PASS**. No new independent serial trace was supplied for that final aggregate confirmation.
- **Full on-device active-FAP readback** and preserved previous FAP backups reported PASS by the guarded installer. No firmware flash in v1.9 deployment.

## Explicit limitations and safe installation

- **No multi-channel acquisition or high-speed sampling throughput claim.** Physical 100 Hz/1 kHz examples are validation points, not a calibrated performance envelope. IRQ/buffer edge loss or clock guard invalidates a measurement.
- No analog input measurements, ADC voltage plots, calibrated time/div or guaranteed accuracy. Independent external oscilloscope calibration and foreign-client E11 IRQ contention are **not** claimed as complete.
- Input is **3.3 V logic ONLY**; follow Flipper pin ratings and common-ground practice, never feed 5 V to a 3.3 V GPIO.
- This release contains **only an app FAP**. It does **not** include or authorize a firmware updater, SD resource cleanup, automatic installation, or migration of other apps.
- Before any app replacement, confirm matching E11 installed firmware/ABI and preserve the currently installed `labmate.fap`, existing v1.8 and E11 backups, CSV logs and Profiles. An E11-specific failure must not trigger a global firmware refresh or manifest cleanup. STOP/BACK and settings/data state should be tested after install.
- The Flipper will not magically gain the special E11 APIs by copying the FAP. If firmware compatibility is not independently known, **do not install**; remain on v1.8 ordinary Stable.
- Existing ordinary v1.8 Stable release and its download assets remain unchanged. GitHub's ordinary `Latest` designation deliberately stays with the existing ordinary-Momentum release.

**Provenance:** See `docs/V1_9_PHYSICAL_ACCEPTANCE_AND_RELEASE_GATE_2026-10-20.md` on the development branch and PR #15. This is the source/physical-evidence-backed v1.9 E11 profile, not a general compatibility certification.
