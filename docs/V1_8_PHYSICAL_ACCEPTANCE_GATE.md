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
- [ ] **On-device new LabMate UI and exact patched firmware About are OPEN.** Check About for `MNTM-HEAD` / the expected development identity, confirm actual app screen and the menu order. Real I2C/OneWire, Button Analyzer and full regression remain OPEN. Physical recovery remains UNTESTED.

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
| I4 | Press OK STOP during scan | Returns to STOP/CANCELLED without deadlock and releases ownership | NOT TESTED |
| I5 | BACK during scan, then re-enter and start again | Returns to menu and can reacquire without stale worker/handle | **PARTIAL — operator confirms BACK and re-entry after scan; BACK DURING active scan and new scan still OPEN** |
| I6 | External firmware I²C mutex contention, **only with an independently safe, verified owner** | BUSY/refusal; no arbitrary pin takeover or deadlock | BLOCKED: safe real owner fixture needed |
| I7 | Force probe timeout/fault **only with a safe fixture** | Distinguish non-ACK from transport fault where HAL permits; no leak | BLOCKED: safe fault fixture needed |
| I8 | Repeat STOP and reopen after successful and empty scans | No stuck BUSY, no inherited stale result, no reboot | **PARTIAL — re-entry after empty scan PASS; STOP/repeated runs with ACK still OPEN** |

## Gate 3 — PA4 1-Wire DS18B20

Use one independently verified, compatible, externally VDD-powered **3.3 V** DS18B20 with an appropriate 3.3 V data pull-up. Pin PA4; never assume PB14 is free or auto-enable OTG.

| ID | Check | Pass condition | Status |
| --- | --- | --- | --- |
| W1 | Enter `COMM → 1-Wire Temp` with no sensor | Correct NONE/no-sensor result; no pin leak | **PASS (visible behavior) — operator confirms NONE and BACK; low-level pin-lease validation not independently proven** |
| W2 | Read real DS18B20 | Plausible measured reading + valid scratchpad CRC; no simulated result | NOT TESTED |
| W3 | STOP during conversion, BACK, reopen, read again | Cancellation and resource recovery | NOT TESTED |
| W4 | Legacy capture/PWM/UART/Logger active | App-local conflict is blocked safely; no false ownership claims | NOT TESTED |

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

## Stable release boundary

Only after **all required** software, matched-firmware and safe physical acceptance gates are reported and verified may a revised `v1.8` Stable asset be considered. Historical source `v1.8` tag provenance must remain immutable; document exact old and replacement source/FAP SHA256, review release asset updates explicitly, then redownload and independently verify the remote asset. No v1.8.1 or v1.9 feature work until the original v1.8 completion decision is satisfied.

**Evidence classification:** CODE IMPLEMENTED ≠ CI PASS ≠ PHYSICAL PASS. A planned test or generated `.dfu` is not evidence of a device result.
