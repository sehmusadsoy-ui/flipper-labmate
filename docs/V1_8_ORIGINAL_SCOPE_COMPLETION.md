# LabMate v1.8 — Original Roadmap Completion (active work)

**Decision:** Operator requested returning to the original 2026-10-08
v1.8 Communication Tools milestone instead of treating its I²C and
feasible 1-Wire tasks as complete, and including the already physically
tested Button Analyzer STOP/RESUME fix in **v1.8**, not a separate
v1.8.1 release. Restore and finish original requirements first;
do not start v1.9 work. Date: 2026-10-14.

**Published history is immutable evidence:** The public original
v1.8 Stable binary/tag remains valid for its explicitly reduced
scope. Do not rewrite its past build or test results. The requested
future *in-place v1.8 update* can replace the downloaded FAP/assets
only after a new exact-source build, checksum check, and device
regression, with old/new artifact SHA and source provenance recorded.
Do not silently retarget the original tag. No binary update yet.

**One single production application:** `appid=labmate`,
`/ext/apps/Tools/labmate.fap`. The current active work branch
`dev/v1.8-completion` uses the visibly non-Stable label
`v1.8DEV` until original release gates are satisfied.
No standalone preview FAP is an acceptable feature substitute.

## Scope versus verification

| Original milestone | Source implementation | Optional later instrument-grade verification |
| --- | --- | --- |
| v1.5 CSV/History | Implemented and tested; actual Excel import outstanding | Actual Microsoft Excel, destructive SD failures |
| v1.6 code/UI/peripheral architecture | App/driver/GUI/SD/input modules and app-local capture owner implemented | Firmware-wide exclusive resource safety across unrelated system services is not yet proven |
| v1.7 PWM/Counter/Button/Alerts | Implemented, physical functional smoke; Button STOP/RESUME improvement integrated in this working branch | Calibrated PWM, mechanical contact bounce, exhaustive 3.3V extremes |
| v1.8 UART | Implemented and external-peer tested | Physical RX DROP and calibrated baud |
| v1.8 I²C Explorer | **HARDWARE-READY CONDITIONAL CODE, NOT YET OPERATIONAL ON STOCK FIRMWARE:** live HAL ACK adapter, threaded worker, local resource owner, COMM screen and result paging compile into the single development FAP. Stock firmware reports FW API rather than touching PC0/PC1. | Patched Momentum firmware/SDK **actual build** and then user physical safe scan/STOP/BACK validation |
| v1.8 optional 1-Wire | **REAL DRIVER CODE INTEGRATED, HARDWARE TEST PENDING:** PA4 1-Wire host reset/convert/wait/read, scratchpad CRC/temp decoding, no auto OTG, COMM UI and BACK/STOP resource cleanup compile in actual LabMate | Known 3.3 V externally powered single DS18B20 test, pin collision and measured temperature |

## Menu policy (fixed)

**MEASURE → OUTPUT → RECORDS → COMM → INFO (About)**.
INFO/ABOUT is always the **last root group and bottommost menu item**;
COMM is directly above it and contains UART, I²C Explorer and 1-Wire Temp.
Preserve historical tool IDs, profile storage format and 128×64 scrolling.
Portable navigation tests assert the COMM/INFO positions, child mapping
and About's final position. Do not move About into COMM.

## Code gates

### B — Button Analyzer

- [x] Bring prior Button STOP → RESUME implementation, host tests
  and lifecycle guard into *current v1.8* development app.
- [x] Existing physical v1.8.1d candidate Button B1–B6
  operator-reported **6/6 PASS**, source in previous draft PR #12.
  This is carry-forward behavior evidence, **not a physical PASS on
  the newly combined v1.8DEV build**.
- [x] Integrated `v1.8DEV` SDK/host CI [38558631375](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38558631375) PASS, exact source `8956f76d29d8e20d775533e1b066adfb05536872`, same candidate FAP SHA256 `524006f7229a8e706d270a108f21193021f7597ff1bfd6d70e03b66c21981ba9`; native Button, navigation and app-local COMM collision guards plus Windows installer mock PASS.
- [ ] Final *full-scope* device acceptance after I²C/optional 1-Wire integration.

### M — v1.6 resource and module completion

- [x] The app already has split capture/input/view/storage and
  deterministic internal capture owner, PWM TIM1 and USART lifecycle.
- [ ] Audit every production GPIO/IRQ/TIM/UART path, all STOP/BACK/
  failed-acquire/exit transitions and potential concurrent claims.
- [x] Implement **isolated application-local** COMM mutual-exclusion
  model for I²C PC0/PC1 and candidate 1-Wire PA4 (not PB14), explicitly
  refusing capture, GPIO Monitor, PWM, UART, Logger activity; non-owner
  STOP does not release the active owner. Portable tests PASS in
  [CI 38558631375](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38558631375).
  The local claim now guards both real 1-Wire PA4 and conditional I²C3 drivers; it is **not** a global firmware lock.
- [x] Connect local COMM owner gate to actual PA4 1-Wire driver
  START and all STOP/BACK/exit cleanup paths. Direct HAL-backed
  one-shot DS18B20 implemented and compiled; firmware-wide arbitration
  cannot be inferred from app-local exclusivity.
- [x] Connect the I²C runtime worker, COMM screen and PC0/PC1 app-local
  claim to a **conditional real HAL ACK transport**. On stock Momentum
  the feature fails closed with `FW API` and never acquires bus locks.
  SDK/native source tests PASS; genuine firmware runtime still pending.
- [x] Compile the exact patched Momentum firmware and matching real
  integrated LabMate FAP in an ephemeral CI checkout: [Actions 38577944741](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38577944741),
  source `531a2e376beed1eb72ed08f6d9261213c8a24dac`, both `./fbt firmware_all`
  and `./fbt fap_labmate` PASS; FAP SHA256
  `f7e8cf33c4dce0cf7afac724a5d645edbb7263f29cbf7eab4add089bf3cc7db8`.
  This is SDK build/link evidence only, not firmware runtime or bus safety.
- [ ] Test actual firmware-wide owner coordination, failed-acquire, STOP/BACK
  and peripheral recovery plus existing Profiles/CSV on physical hardware.
- [ ] A firmware-wide lock claim requires a real exported HAL
  owner/lock contract or verified firmware change. App-local flags
  alone never guarantee global ownership.

### I — real I²C Explorer (blocked until viable owner path)

- [x] Preserve old pure scanner/pagination/lifecycle research in
  branch `dev/v1.8-i2c-explorer`, never call simulated hits real.
- [x] Design a compatible bounded mutex acquisition using Momentum's
  **same external I²C3 mutex and existing release path**, with finite
  50 ms wait instead of the stock infinite wait. Reproducible
  source patch has **source-application PASS** in
  [CI 38567640945](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38567640945),
  exact firmware source `d3f89dfe2ef6b01839201598e9be1590cba80322`.
  **Not a firmware compile, flash, or real cancellation PASS.**
- [x] Integrate original pure address scanner, result pages, per-probe
  lifecycle and **transport-injected worker** for true 0x08..0x77
  addresses, ACK/NACK/FAULT, bounded probe contract, STOP and exactly
  one matching owner release. All native tests + SDK FAP CI PASS in
  [38561645642](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38561645642).
- [x] Wire **real `furi_hal_i2c_is_device_ready` ACK probes** to the
  HAL adapter, bounded-acquisition contract, dedicated worker,
  I²C Explorer COMM UI, STOP/BACK thread join and owner cleanup.
  The patched SDK's `FURI_HAL_I2C_HAS_EXTERNAL_ACQUIRE_TIMEOUT` marker
  activates the transport automatically. On stock SDK the adapter
  deliberately returns unavailable; no unsafe blocking fallback.
- [x] SDK/host tests: [run 38568097149](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38568097149) PASS.
  Exact source `81f910d18104172387917808d471d21127e7171b`,
  integrated development FAP SHA256
  `4ae887fa2bc8d0ca54758487b37ec7421240d6c5e157782e328fb268b5ca8421`.
  Host fake HAL tested missing-API refusal, encoded ACK on 0x3C,
  STOP before acquire, BUSY and release. Runtime guards cover
  dedicated worker, release and status. **Not physical scanning.**
- [x] **Full patched Momentum firmware AND matching integrated FAP
  compiled** in [CI 38577944741](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38577944741).
  Exact production LabMate and new firmware HAL export link under the
  same patched source; generated FAP SHA256
  `f7e8cf33c4dce0cf7afac724a5d645edbb7263f29cbf7eab4add089bf3cc7db8`.
  First [CI 38576263608](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38576263608)
  had a real `-Werror=redundant-decls` app compile failure, fixed in
  `e33213309240fdb8c9134de84625a987ee5e8bed`. **This PASS is not
  firmware flashing, physical I2C or independent runtime validation.**
- [x] **STOP-during-acquire race corrected and host verified:**
  [source `82d211b`](https://github.com/sehmusadsoy-ui/flipper-labmate/commit/82d211b4820a2ed301665ad28585360786db7d75) now records STOP
  immediately after a bounded external-mutex attempt and before the
  acquire-result transition. Timeout after STOP is CANCELLED (zero
  release without ownership); acquired-after-STOP performs zero probes,
  releases exactly once, and reports CANCELLED. Added two native
  regression cases; stock SDK FAP and installer-mock tests PASS in
  [Actions 38579861058](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38579861058).
  Matching patched Momentum firmware + integrated real FAP build and
  APPCHK PASS in
  [Actions 38579860905](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38579860905).
  Patched FAP SHA256
  `7eaf093d4499a95c0410ef4bfe4a5c5ece5110c66a900bece73e737503a58377`.
  **CI only; no firmware flash or physical STOP race test.**
- [ ] **Physical owner, contention and STOP/BACK still NOT VERIFIED:**
  demonstrate no deadlock under real bus contention, I2C transfer
  timeouts, actual STOP/BACK/release and peripheral recovery.
- [ ] Physical known-safe **3.3V** hardware scan (device/no-device)
  and transition regressions later. No fake FAP, fake hit or
  future-unverified global mutex shortcut.

### W — feasible 1-Wire DS18B20 (real driver, not just decoder)

- [x] Preserve previous pure CRC/temperature codec and STOP model in
  `dev/v1.8-onewire-feasibility`.
- [x] New source review: Flipper's official `example_thermo`
  supports alternative external GPIO pins (PC0, PC1, PC3, PB2, PB3,
  PA4, PA6, PA7), not just shared PB14/`gpio_ibutton`.
  Changing to a non-PB14 pin needs an appropriate 3.3V pull-up.
- [x] Select **external PA4**, not PB14, and enforce LabMate-local
  capture/PWM/UART/Logger ownership exclusions (no firmware-wide GPIO
  arbiter exported); physical shared-owner cases still require review.
- [x] Implement actual 1-Wire host reset, 0xCC/0x44 conversion,
  nonblocking 800 ms conservative wait, 0xCC/0xBE scratchpad read,
  CRC8, signed temperature, unknown-power-on 85 C refusal,
  no OTG auto-power and immediate STOP cleanup.
- [x] Connect single integrated `COMM → 1-Wire Temp` screen with
  READY/RUN/DONE/NONE/BUSY/ERROR/PWR/STOP, explicit OK and BACK.
  COMM remains immediately above the final INFO → About root group.
- [x] Verified exact-source [CI 38563555290](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38563555290)
  on source `a40333dd2e8d2abccaa176ebd63f9037e7f5ee9b`:
  true Momentum SDK/FAP compilation, native CRC/temp tests, UI/menu
  guards, ownership and Windows installer mock PASS. FAP SHA256
  `afa88deb4d64752d9305708909663216778a17f7d8473611bb3c20513b2a1794`.
  **This proves SDK compilation, not physical sensor reading.**
- [ ] Physical known-safe 3.3 V, externally VDD-powered *single*
  DS18B20 test on PA4 with suitable pull-up; BUSY, STOP/BACK and
  existing-instrument regression pending. This is not yet Stable.

### I²C STOP and contention semantics — 2026-10-14

- [x] STOP while the firmware external-mutex acquire is pending now
  returns **CANCELLED** rather than reporting an unrelated bus fault.
  A failed acquire never releases an unowned bus. If STOP races a
  successful acquire, no address probes run, and the bus is released
  exactly once. Fake transport cases cover both races.
- [x] A bounded acquire refusal **without STOP** is now reported as
  **BUSY**, distinct from an actual probe/transfer **ERROR**. The
  complete lifecycle model, runtime status mapping and I²C screen
  preserve this distinction. Bus contention and a local conflicting
  LabMate tool intentionally share the user-facing BUSY status.
- [x] Final portable test suite, real stock Momentum SDK FAP build and
  Windows installer mock PASS for source
  [`2045951b`](https://github.com/sehmusadsoy-ui/flipper-labmate/commit/2045951b020c07449e47a77bac44bc75bb2e83f2)
  in [Actions 38580743450](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38580743450).
- [x] Patched Momentum firmware and exact integrated LabMate FAP built
  with source [`5238c3f9`](https://github.com/sehmusadsoy-ui/flipper-labmate/commit/5238c3f9b27cbd1f7052aa5e82ec6955350293bf)
  in [Actions 38580514575](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38580514575).
  `firmware_all`, `fap_labmate` and APPCHK PASS; patched FAP SHA256:
  `c67569797439819f846b0f6cd7d636483207d0b581151c692f90eee122cc7e59`.
  The subsequent changes are native-test assertions/source guards
  rather than production `src/` changes, so do not attribute a new
  exact patched artifact hash to the later commit.
- [ ] Physical I²C contention, STOP latency, device ACK, empty bus,
  firmware service coexistence and PA4 DS18B20 tests remain OPEN.
  **No firmware flashing or physical BUSY verification was performed.**

### Matched firmware/FAP test archive — 2026-10-14

- [x] [CI run 38582296921](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38582296921)
  on exact code source `f643b6dcd78224c7248ad9e85e97a7d2a31ce653`:
  real pinned patched Momentum `firmware_all`, integrated `fap_labmate`,
  FAP APPCHK and both local file SHA256 verifications PASS.
  FAP SHA256: `ac62c5a64b34376ddf0b1855634d490ecc0d870049f9be2652d48b19fd9e5003`.
  Exact paired `firmware.dfu` checksum is in the CI artifact's
  `SHA256SUMS.txt`; do not infer it from the FAP hash.
- [x] Created GitHub Actions **development-only** archive
  `v18DEV-patched-firmware-FAP-UNTESTED-DO-NOT-FLASH` (artifact
  `11902833775`, retention 7 days) containing the **one real**
  `labmate.fap`, matching `firmware.dfu`, `SHA256SUMS.txt`,
  `PROVENANCE.txt` and `READ_ME_FIRST.txt`. This is NOT a new
  Stable release, not a separate demo FAP and not an installation event.
- [x] Follow-up exact matched build [CI 38582754108](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38582754108)
  **PASS** on source `0195b9d4bbbd4d5480ef340a7b6d49479cb78b34`.
  This run again built the full patched firmware and single integrated
  LabMate FAP, verified both hashes and archived paired artifact
  `11903867521`. Patched FAP SHA256
  `9a276e6caa8173a03382d1b6ae7e163ddd535a878264084423c67f66deb6c881`.
  The only source change after the previous matched binary was a
  truthful comment clarification in the HAL-free control header;
  neither run supplies physical device evidence.
- [x] Added [physical acceptance gates](V1_8_PHYSICAL_ACCEPTANCE_GATE.md):
  exact-image pairing, independent firmware approval/rollback,
  real I2C3 ACK/NACK/STOP/BACK/BUSY, PA4 DS18B20 and old instruments.
- [ ] **No custom firmware flash or physical test is approved/claimed.**
  User authorization, recoverability review, suitable 3.3 V test devices,
  and real firmware-wide coexistence/STOP validation remain required.

### Firmware export and local pair-verification hardening — 2026-10-14

- [x] Added compiled firmware **ELF symbol-table check**:
  `furi_hal_i2c_external_acquire_timeout` must be an actually DEFINED
  global function in `firmware.elf`, not merely mentioned in header/API CSV.
  Full patched Momentum source + real integrated `labmate.fap` compiled and
  custom function symbol verified in [CI 38584209652](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38584209652) PASS.
- [x] Created **read-only** `scripts/verify-v18-matched-pair.ps1` to verify
  both FAP and firmware SHA256 plus pinned Momentum base, patch diff
  fingerprint, source commit, Actions run, and unapproved-development
  warning. It has **no USB or flashing operations** and checks only
  internal file consistency, not artifact authenticity.
- [x] Windows native mock tests reject mismatched source SHA, tampered
  FAP, tampered firmware, duplicate hashes, wrong Momentum base and
  absent binaries. FAP SDK + full host suite and installer mock
  [CI 38585242107](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38585242107) PASS.
- [x] Actual built firmware+FAP pair was verified by **that same**
  PowerShell preflight within
  [CI 38584936591](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38584936591) PASS
  on source `60464ed4df3c1133525b91dad0bfc09610eab855`.
  Matched FAP SHA256:
  `9a276e6caa8173a03382d1b6ae7e163ddd535a878264084423c67f66deb6c881`.
  Matched firmware.dfu SHA256:
  `e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0`.
  Both are in test-only artifact `11905990133` with a 7-day retention.
- [ ] **Still not tested:** physical Flipper boot of modified firmware,
  original Momentum service coexistence, real I2C3 ACK/NACK/STOP/BACK,
  DS18B20 PA4 sensor reading, full integrated legacy tools.
  Nothing was flashed, merged, published or installed.

### Approved trial preparation, minimal updater and rollback prerequisites — 2026-10-14

- [x] Operator's explicit project-chat consent to **try** temporary
  custom test firmware recorded on 2026-10-14. This does **not**
  imply physical installation has happened.
- [x] Built **minimal firmware-only** Momentum updater TGZ (no radio/
  SD-resource/option-byte updates requested) from the same exact patched
  source as the real integrated LabMate FAP. Read-only Python gate verified
  embedded DFU SHA256 matches the separately compiled firmware; native
  synthetic archive tests covered substitution, extra radio data,
  dangerous option-byte mask, path traversal and wrong hardware target.
- [x] On exact LabMate source `0fdd558291222c54f5b52b762e00fafffa3d0d62`,
  [CI run 38587659583](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38587659583)
  PASS: patched firmware/FAP compile, firmware ELF exported API symbol,
  minimal TGZ internal identity, three local checksums and the real
  matched-pair PowerShell read-only preflight. Original Stable untouched.
  Artifact `11906491025` (7-day retention) includes:
  - `labmate.fap` SHA256 `9a276e6caa8173a03382d1b6ae7e163ddd535a878264084423c67f66deb6c881`.
  - `firmware.dfu` SHA256 `e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0`.
  - `firmware-update.tgz` SHA256 `b796b42cb5756fc8bb2bb3180ae2c2cb00775b3f88ceceae1025299a2f424ad2`.
- [x] [Windows 38587659841](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38587659841)
  stock Momentum FAP build and read-only verification mocks PASS, including
  absent updater, mismatched source and tampered FAP/firmware/TGZ.
- [ ] **Still required BEFORE any firmware installation:** successful
  verified backup of the existing Flipper's internal settings AND separate
  microSD Profiles/CSV, current installed Momentum version/compatibility
  report, and a reviewed, available working rollback/recovery option.
  No physical firmware startup, I2C, DS18B20, or legacy tools accepted.
  Physical test gates: [V1_8_PHYSICAL_ACCEPTANCE_GATE.md](V1_8_PHYSICAL_ACCEPTANCE_GATE.md).

### 2026-10-14 — ACTUAL full MNTM-012 migration firmware/FAP CI PASS

- [x] The operator reported **official MNTM-012 rollback updater + prior
  LabMate v1.8 Stable FAP `ROLLBACK READY PASS`**: both publicly
  published SHA256 values matched, downloaded to
  `Downloads\LabMate-Rollback-MNTM012`.
  An actual device recovery/restore remains NOT TESTED.
- [x] [FULL migration CI run 38611756627](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38611756627) **SUCCESS**
  on exact LabMate source `370bc048dc21d7d58ee69c8e762f5c29705a1c1c`.
  Actual pinned Momentum (18 Aug 2026) full updater + C2 radio +
  **SD resources** + one integrated genuine LabMate FAP compiled.
  `APPCHK`, compiled bounded-I2C firmware ELF symbol, real DFU identity
  within TGZ and read-only full-package checks PASS.
- [x] CI downloaded the **OFFICIAL MNTM-012** updater, matched public
  vendor SHA256
  `1d9e1e600c8680172ff6f6913ca0b12484e7d45adbc72a66552e534784c8c1a7`,
  and proved the actual radio payload **byte-identical** to the new
  full updater (radio SHA256
  `134a9af448d2bc35995600c9e95723a387c144c2d1adea671086f16f95d327df`).
  Option-byte reference, compare mask and write mask in the two
  firmware update manifests are **identical**, not zero: the official
  manifests can apply option-byte policy. This is an on-disk format
  check, not safe-to-flash physical proof.
- [x] Test-only GitHub Actions artifact `11918707230`, named
  `v18DEV-FULL-MNTM012-REVIEW-DO-NOT-FLASH`, archived matched files
  and provenance; independently retrieved and unpacked its ZIP
  (6 entries, all hashes MATCH):
  - `labmate.fap` SHA256
    `9a276e6caa8173a03382d1b6ae7e163ddd535a878264084423c67f66deb6c881`.
  - `firmware.dfu` SHA256
    `e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0`.
  - `firmware-full-update.tgz` SHA256
    `5e3267d780a56178e8ff40cb81ca2f6562e81d4d07daf703ab1c7db34e967d0d`.
  - GitHub artifact ZIP SHA256
    `fc581a79e999b64b853095a87c0075d8894856f132299e13f9fef4c1922e4493`.
- [x] New `scripts/prepare-v18-full012-test.ps1` prepares **only**
  the pinned exact successful full artifact through PowerShell
  and validates the fixed three independent binary digests, manifest,
  provenance and the GitHub run success/source. It NEVER flashes.
- [x] **Physical firmware update handoff and matched LabMate FAP upload occurred on COM7 (2026-10-14)** with exact artifact digests and user-retained backups: full MNTM-012 replacement TGZ transferred, update command accepted, device rebooted, actual pinned SHA256 `9a276e6caa8173a03382d1b6ae7e163ddd535a878264084423c67f66deb6c881` FAP transferred to `/ext/apps/Tools/labmate.fap` and launch requested. Operator subsequently confirmed app `v1.8DEV`, root order with INFO at bottom, empty I2C `READY→NONE` and no-sensor 1-Wire `NONE` with responsive BACK. These are FIRST physical PASS observations, recorded gate-by-gate in [V1_8_PHYSICAL_ACCEPTANCE_GATE.md](V1_8_PHYSICAL_ACCEPTANCE_GATE.md); **not** real ACK/CRC sensor or comprehensive regression. Device About build string and physical recovery remain OPEN. v1.8 Stable and main remain unchanged. v1.9 is frozen.

### R — in-place v1.8 final release gate (NOT YET OPEN)

- [ ] Original v1.8 functional code gates above are satisfied or
  each genuinely infeasible limitation is explained and explicitly
  authorized; this branch is **not** yet complete.
- [ ] All existing v1.5–v1.8 instruments/CSV/Profiles regressions.
- [ ] Final production badge `v1.8` restored, exact FAP SDK/host CI
  and hash recorded, Flipper installed binary acceptance obtained.
- [ ] Replace only the published `v1.8` FAP/checksum after those
  gates; document **both old and new SHA/source** and independently
  verify remote asset digest; preserve immutable original tag
  and earlier v1.7 assets.
- [ ] v1.9 work only afterwards.

**Do not label research UI, decoder, CI or arbitrary hash as a
physically functional device.** Do not promise a solution to firmware
API restrictions before verifying the actual supported interface.
