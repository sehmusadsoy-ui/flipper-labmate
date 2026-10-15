# LabMate v1.8 Completion — Physical Acceptance Gate (NOT YET APPROVED)

**Branch:** `dev/v1.8-completion` · **PR:** #13 (Draft) · **Stable release:** unchanged `v1.8`.

This checklist deliberately separates compiled source from actual Flipper hardware evidence. Nothing below is a reported device PASS until the operator records a result from the exact checksummed firmware/FAP pair. The existing v1.8 Stable installation and all saved profiles/CSV files must remain intact while these gates are open.

## Gate 0 — Before any device firmware change

- [x] Operator explicitly approved a **temporary, non-Stable custom firmware trial** in the project chat on **2026-10-14**. Approval is not evidence that a backup, installation or physical test occurred.
- [x] **qFlipper internal-settings backup — operator-provided archive validated structurally, 2026-10-14.** The private `.tgz` contained 14 readable regular internal-settings files and one directory; no unsafe tar paths or failed reads. The archive remains private; contents are not committed. **Restore is NOT tested**, and this archive does not include microSD saved files.
- [x] **LabMate-only microSD folder copy — USER-REPORTED PASS, 2026-10-14:** Windows PowerShell `storage.py receive "/ext/apps_data/labmate"` exited successfully; backup location `C:\\Users\\sehmu\\Downloads\\LabMate-Backup-20261014-201529` and 14 copied files reported. **Scope:** this confirms the user-observed LabMate directory copy and nonempty files only; no independent source/file-by-file hash comparison, full microSD backup, restore test, or internal-settings backup was performed. Preserve the copy without modifying it.
- [ ] Separately confirm the LabMate profiles/CSV copied correctly and, if desired, make a **complete** microSD backup before changing firmware.
- [ ] Prepare an independently tested way to restore the known working Stable Momentum firmware and historical v1.8/v1.7 LabMate. Keep its official updater package and the known-Stable `labmate.fap` available and verifiable. No automatic restore/erase.
- [x] Operator provided About-screen evidence: installed **Momentum `MNTM-012`**, **31 December 2025**. This is the published `mntm-012` release, tag `e1784e7418d8b074e971983ceb6fef0f37e52ae4`; the LabMate test's pinned development base is **18 August 2026** (`d3f89dfe2ef6b01839201598e9be1590cba80322`).
- [ ] **COMPATIBILITY BLOCKER:** The minimal firmware-only `.tgz` lacks updated bundled SD resources and radio. Do **not** install this current minimal candidate over `MNTM-012` until a full matched updater strategy or an explicitly justified compatibility proof and restore plan are validated. The package's internal checksum PASS does **not** close this gate.
- [x] **ROLLBACK FILES USER-REPORTED SHA256 PASS, 2026-10-14:** Windows PowerShell downloaded official `flipper-z-f7-update-mntm-012.tgz` with SHA256 `1d9e1e600c8680172ff6f6913ca0b12484e7d45adbc72a66552e534784c8c1a7` and previously published v1.8 Stable `labmate-v18-stable.fap` with SHA256 `119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0`. Terminal displayed `ROLLBACK READY PASS`. Folder: `Downloads\\LabMate-Rollback-MNTM012`. **This is validated *availability* of fallback binaries only, NOT a tested firmware restore or recovery path.**
- [ ] Identify the exact test build `LabMate commit`, pinned `Momentum base commit`, patched HAL diff hash, `firmware.dfu` SHA256 and `labmate.fap` SHA256 from a **single** CI run's `PROVENANCE.txt` and `SHA256SUMS.txt`; verify both files with SHA256 *again* after retrieval.
- [ ] Review the patch's scope and firmware startup/recovery behavior separately. No tested ROM compatibility, rollback or hardware coexistence is implied by CI compilation.
- [ ] Keep the test pair separate from the existing GitHub Stable Release. No background install, USB transfer, firmware flash, automatic publish or tag mutation.
- [ ] Confirm all external signals and pull-ups are known-compatible **3.3 V**. Never connect unknown voltages, 5 V inputs, mains or other unsafe sources to Flipper GPIO.

The verified **test-only** GitHub Actions artifact named `v18DEV-minimal-updater-FAP-UNTESTED-DO-NOT-FLASH` is a **development archive only** with a short retention period. It is not an installer, release, recommendation to flash, or a physical acceptance claim. Its FAP must not be used with ordinary stock Momentum firmware: the timed-I²C ABI would be missing.

### Matched uninstalled candidate — 2026-10-14

The most recent **exact source + real FAP + DFU + minimal qFlipper-style TGZ**
was created and triply checksum-verified in
[CI 38587659583](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38587659583),
LabMate source `0fdd558291222c54f5b52b762e00fafffa3d0d62`,
GitHub Actions artifact `11906491025` (**7-day retention**):

| Exact paired file | Verified SHA256 |
| --- | --- |
| `labmate.fap` | `9a276e6caa8173a03382d1b6ae7e163ddd535a878264084423c67f66deb6c881` |
| `firmware.dfu` | `e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0` |
| `firmware-update.tgz` | `b796b42cb5756fc8bb2bb3180ae2c2cb00775b3f88ceceae1025299a2f424ad2` |

CI verified that the TGZ contains the **identical DFU bytes**, is targeted
at f7 and does not request extra radio/SD-resource or option-byte changes.
The patched firmware contains the expected callable bounded-I2C API.
Both the Windows mock and the real artifact read-only preflight passed.
This does **not** validate recovery, startup or USB flashing on a device.
Historical Stable v1.8 FAP SHA256 for rollback:
`119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0`.

### Windows PowerShell — one-command preparation (NO DEVICE CHANGE)

The operator continues using the original Windows **PowerShell** workflow.
For the currently pinned candidate, obtain the preparation script from its
reviewable GitHub commit, then run it:

```powershell
$prep = "$env:TEMP\\prepare-labmate-v18dev.ps1"
Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/715973ed94f14a60e90cac037611f0d4501d6e90/scripts/prepare-v18-dev-test.ps1" -OutFile $prep
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $prep
```

This script uses the previously established `gh` login, downloads the
**exact pinned** [Actions 38587659583](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38587659583)
archive, verifies all three fixed file SHA256s, the checksum list and
source provenance, then prints `PREPARE PASS`. It does **not** talk to
COM ports, call qFlipper, install firmware, or replace LabMate Stable.
The archive expires after 7 days; an expired run must fail closed, never
automatically substitute a newer build.

**Subsequent PowerShell firmware installation** uses the firmware's
`scripts/selfupdate.py -p COMx <path-to-update.fuf>`, and a separate
`scripts/install-labmate.ps1` only after the matching custom firmware
has booted. That later phase requires independently verified backups,
rollback, installed Momentum version and reviewed update compatibility.
Do **not** run either installation command just because preparation
passed. Device USB/port may change after a firmware reboot.

### Read-only paired-file verification (Windows; no installation)

After obtaining the **specific official GitHub Actions artifact** and extracting its files to a dedicated folder, from the LabMate source root run the following **verification only** in PowerShell (adjust the folder and source SHA to the exact originating CI run):

```powershell
& .\scripts\verify-v18-matched-pair.ps1 `
    -PairDirectory 'C:\LabMate-CI-Pair' `
    -ExpectedSourceSha '0fdd558291222c54f5b52b762e00fafffa3d0d62' `
    -RequireUpdater
```

The verifier rejects missing/mixed files, mismatched firmware/FAP SHA256, wrong pinned Momentum base, missing provenance, and wrong expected LabMate commit. It **never** contacts a USB/COM port, copies a FAP, or flashes firmware. A PASS establishes file self-consistency, **not GitHub download authenticity or physical compatibility**; confirm the artifact's official GitHub Actions origin separately. The mocked PowerShell rejection tests do not prove real hardware functionality.

### FULL MNTM-012 migration pair — CI and Windows PASS (2026-10-14)

The vendor's **official MNTM-012** update TGZ SHA256 matches the
original release, and the pinned newer Momentum full update from
[CI 38611756627](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38611756627)
contains the **exact same C2 radio binary bytes** (SHA256
`134a9af448d2bc35995600c9e95723a387c144c2d1adea671086f16f95d327df`).
Its update manifest's **option-byte reference, mask and write mask** are
also byte-equivalent to the official MNTM-012 updater. They are not
all zero; no claims of risk-free physical flashing or restore are made.

The **FULL** firmware-only **plus radio and SD resources** build passed,
and the single genuine LabMate FAP `APPCHK` passed. The verified
test-only artifact is
[GitHub Actions artifact 11918707230](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38611756627/artifacts/11918707230)
(7-day retention), pinned LabMate source commit
`370bc048dc21d7d58ee69c8e762f5c29705a1c1c`.
It contains:

| Name | SHA256 |
| --- | --- |
| `labmate.fap` | `9a276e6caa8173a03382d1b6ae7e163ddd535a878264084423c67f66deb6c881` |
| `firmware.dfu` | `e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0` |
| `firmware-full-update.tgz` | `5e3267d780a56178e8ff40cb81ca2f6562e81d4d07daf703ab1c7db34e967d0d` |

Independently retrieved artifact ZIP and checked all six internal
entries and hashes. The exact full update (not the earlier minimal
test package) was also downloaded and verified by the **actual Windows
PowerShell** preparer in [CI 38613472751](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38613472751):
all three SHA256 checks and `LABMATE FULL MNTM012 PREPARE PASS`.
**NO USB or firmware flash** occurred in CI.

Windows operator preparation uses reviewed
`scripts/prepare-v18-full012-test.ps1` with an exact frozen successful
artifact ID, CI run, source SHA and all file SHA256 values.
The full test package still requires controlled physical startup and
on-device LabMate/COMM tests. A prepared updater is not acceptance.

### Controlled PowerShell firmware install — 2026-10-14

- [x] Operator on **Windows** reported full matched artifact
  `LABMATE FULL MNTM012 PREPARE PASS`, **all three**
  `firmware.dfu`, `firmware-full-update.tgz`, `labmate.fap`
  SHA256 checks PASS; directory:
  `C:\Users\sehmu\Downloads\LabMate-v18DEV-FULL`.
  This was a **download-only** action.
- [x] Added `scripts/install-v18-full012-dev-firmware.ps1`: real
  **stage-only by default** and `-Apply` with the 3 pinned
  artifact SHA256 values; checks archive entries against an exact
  file allow-list, extracts to a **fresh** directory, verifies
  embedded DFU/radio hashes and manifest target,
  rechecks official MNTM-012 rollback and v1.8 Stable FAP SHA256,
  confirms recorded 14-file LabMate backup plus a qFlipper settings
  archive, validates Momentum SDK tools and requires user to type
  `YUKLE` before sending the package through Momentum
  `scripts/selfupdate.py`. No LabMate FAP overwrite occurs in
  this firmware-only step.
- [x] [Actual Windows CI 38614867094](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38614867094)
  PASS: downloaded REAL full artifact, original preparer hash-check
  PASS, real Windows TAR extraction + manifest + DFU/radio digest
  verification PASS, `-Apply` fails closed for missing rollback.
  **No USB/flashing** was performed in CI.
- [x] **Operator's actual COM7 USB update upload and firmware updater handoff — 2026-10-14 21:36–21:37 local — REPORTED PASS:** on Windows, `install-v18-full012-dev-firmware.ps1 -Apply -SettingsBackupPath ...` revalidated all three SHA256s, embedded DFU and radio, both rollback digests, 14 microSD backup files and qFlipper settings archive; operator explicitly typed `YUKLE`. Momentum `selfupdate.py` connected to `FLIP_UYBELAV` on **COM7**, transferred all seven firmware update components (firmware.dfu, firstboot.bin, radio.bin, resources.tar.gz, splash.bin, update.fuf, updater.bin), then returned `FIRMWARE UPDATE COMMAND ACCEPTED; WAIT FOR FLIPPER TO REBOOT.` No upload transport error was reported.
- [x] **Operator-reported physical reboot and basic UI launch: PASS (2026-10-14).** User reports the Flipper rebooted, all basic controls are working and they can open LabMate. This upgrades the earlier updater-handoff-only status to **basic physical boot/UI PASS**, but the **on-device firmware About/version was not yet reported** and it may be the pre-existing Stable LabMate FAP from microSD.
- [x] **EXACT MATCHED LabMate FAP USB upload and launcher request — OPERATOR LOG PASS, 2026-10-14 21:52 local.** PowerShell installer verified `labmate.fap` SHA256 `9a276e6caa8173a03382d1b6ae7e163ddd535a878264084423c67f66deb6c881`; `runfap.py` connected to `FLIP_UYBELAV` COM7, installed to `/ext/apps/Tools/labmate.fap`, closed the previous app if any, logged `Launching app: /ext/apps/Tools/labmate.fap`, and exited `0` (`SUCCESS: runfap.py exited 0 and requested app launch.`). This **proves transfer plus launch request only**; matching FAP is staged on Flipper, but rendered v1.8DEV menu/normal operation has not yet been observed.
- [x] **Subsequently obtained app UI and firmware identity evidence.**
  Operator reported v1.8DEV menu, root order and operating tools;
  additionally supplied screenshots showing `mntm-dev [14-10-2026]`,
  `d3f89dfe`, `HEAD`, and Flipper Zero FZ.1. See
  firmware About identity record near end. Those screenshots identify
  the reported development firmware, not its installed DFU byte-hash.
  The original note above is historical upload-stage evidence;
  firmware-wide arbitration, positive I2C/1-Wire peripherals and
  tested physical rollback remain OPEN.

## Gate 1 — Firmware startup and single-app sanity (after approved installation only)

| ID | Check | Required evidence | Status |
| --- | --- | --- | --- |
| F1 | Test firmware boots and basic OS menu, Back and input work | Operator result + exact build IDs | **PASS — operator reports boot, controls and UI functional on matched dev trial** |
| F2 | The single LabMate entry launches; shows `v1.8DEV` | Operator result + FAP SHA256 | **PASS — operator reports v1.8DEV menu; FAP install SHA verified** |
| F3 | Root order is `MEASURE → OUTPUT → RECORDS → COMM → INFO`; About remains last | Operator screen observation | **PASS — operator confirms expected order, INFO bottom** |
| F4 | No automatic USB OTG/5 V activation; idle tools do not seize pins | Operator observation | NOT TESTED |

## Gate 2 — External I²C3 functionality

**Pins:** PC0 SCL and PC1 SDA. Firmware API: `furi_hal_i2c_external_acquire_timeout()`. Require a known-safe 3.3 V I²C peripheral for positive-ACK testing; do not infer a device address from host stubs (`0x3C` in tests is simulated). A no-ACK result can also be a bus transfer timeout, so an empty scan alone does *not* prove electrical health.

| ID | Check | Pass condition | Status |
| --- | --- | --- | --- |
| I1 | Enter `COMM → I2C Explorer` on **matching patched firmware** | READY, not `FW API`, no automatic scan | **PASS — operator confirms READY; scan only on OK** |
| I2 | Scan an unconnected/known-idle bus | Completes with NONE/no ACK, never fabricates a hit, no freeze | **PASS — operator reports NONE, responsive UI on empty bus** |
| I3 | Scan a known-safe peripheral with a confirmed 7-bit address | Correct real ACK address displayed; pagination does not change measurements | NOT TESTED |
| I4 | Press OK STOP during scan | Returns to STOP/CANCELLED without deadlock and releases ownership | **PASS — operator reports RUN→OK STOP/CANCELLED with no freeze and subsequent scan** |
| I5 | BACK during scan, then re-enter and start again | Returns to menu and can reacquire without stale worker/handle | **PASS — operator reports BACK during RUN, re-entry, new scan→NONE** |
| I6 | External firmware I²C mutex contention, **only with an independently safe, verified owner** | BUSY/refusal; no arbitrary pin takeover or deadlock | BLOCKED: safe real owner fixture needed |
| I7 | Force probe timeout/fault **only with a safe fixture** | Distinguish non-ACK from transport fault where HAL permits; no leak | BLOCKED: safe fault fixture needed |
| I8 | Repeat STOP and reopen after successful and empty scans | No stuck BUSY, no inherited stale result, no reboot | **PARTIAL — STOP, retry/reopen and empty-bus scan PASS; ACK-device repetition still OPEN** |

### 2026-10-14 — real Flipper I²C cancellation/STOP lifecycle PASS

Operator replied **"I2C STOP PASS"** following the explicit no-peripheral
test with: `COMM → I2C Explorer`; scan by OK; OK during `RUN`
to stop with `STOP / SCAN CANCELLED`; new scan to `NONE`; BACK
during `RUN`; re-enter and scan to `NONE`; no stuck `BUSY`,
UI freeze or spontaneous reboot. Classify **I4 and I5 PASS**,
and **I8 PARTIAL** because repeated runs with an actual ACK device
have not yet occurred. This confirms operator-observed app lifecycle,
not firmware-wide arbitration, scan accuracy with external sensor,
or transport-fault differentiation.

## Gate 3 — PA4 1-Wire DS18B20

Use one independently verified, compatible, externally VDD-powered **3.3 V** DS18B20 with an appropriate 3.3 V data pull-up. Pin PA4; never assume PB14 is free or auto-enable OTG.

| ID | Check | Pass condition | Status |
| --- | --- | --- | --- |
| W1 | Enter `COMM → 1-Wire Temp` with no sensor | Correct NONE/no-sensor result; no pin leak | **PASS (visible behavior) — operator confirms NONE and BACK; low-level pin-lease validation not independently proven** |
| W2 | Read real DS18B20 | Plausible measured reading + valid scratchpad CRC; no simulated result | NOT TESTED |
| W3 | STOP during conversion, BACK, reopen, read again | Cancellation and resource recovery | NOT TESTED |
| W4 | Legacy capture/PWM/UART/Logger active | App-local conflict is blocked safely; no false ownership claims | **PARTIAL — real PWM RUN blocks 1-Wire (`BUSY`), PWM STOP restores no-sensor `NONE`; capture/UART/Logger conflicts OPEN** |

### 2026-10-14 — first matched-FAP physical no-peripheral acceptance (operator-reported)

After [exact matched FAP COM7 upload](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38611756627)
(SHA256 `9a276e6caa8173a03382d1b6ae7e163ddd535a878264084423c67f66deb6c881`),
the operator explicitly reported **"hepsi çalışıyor pass"** for
three immediately preceding test sets: `v1.8DEV` badge + root
`MEASURE, OUTPUT, RECORDS, COMM, INFO`, I2C Explorer
`READY`/no `FW API` + empty-bus `NONE` and BACK/re-entry,
and 1-Wire Temp no-sensor `NONE` + BACK. Mark F1–F3, I1–I2,
and W1 (user-visible subset) PASS. I5/I8 are **PARTIAL** because
cancellation *during* scan was not explicitly demonstrated;
I3 actual 7-bit ACK, I6 contention, I7 fault, W2 CRC sensor,
W3 mid-conversion STOP and W4 coexistence are **NOT tested**.
This report does not claim successful sensor connection, firmware-wide
GPIO arbitration, or every remaining v1.8 acceptance requirement.
Firmware About build string still has not been separately photographed.

### 2026-10-14 — PWM local resource arbitration vs. I²C and 1-Wire

- [x] **Operator physical PASS, GPIO disconnected:** PWM Studio OK to
  `RUN` on PA7; BACK to root with PWM still running; I²C Explorer
  OK refused with `BUSY`; 1-Wire Temp OK refused with `BUSY`.
  Re-enter PWM Studio, OK `STOP`; I²C scan completed with empty-bus
  `NONE` and 1-Wire READ completed with no-sensor `NONE`.
  Operator replied **"pass"** to this exact seven-step procedure.
  This verifies LabMate **app-local** PWM ownership checks and
  release/reuse across tools. It does not establish cross-app
  firmware-wide GPIO arbitration or PA7 waveform precision.
- [ ] Additional clashes with UART, Logger, Counter, Button and
  firmware subsystems, plus real PA7 output waveform, remain OPEN.

## Gate 4 — Regression of earlier Stable features

Record **separately**: Button Analyzer START/STOP/RESUME/RESET and preserved completed counts; PWM Studio START/STOP; Counter STOP/RESUME; GPIO Monitor, Frequency and Pulse; UART ESP32 RX/TX RUN/STOP/BACK; Logger/History open and delete confirmation; Profiles S1–S3 LOAD/SAVE/DELETE with real prior data; application exit and re-entry without stuck hardware ownership. Recheck INFO at bottom and COMM directly above. Do not overwrite old CSV or profiles during exploratory tests.

### 2026-10-14 — Button Analyzer control regression: operator physical PASS

- [x] **No external button connected — UI/state transition PASS.** Operator
  answered **"pass"** to the exact on-device Button Analyzer test:
  `MEASURE → Button Analyzer` initial `STOP` / `PC1 / PULLUP` /
  `DB 10 ms`; OK `RUN`; DOWN detail page and back to main;
  OK `STOP`; OK `RESUME`; OK `STOP`; UP `RESET` yielding
  next OK `START`; BACK returns to menu. No crash or stuck UI
  reported. This is real-device operator confirmation of **input,
  display and lifecycle controls**, not a synthetic CI claim.
- [ ] **Measured real switch press/release counts, debounce, bounce
  duration, settle time and completed nonzero results preserved by
  STOP→RESUME remain OPEN.** They require a real known-safe contact on
  PC1/ground, not an unattached pin. Do not infer electrical accuracy
  from the control-only PASS.

### 2026-10-14 — Event Counter TIM2 control/time regression: physical PASS

- [x] **Operator-reported on-device PASS, no externally applied pulses:**
  `MEASURE → Event Counter` initial STOP, COUNT 0, TIME 0 s;
  OK RUN, wait ~5 seconds and observe elapsed time advance; OK STOP
  freezes time; OK RESUME continues accumulated elapsed time; OK STOP
  then UP RESET zeros COUNT and TIME; BACK and re-enter without
  lingering BUSY/freeze. The operator explicitly replied
  **"COUNTER PASS"** to these exact steps.
- [ ] **Real external PB3 rising-edge count accuracy, counter rollover,
  latency and coexistence with other live input capture remain OPEN.**
  The above reports successful UI/timer/ownership transitions and
  elapsed-time semantics only, not hardware pulse-accuracy proof.

### Physical regressions: Logger/History and Profiles (2026-10-14)

- [x] Logger and History: operator reported `LOGGER HISTORY PASS` for new PC1 frequency CSV recording, advancing rows, STOP/SAVED, opening the newest log and inspecting row count, and canceling the delete confirmation without loss.
- [x] Profiles: operator reported `PROFILES PASS` for inspecting S1-S3, LOAD from a saved slot, canceling SAVE and DELETE confirmations with BACK, and checking profile preservation after reopening.
- [x] Disposable newly-created CSV deletion, including BACK cancel,
  targeted confirmed DELETE and persistent absence after app reentry
  **physically PASS** in the 2026-10-14 Log History section below.
- [x] Disposable S3 real **SAVE/LOAD across full application restart**
  is physically PASS; see S3 section below.
- [x] Independent Windows CSV structure/content audit of a later
  untouched test file `log_0056.csv`: USB receive, 8 parsed rows,
  correct header, strictly increasing timestamps and FREQ/PC1 source
  verified (2026-10-15, see record below).
- [x] Disposable S3 targeted DELETE/BACK cancel and app-restart
  persistence **physically PASS** (see S3 record below).
- [x] Flipper-side vs downloaded-byte MD5 checksum equality
  physical USB PASS for `log_0056.csv` on 2026-10-15;
  preserve S1/S2 and backups.

### 2026-10-14 — MEASURE suite navigation and capture lifecycle: physical PASS

- [x] **Operator-reported `MEASURE PASS` with external GPIO disconnected**
  after the exact on-device four-part regression:
  GPIO Monitor switches pins, OK HOLD/LIVE and BACK;
  Frequency Meter switches HIGH PB3 / LOW PC1, OK HOLD/LIVE,
  UP stats reset and BACK; Pulse Analyzer LIVE/HOLD/LIVE,
  UP STATS and BACK; afterward, I2C Explorer displays READY
  and completes an empty-bus scan with NONE. No stuck BUSY
  or unresponsive application was reported.
- [ ] This is UI/control and LabMate-local resource reuse acceptance;
  it does not re-establish frequency, pulse width/duty, edge
  counting or GPIO electrical accuracy for the newly installed
  firmware/FAP pair. Earlier real peripheral evidence is historical;
  current matched-pair signal tests are still OPEN.

### 2026-10-14 — PWM Studio custom-frequency control: physical PASS

- [x] Operator-reported `PWM CUSTOM PASS` for the exact staged
  no-external-load test: PWM Studio STOP frequency preset and duty
  edits; long-OK CUSTOM editor, frequency and step adjustments;
  BACK cancels; re-enter editor and OK saves; PWM RUN, live duty
  change, OK STOP and BACK with no freeze/reboot.
- [ ] PA7 waveform frequency, duty-cycle and switching accuracy
  measured on external hardware remain OPEN. This PASS covers
  device UI, edit/cancel/save and state transitions only.

### 2026-10-14 — UART Terminal control regression: physical PASS

- [x] Operator reported `UART UI PASS` after the requested
  no-connected-peripheral test: baud selection 9600/38400/115200,
  ending at 115200; UART OK RUN with no unexpected busy/error;
  DOWN opens TX editor with default AT and edit controls;
  BACK returns to RX without sending; OK STOP, BACK to menu;
  re-enter UART and selected 115200 baud preserved, with no
  persistent BUSY/ERR.
- [x] The subsequently installed UARTFIX ST3 pair **did** pass
  ESP32-S2 115200 physical throughput and TX with `R=20543`,
  `D=0`, `E=0` and STOP/BACK/re-entry. See ST3 record below.
  Other baud rates under real traffic and longer-term stress
  remain untested.

### 2026-10-14 — UART ESP32-S2 stress: **UARTFIX ST3 PHYSICAL PASS** (initial D=52 retained as historical failure)

- [x] **Positive link and TX evidence:** operator's actual ESP32-S2
  115200 8N1 trial on the matching firmware/FAP reports
  `ESP32_READY=yes; R=20621; D=52; E=0; TX A/T=yes`.
  RX is active, two explicit TX commands produced expected replies,
  and UART framing/noise error counter stayed zero.
- [x] **Initial run FAILURE documented historically, before the fix:**
  `D=52` means the original 256-byte UART ISR RX queue overflowed during
  the reported trial. This initial run is not a PASS; see ST3 physical
  retest result below for the independently reported zero-loss outcome.
- [x] Source-only mitigation committed on `dev/v1.8-completion`:
  original 256-byte UART queue increased to 1024 bytes, consumer
  cap raised from 4x64 to 16x64 bytes per event-loop pass, ISR drop
  reporting preserved. Native HAL mock now confirms a 320-byte burst
  (previously overflowing) has `D=0`, 1088-byte queued without
  a poll still reports exactly 64 drops and a full 1024-byte
  drain succeeds. Static UART guard also checks both bounds.
  [Source CI 38635609797](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38635609797)
  **SUCCESS**, but this is NOT a physical UART throughput result.
- [x] [FULL pinned patched firmware/FAP build 38635690935](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38635690935)
  **SUCCESS** on exact source `f24a08640e7938cfaf7000a8f5b3e470c9b6ad14`;
  compiled firmware.dfu digest `e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0`
  is byte-identical to the firmware image previously flashed successfully.
  Real patched-SDK LabMate APPCHK passed; pinned new `labmate.fap`
  SHA256 `eaadc85aba2c8a78074dc97935dc6d71de982582054f8addbeea227428b4f0cf`
  independently verified from actual GitHub artifact
  `11927944759` together with provenance and all ZIP file digests.
- [x] Added `scripts/install-v18-uart-queue-dev-fap.ps1`:
  exact pinned Actions run/source, three fixed artifact digests,
  6-file allow-list, checksum manifest and provenance checks;
  default only stages/verifies, `-Apply` refuses unless the previous
  LabMate DEV FAP is backed up and SHA-correct, SDK USB tooling exists
  and operator manually confirms YUKLE. Only installs
  `/ext/apps/Tools/labmate.fap`; it does NOT flash firmware.
- [x] Real [Windows preflight CI 38637386364](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38637386364)
  **SUCCESS**: Windows downloaded the exact real paired artifact,
  verified all pinned source/hashes/manifest, passed repeat-stage,
  rejected a deliberately tampered FAP and rejected `-Apply`
  with missing prior DEV FAP backup **before any USB call**.
  No Flipper or hardware device was modified by CI.
- [x] **Operator reports successful FAP-only USB installer command**:
  PowerShell printed `SUCCESS: runfap.py exited 0 and requested app launch.`
  and `LABMATE UARTFIX FAP INSTALL COMMAND PASS. Confirm actual app launch on screen.`
  The script's preflight was designed to verify the pinned artifact and
  preserve the previous development FAP. This confirms USB installer exit
  status and app-launch request; it is **not yet independent proof** that
  Flipper visibly launched the new app. No firmware flash was requested.
- [x] **UARTFIX ST3 operator real-device physical PASS, 2026-10-14:**
  `APP=yes; READY=yes; R=20543; D=0; E=0; TX=yes; STOP/BACK=yes`
  on the installed UARTFIX 1024-byte-queue FAP and ESP32-S2 115200 peer.
  Operator confirms app actually opened, ESP32_READY, 20543 RX bytes,
  **zero UART queue drops**, zero UART errors, TX responses, STOP/BACK
  and successful re-entry per the immediately preceding ST3 procedure.
  Thus the **bounded ESP32-S2 UART 115200 stress and lifecycle acceptance
  gate is PASS** for this matched firmware/FAP pair. Do not erase the
  historical pre-fix D=52 result, or imply all conceivable UART workloads
  are zero-drop guaranteed; much longer or different loads are not tested.

### 2026-10-14 — External I2C/1-Wire hardware availability, operator report

- [ ] Operator reports no external 3.3 V I2C OLED/sensor module and
  no DS18B20 temperature sensor available for physical acceptance.
  I3 (positive real ACK), ACK-device part of I8, W2 (actual DS18B20
  reading and CRC), and W3 (STOP during real sensor conversion) remain
  **BLOCKED BY FIXTURE / NOT TESTED**, not PASS and not firmware FAIL.
  Empty-bus I2C scan and no-sensor 1-Wire screen passes do not satisfy
  the positive-peripheral requirements.
- [ ] Existing ESP32-S2 could potentially act as an independent I2C
  slave test peer, but do not count this as a tested peripheral:
  physical pin routing, external I2C pull-ups to 3.3 V, safe power
  isolation and board firmware still need separate verification.
  Arduino-ESP32 exposes Wire slave mode; that alone is not proof
  of a working Flipper/ESP32 electrical I2C fixture.
- [ ] Continue no-new-hardware Threshold Alerts, resource lifecycle,
  app exit/reopen and non-destructive persistence regressions.
  Do not manufacture simulated hardware ACK/CRC evidence.

### 2026-10-14 — Threshold Alerts control and no-input regression: physical PASS

- [x] Operator reported `THRESHOLD PASS` following the exact
  no-external-GPIO procedure: `OUTPUT → Threshold Alerts` in OFF,
  LEFT/RIGHT cycles FREQUENCY, PULSE DUTY, EDGE COUNT and BUTTON SETTLE,
  UP/DOWN adjust each LIMIT, OK ARM shows WAITING FOR INPUT without
  externally valid samples, armed source/limit editing is locked,
  OK OFF, BACK and re-entry preserve the last source and limit.
  No unwanted alarm, freeze or configuration loss reported.
- [ ] Real live threshold crossing, latched alert, ACK, hysteresis /
  event timing, and valid-sample response remain **NOT TESTED**.
  No-pulse UI acceptance cannot verify sensor/alert triggering.

### 2026-10-14 — PWM/UART/GPIO monitor app-exit resource regression: physical PASS

- [x] Operator explicitly reported `RESOURCE EXIT PASS` following
  the requested no-external-connection test: leave PWM Studio RUN
  through BACK into menu; cycle GPIO Monitor pins and observe PA7
  excluded while TIM1 PWM owns it; UART 115200 can independently
  RUN/STOP without stale BUSY while PWM remains RUN; revisit PWM
  and observe RUN; exit **entire LabMate application** with PWM
  still RUN; relaunch and observe PWM STOP and PA7 once again
  selectable; subsequent I2C Explorer empty scan completes NONE
  and 1-Wire no-sensor test returns NONE without lingering BUSY.
- [ ] This confirms only the specified LabMate-local ownership,
  TIM1/UART coexistence, clean exit/re-entry and no-sensor COMM
  recovery on the matched firmware/FAP pair. It does not prove
  unrelated firmware-service resource exclusion, actual I2C ACK,
  real DS18B20 reading or calibrated GPIO/waveform accuracy.

### 2026-10-14 — PWM background with Logger and Profiles conflict: physical PASS

- [x] Operator explicitly reported `PWM LOGGER PASS` for the exact
  no-external-GPIO sequence: PWM Studio RUN then BACK, Profiles LOAD
  blocked with visible PWM ON and no SAVE/DELETE, Data Logger FREQ /
  PC1 LOW recording while PWM remains active with rows advancing,
  STOP/SAVED and BACK, PWM still RUN on re-entry and then STOP, and
  Log History listing the newly created CSV while preserving old logs.
  This establishes the specified app-local TIM1 PWM and logger capture/
  SD recording coexistence, and safe Profiles LOAD refusal during RUN.
- [ ] This `PWM LOGGER PASS` itself does NOT exercise actual Profiles
  SAVE/DELETE mutations, independent file-content inspection, SD failure
  recovery, or calibrated pulse/frequency capture with external signals.
  Deletion of the disposable new CSV was subsequently physically
  reported PASS in the `HISTORY DELETE PASS` test below.

### 2026-10-14 — Log History disposable CSV real deletion: physical PASS

- [x] Operator explicitly reported `HISTORY DELETE PASS` for the
  immediately requested physical sequence: with PWM/Logger STOP,
  identify the new disposable `log_XXXX.csv`, open its LOG VIEW
  and inspect rows, enter DELETE confirmation for that **same**
  filename, BACK cancels without removing it, re-enter confirmation,
  OK permanently deletes that one test CSV, prior CSV files
  remain listed, and after exiting/reopening LabMate the deleted
  file remains absent while old files remain present.
- [ ] The DELETE test verifies app-visible real single-file DELETE,
  cancel/no-delete and persistence over app reentry. A **different**
  intact log `log_0056.csv` received independent Windows CSV
  content review on 2026-10-15 (details below), but not device-side
  checksum comparison, unexpected SD removal/power-fail resilience,
  or deletion of old non-disposable logs. Preserve preexisting files.

### 2026-10-14 — Profiles S3 real SAVE/LOAD and app restart: physical PASS

- [x] **Before writing:** operator used read-only Windows PowerShell to
  verify that previously archived `profiles_a.bin` and
  `profiles_b.bin` are both present and 32 bytes each in the retained
  LabMate backup `LabMate-Backup-20261014-201529`. This checks
  existence and expected size, **not independently verified binary
  integrity or tested restore**.
- [x] Operator confirmed S3 originally `EMPTY` and then explicitly
  reported `PROFILE S3 SAVE LOAD PASS` following the exact controlled
  physical test: with PWM STOP, select preset **100 Hz**, SAVE only
  to S3 and confirm the SAVE TO S3? prompt; observe SAVED and occupied
  S3; completely exit/relaunch app; observe S3 still present showing
  100 Hz; LOAD S3 and observe LOADED; return to PWM Studio and
  confirm 100 Hz selected while still STOP. S1 and S2 were not
  selected for modification.
- [x] **Disposable S3 actual DELETE / cancel / persistence PASS:**
  operator explicitly reported `PROFILE S3 DELETE PASS` following
  the requested test of DELETE S3? confirmation, BACK cancel
  preserving S3, confirming targeted DELETE, seeing DELETED / EMPTY,
  and fully exiting/reopening LabMate with S3 still EMPTY while
  previously saved S1/S2 remain intact. Together with the earlier
  S3 SAVE/LOAD result, all tested Profiles SD lifecycle operations
  now have actual operator-reported device evidence.
- [ ] SD torn-write or corrupt-copy recovery and independent
  backup-restore verification still remain OPEN.

### 2026-10-15 — USB-downloaded CSV content audit: physical + Windows PASS

- [x] Operator's real Windows PowerShell transcript shows official
  `scripts/storage.py -p auto receive` receiving
  `/ext/apps_data/labmate/log_0056.csv` on `COM7` into
  `Downloads/LabMate-CSV-Audit/log_0056.csv` without writing back to
  the Flipper, with exit status zero and 100% receive.
- [x] Independent `Import-Csv` header comparison exactly matches
  `elapsed_ms,source,pin,valid,frequency_hz,high_us,low_us,period_us,duty_pct`;
  `ROWS: 8`; all rows pass strictly increasing signed integer
  `elapsed_ms` and exact `source=FREQ`, `pin=PC1` checks.
  Visible first three timestamps: 1003, 2003, 3003 ms; final
  three 6003, 7003, 8003 ms; reported `LAST_MS: 8003`.
  Displayed rows use `valid=0`, `frequency_hz=0.000`
  with no externally connected signal, consistent with invalid/
  signal-absent sampling; not an electrical accuracy test.
- [x] SHA-256 **of Windows-downloaded local file**:
  `1BE4426E638B2227AD69ED6D9CA78E82FB406DD8F3DF2196F112AC17015968C3`.
  This is a local SHA-256 audit reference; no matching
  device-side SHA-256 was queried. CSV header, structure, timing
  sequence and sample content are PASS; electrical capture accuracy
  and durability under power/storage faults remain untested.
- [x] **Device-vs-PC MD5 equality physical USB PASS, 2026-10-15:**
  operator ran read-only official FlipperStorage `storage md5` for
  `/ext/apps_data/labmate/log_0056.csv` over COM7, and independently
  computed Python `hashlib.md5` on the locally downloaded file.
  Both returned
  `6c66004157cf7142eb7984441e7e4c18`;
  printed `CSV DEVICE HASH MATCH PASS`, with PowerShell exit-code
  guard not raising an error. The checksum equality confirms this
  copy's bytes match by the device/host MD5 check. It does not
  replace the separate SHA-256 local digest or imply a cryptographic
  security guarantee under malicious collision attacks.

### 2026-10-15 — On-device firmware About identity: screenshot evidence PASS

- [x] User-provided three screenshots from Flipper's firmware/hardware
  information screens (capture filenames dated 2026-10-14 ~21:57).
  The actual display reports device model `FZ.1` and firmware
  `mntm-dev [14-10-2026]`, abbreviated commit `d3f89dfe`,
  and branch label `HEAD`. The abbreviated commit **matches
  the first eight characters** of the project's pinned Momentum
  source `d3f89dfe2ef6b01839201598e9be1590cba80322`.
  An additional visible build label `[87.1] 2.0.0:L` is
  transcribed as display metadata only; no semantic or checksum
  claim is inferred from it.
- [x] This closes **on-device displayed firmware identity** acceptance
  for the reported development build. It does not independently
  verify flashed firmware's complete DFU SHA-256 or the historical
  screenshots' exact contemporaneity with later UARTFIX FAP
  installation. The UARTFIX installation did not request any firmware
  reflash and the DFU hash from the known matched build remained
  `e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0`.
- [ ] Firmware-wide external service resource coordination, safe
  rollback/recovery, optional live peripheral I2C/DS18B20
  hardware acceptance and calibrated electrical outputs remain OPEN.
  Do not publish or retag Stable based solely on this identity PASS.

### 2026-10-15 — OTG UI check: not executable in pinned Momentum Power menu

- [ ] Operator reports no `5V on GPIO` / `OTG Power` control in
  Flipper's `Settings → Power` while attempting the proposed
  read-only OTG UI regression. This is **NOT a LabMate bug report,
  NOT an OTG test failure, and NOT a PASS**. No toggle was used.
- [x] Reviewed exact pinned firmware source
  `Next-Flip/Momentum-Firmware@d3f89dfe` file
  `applications/settings/power_settings_app/scenes/power_settings_scene_start.c`.
  Its Power main list is **Battery Info, Reboot, Power OFF,
  Auto PowerOff, Limit Charge** — no OTG / 5V GPIO item.
  The proposed `Settings → Power` UI test is therefore **not
  applicable to this firmware menu**; do not ask operator to
  find or change a nonexistent setting.
- [x] Source-level inspection of six relevant LabMate production
  modules (`labmate.c`, `labmate_onewire_hw.c`,
  `labmate_generator.c`, `labmate_input_menu.c`,
  `labmate_uart.c`, `labmate_i2c_momentum.c`)
  found no OTG enabling API calls; 1-Wire source comments
  explicitly do not require OTG 5 V. This is **partial source
  evidence**, not a whole-program proof or physical power-state
  measurement.
- [ ] Gate F4 (no automatic USB OTG / 5 V activation) remains
  **OPEN / NOT TESTED** pending a real, non-invasive read-only
  power-state method or independent safe measurement. Do not
  energize external GPIO, change the power setting or claim
  physical 5 V OFF merely from source inspection.

### 2026-10-15 — v1.8 app-exit capture cleanup hardening: SOURCE CI PASS, device retest OPEN

- [x] Reviewed current real production capture, TIM2/EXTI, PWM,
  UART/Expansion, external I2C3 worker, PA4 1-Wire and SD lifecycle
  code; owner/release matrix and exact unresolved firmware-wide scope
  are recorded in [V1_8_RESOURCE_LIFECYCLE_AUDIT.md](V1_8_RESOURCE_LIFECYCLE_AUDIT.md).
- [x] **Real source defect/risk corrected on DEV only:** `src/labmate.c`
  previously conditioned its last `labmate_capture_stop_all` on
  `labmate_screen_uses_gpio(app->screen)`. Normal UI BACK routes
  already released capture, but a stale active owner on future MENU
  exit would skip that final STOP. Production commit
  `d89d2715e246546b1eb07c483d3ba46a3713b5ed` calls
  `labmate_capture_stop_all` unconditionally, snapshots the
  armed capture GPIO before STOP clears the pin index, and releases
  it even after a menu exit. GPIO-only selected input release is
  retained; redundant direct counter/button stops removed because
  the shared STOP already invokes both.
- [x] Source guards `check_v18_coordinator.py` and
  `check_v16_boundaries.py` updated for the safer unconditional
  teardown. Initial CI runs 38645684019/38645836650 failed an
  **obsolete v1.6 structural assertion** that demanded the old
  screen-gated STOP, not a device failure. Guard corrected in commit
  `f865a8099c5ba7d83971933fcff1def51d98b358`.
  [Source CI 38645962260](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38645962260)
  **SUCCESS** (native/SDK + installer mocks). It did not contact
  or update the user's Flipper.
- [x] Full patched Momentum + one real LabMate FAP build workflow
  changed to trigger for **any** `src/**` modification, not only
  UART or I2C module edits. New full [CI run
  38645876409](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38645876409)
  was **IN PROGRESS** when documented. Until it finishes and its
  real outputs/DFU digest are reviewed, do not assign a new FAP hash.
- [ ] **New source is NOT PHYSICALLY INSTALLED or ACCEPTED.** The
  operator's previous UARTFIX ST3, CSV/Profiles, RESOURCE EXIT and
  other actual Flipper passes refer only to the **earlier installed
  FAP SHA256 `eaadc85aba2c8a78074dc97935dc6d71de982582054f8addbeea227428b4f0cf`**.
  Before any new source can be declared device PASS, verify the exact
  patched firmware identity/unchanged DFU SHA, separately pin and
  verify the rebuilt FAP, stage it with fail-closed checks, obtain
  explicit operator approval before any USB installation, and repeat
  the focused capture/pin-exit/UART/COMM regressions.
- [ ] Firmware-wide exclusive lease coordination with unrelated
  services, positive I2C/DS18B20 signal fixtures, calibrated GPIO
  measurements and tested restore are still OPEN. Local owner
  guards and source CI are not substitutes.

### 2026-10-15 — Rebuilt exit-cleanup FAP, exact matched archive: independently VERIFIED (NO USB)

- [x] Full patched Momentum + real integrated LabMate production FAP
  [GitHub Actions run 38645876409](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38645876409)
  concluded **SUCCESS** at source commit
  `a3c52e8ef5ff09c51cd3b5eb40c6c1108cb89e18`;
  compile log contains actual `APPCHK` on `labmate.fap`.
  The 13 MB artifact ZIP (ID `11931799735`) was downloaded
  independently and its six entries were inspected; ZIP integrity
  and embedded `SHA256SUMS.txt` and `PROVENANCE.txt` verified.
- [x] Independently recalculated SHA256 of actual ZIP entries:
  - New **EXITFIX LabMate FAP** `labmate.fap`:
    `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`.
  - **Firmware DFU (unchanged exact pinned patched Momentum)**:
    `e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0`.
  - **Full update TGZ (DO NOT FLASH)**:
    `d7665bf273f69d98aef8bdab06705640833127465d9241c00dff399248b57b18`.
  All equal the independent CI archive's three SHA256SUMS entries.
  PROVENANCE matches the LabMate source SHA, pinned Momentum base
  `d3f89dfe2ef6b01839201598e9be1590cba80322`,
  MNTM012 previous source `e1784e7418d8b074e971983ceb6fef0f37e52ae4`
  and Actions run ID `38645876409`.
- [x] Implemented DEV-only **stage/verify, no USB** PowerShell script
  `scripts/prepare-v18-exitfix-fap.ps1`: pins real CI run,
  exact source/FAP/DFU/TGZ digests, backup of prior working
  UARTFIX FAP SHA
  `eaadc85aba2c8a78074dc97935dc6d71de982582054f8addbeea227428b4f0cf`,
  strict directory contents, manifest/provenance and release warning.
  This script cannot install/flash firmware or update a Flipper;
  validates locally before permitting **separately approved** action.
- [x] Source-only staging safety static guard
  `scripts/check_v18_exitfix_stage.py` integrated into source
  workflow. [CI run 38650032766](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38650032766)
  finished **SUCCESS**: source guard, development FAP compile,
  Windows installer mock PASS; unrelated old v1.7 Stable finalize
  job SKIPPED. CI never wrote to operator's Flipper.
- [x] **Operator Windows stage-only PASS, 2026-10-15:** Windows
  PowerShell executed the pinned `prepare-v18-exitfix-fap.ps1`
  from dev source commit `08b385f41a9664a7ffffcdbe94b7ccf56f94dfe7`.
  Actual output: `SHA256 PASS: previous UARTFIX rollback FAP`,
  `SHA256 PASS: labmate.fap`, `SHA256 PASS: firmware.dfu`,
  `SHA256 PASS: firmware-full-update.tgz`,
  `SHA256 MANIFEST PASS`, `PROVENANCE PASS`, then
  `LABMATE V1.8 EXITFIX STAGE PASS. NO DEVICE CHANGE.`.
  New candidate path:
  `C:\Users\sehmu\Downloads\LabMate-v18DEV-EXITFIX\labmate.fap`;
  new FAP SHA-256
  `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`,
  pinned firmware DFU SHA-256
  `e69f717df28f2ff5a417a69ac212f242cf2725a48ce8c4e31296ceb4a0157ec0`.
  Exit code guard did not raise an error. **No USB install** was
  attempted; previous UARTFIX backup was independently verified.
- [x] **Operator explicitly approved the EXITFIX FAP-only update**
  in project chat on 2026-10-15, **after** stage-only SHA/provenance
  PASS. Approval scope is strictly a replacement of
  `/ext/apps/Tools/labmate.fap` with the pinned candidate SHA256
  `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`.
  No firmware DFU/TGZ flash, other app install, microSD CSV/profile
  deletion or Stable publication is approved.
- [x] **EXITFIX FAP-only USB transfer + launcher-request: REAL DEVICE
  TRANSPORT PASS, 2026-10-15 at 02:10 local.** Operator PowerShell
  confirmed `SHA256 VERIFIED:
  7A76F626F34A65059D9536FA2CD52B2639F4D1038A9B5C69291FA28D5E4F63BE`,
  `Installing to /ext/apps/Tools/labmate.fap via auto`,
  `Using FLIP_UYBELAV on COM7`,
  `Sending ... labmate.fap`, `100%, chunk 10 of 10`,
  `Closing current app, if any`, `Launching app:
  /ext/apps/Tools/labmate.fap`, and
  `SUCCESS: runfap.py exited 0 and requested app launch.`.
  Operator's final guard printed `EXITFIX USB INSTALL COMMAND PASS`.
  This confirms successful reported USB file transfer and app launch
  **request**, NOT verified on-screen startup or STOP/BACK resource
  behavior. Pinned DFU/TGZ were not installed; old UARTFIX rollback
  FAP hash was checked before install. Stable/main unchanged.
- [x] **EXITFIX E1 — Button Analyzer / app exit and relaunch:
  OPERATOR PHYSICAL PASS, 2026-10-15.** On the exact USB-installed
  EXITFIX FAP (SHA256
  `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`),
  the operator performed the requested no-external-wires test:
  enter MEASURE > Button Analyzer, OK RUN ~5 s, OK STOP, BACK,
  exit app, reopen, repeat RUN/STOP. Raw operator result:
  `EXITFIX E1: APP=yes; RUN/STOP=yes; EXIT=yes; REOPEN=yes; ERROR=no`.
  This establishes a real screen startup and basic Button owner/EXIT
  lifecycle smoke PASS; it does **not** establish external button
  bounce accuracy, firmware-wide resource leasing, or whether the
  exceptional stale-capture forced-exit guard was dynamically reached.
- [x] **EXITFIX E2 — Event Counter TIM2 RUN/STOP/RESUME,
  exit and reopen: OPERATOR PHYSICAL PASS, 2026-10-15.**
  On the installed EXITFIX FAP (SHA256
  `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`),
  the operator performed the instructed no-external-signal workflow:
  MEASURE > Event Counter; OK RUN, wait ~5 s, OK STOP,
  OK RESUME, wait ~5 s, OK STOP, BACK, full LabMate exit,
  reopen and another RUN/STOP. Report:
  `EXITFIX E2: RUN/STOP=yes; RESUME=yes; EXIT=yes; REOPEN=yes; ERROR=no`.
  Establishes real TIM2 counter control / normal resource transition
  smoke and reopen PASS, **not** calibrated input pulse counting,
  firmware-wide TIM2 lease exclusivity or abnormal forced-exit behavior.
- [x] **EXITFIX E3 — PWM Studio RUN persistence, Logger START/STOP,
  PWM STOP, full exit/reopen: OPERATOR PHYSICAL PASS, 2026-10-15.**
  With no external GPIO wiring, operator followed OUTPUT > PWM Studio
  OK RUN, BACK (PWM remains active), RECORDS > Data Logger
  FREQ PC1 LOW START ~5 s and STOP, BACK, reenter PWM Studio and
  observe still RUN, OK STOP, full app EXIT, REOPEN and confirm STOP.
  Exact report:
  `EXITFIX E3: PWM RUN=yes; LOGGER START/STOP=yes; PWM PERSIST=yes; PWM STOP=yes; REOPEN=yes; ERROR=no`.
  Confirms the selected tool transitions, permitted app-local PWM +
  Logger coexistence and normal file START/STOP UI on the new FAP
  SHA256 `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`.
  Test can create one additional no-signal CSV; **its content,
  path, valid flags and checksum were NOT audited**. This does not
  measure PWM frequency/duty independently or prove force-exit
  cleanup while generator is *still* RUN.
- [x] **EXITFIX E4 — full app EXIT while PWM RUN, automatic STOP
  on relaunch: OPERATOR PHYSICAL PASS, 2026-10-15.**
  On exact installed EXITFIX FAP SHA256
  `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`,
  operator entered OUTPUT > PWM Studio, set RUN, returned to menu,
  exited LabMate **without manually stopping PWM**, reopened LabMate
  and observed PWM Studio STOP, then confirmed another RUN/STOP
  cycle. Exact report:
  `EXITFIX E4: EXIT_WHILE_RUN=yes; REOPEN=yes; AUTO_STOP=yes; RUN/STOP=yes; ERROR=no`.
  Proves physical UI/state lifecycle and expected auto STOP after
  full app exit. It does **not** independently electrically measure
  PA7 OFF voltage, waveform accuracy, or firmware-global TIM1 lease.
- [x] **EXITFIX E5 — I2C Explorer empty-bus scan, PWM BUSY,
  recovery and BACK: OPERATOR PHYSICAL PASS, 2026-10-15.**
  With external GPIO wiring absent, operator followed COMM > I2C
  Explorer OK on the empty bus (NONE/no devices), BACK; OUTPUT >
  PWM Studio RUN, BACK to menu; I2C Explorer OK reports BUSY;
  BACK, PWM STOP; reenter I2C Explorer and scan normally, BACK.
  Exact report:
  `EXITFIX E5: I2C NONE=yes; PWM BUSY=yes; AFTER STOP SCAN=yes; BACK=yes; ERROR=no`.
  FAP was the installed EXITFIX SHA256
  `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`.
  Establishes real local PWM-vs-I2C exclusion, negative empty-bus
  scan and post-STOP recovery on this tested firmware/FAP pair.
  It does **not** verify positive peripheral ACK, electrical I2C
  transfer correctness, external firmware service contention or
  sensor hotplug.
- [x] **EXITFIX E6 — 1-Wire PA4 no-sensor, PWM BUSY, recovery,
  BACK and app reopen: OPERATOR PHYSICAL PASS, 2026-10-15.**
  With no external GPIO sensor/wiring, operator followed COMM >
  1-Wire Temp and OK, observed NO SENSOR; BACK; OUTPUT > PWM Studio
  RUN and BACK; 1-Wire Temp OK returned BUSY; BACK, PWM STOP;
  1-Wire Temp OK again returned NO SENSOR (not BUSY); BACK,
  close/reopen LabMate. Exact reported outcome:
  `EXITFIX E6: NO SENSOR=yes; PWM BUSY=yes; AFTER STOP NONE=yes; BACK=yes; REOPEN=yes; ERROR=no`.
  Tested with the single installed EXITFIX FAP SHA256
  `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`.
  Evidence covers negative-path GPIO/owner safety and normal
  inter-tool recovery, **not** a physical sensor detection,
  temperature reading, real DS18B20 CRC validation or firmware-global
  PA4 ownership.
- [x] **EXITFIX E7 — UART Terminal no-peer baud / RUN/STOP /
  BACK / reopen lifecycle: OPERATOR PHYSICAL PASS, 2026-10-15.**
  Operator ran the prescribed no-external-device test on the
  installed EXITFIX FAP SHA256
  `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`:
  COMM > UART Terminal, STOP/115200 -> RUN ~5s -> STOP,
  change 9600 -> RUN/STOP, return to 115200 -> RUN/STOP,
  BACK, reenter UART -> RUN/STOP, exit app and reopen.
  Exact reported result:
  `EXITFIX E7: 115200=yes; 9600=yes; RECOVERY=yes; BACK=yes; REOPEN=yes; ERROR=no`.
  This establishes local UART baud transition/resource lifecycle
  and app reopen smoke **without a connected peer**. No actual RX,
  TX, ESP32 READY, byte count/drop or error-rate metrics were
  reported; those remain **NOT TESTED on EXITFIX**.
- [x] **EXITFIX E8 — external ESP32-S2 UART real RX/TX at
  115200, operator physical PASS, 2026-10-15.** On the exact
  installed EXITFIX FAP SHA256
  `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`,
  operator used the previously known ESP32-S2 UART peer, checked
  ESP32_READY, sent AT, observed working receive/response and
  STOP/BACK, and reported counters:
  `EXITFIX E8: READY=yes; TX=yes; RX=yes; R=20699; D=0; E=0; STOP/BACK=yes`.
  This provides meaningful external peer traffic and zero reported
  drop/error **over the observed test**, not a worst-case queue DROP
  proof, independent baud timing calibration, unrestricted sustained
  reliability or simultaneous third-party USART resource contention.
  No device peer firmware change was reported or requested.
- [x] **EXITFIX E9 — non-destructive Profiles / Log History
  read-only UI preservation and app reopen: OPERATOR PHYSICAL PASS,
  2026-10-15.** With the same installed EXITFIX FAP SHA256
  `7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`,
  operator inspected RECORDS > Profiles S1 and S2 without executing
  SAVE, LOAD or DELETE; opened an existing CSV through RECORDS >
  Log History in normal view mode; exited and reopened the app.
  Verbatim result:
  `EXITFIX E9: S1=yes; S2=yes; HISTORY=yes; CSV OPEN=yes; REOPEN=yes; ERROR=no`.
  This proves on-screen presence/readability for checked entries and
  safe read-only navigation, **not** byte-for-byte SD data parity,
  CRC verification of both profile copies or all CSV rows.
- [ ] **EXITFIX E10 — read-only device-to-host file integrity
  snapshot / comparison remains OPEN** pending operator Windows
  PowerShell output. Preserve the prior October 14 LabMate-only SD
  backup and compare matching paths by SHA256; new log files may
  legitimately exist and must not be falsely marked corruption.
- [ ] **Other EXITFIX device regressions remain OPEN:** Profile
  SAVE/LOAD/DELETE behavior on the new FAP (without risking existing
  slots); firmware-service resource contention and safe positive
  I2C/DS18B20 measurement fixtures; hardware-calibrated PWM/TIM2
  measurements; full restore rehearsal and exceptional stale-capture
  exit path. Earlier UARTFIX physical PASS does not automatically
  transfer to EXITFIX; E1–E9 only cover their explicitly recorded
  workflows. Ordinary BACK cleanup does not demonstrate exceptional
  stale-capture exit branch dynamically executed.

## Stable release boundary

Only after **all required** software, matched-firmware and safe physical acceptance gates are reported and verified may a revised `v1.8` Stable asset be considered. Historical source `v1.8` tag provenance must remain immutable; document exact old and replacement source/FAP SHA256, review release asset updates explicitly, then redownload and independently verify the remote asset. No v1.8.1 or v1.9 feature work until the original v1.8 completion decision is satisfied.

**Evidence classification:** CODE IMPLEMENTED ≠ CI PASS ≠ PHYSICAL PASS. A planned test or generated `.dfu` is not evidence of a device result.
