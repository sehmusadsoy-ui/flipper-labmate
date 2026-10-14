# LabMate v1.8 Completion — Physical Acceptance Gate (NOT YET APPROVED)

**Branch:** `dev/v1.8-completion` · **PR:** #13 (Draft) · **Stable release:** unchanged `v1.8`.

This checklist deliberately separates compiled source from actual Flipper hardware evidence. Nothing below is a reported device PASS until the operator records a result from the exact checksummed firmware/FAP pair. The existing v1.8 Stable installation and all saved profiles/CSV files must remain intact while these gates are open.

## Gate 0 — Before any device firmware change

- [x] Operator explicitly approved a **temporary, non-Stable custom firmware trial** in the project chat on **2026-10-14**. Approval is not evidence that a backup, installation or physical test occurred.
- [ ] Using qFlipper, create and retain an **internal-settings backup** (Advanced Controls → Backup). This does **not** include saved microSD files.
- [ ] Separately copy relevant **microSD data** to a PC location, including `/ext/apps_data/labmate/` (Profiles S1–S3, Logs/CSV, if present) and preferably a complete microSD backup; inspect the copied files before firmware changes.
- [ ] Prepare an independently tested way to restore the known working Stable Momentum firmware and historical v1.8/v1.7 LabMate. Keep its official updater package and the known-Stable `labmate.fap` available and verifiable. No automatic restore/erase.
- [ ] Record the **currently installed** Momentum version/commit from the Flipper before any update. Do not assume its on-device firmware is the pinned `d3f89dfe` build just because the development SDK was. If incompatible/unknown, pause the minimal-updater trial pending a safe compatibility and recovery review.
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

### Read-only paired-file verification (Windows; no installation)

After obtaining the **specific official GitHub Actions artifact** and extracting its files to a dedicated folder, from the LabMate source root run the following **verification only** in PowerShell (adjust the folder and source SHA to the exact originating CI run):

```powershell
& .\scripts\verify-v18-matched-pair.ps1 `
    -PairDirectory 'C:\LabMate-CI-Pair' `
    -ExpectedSourceSha '0fdd558291222c54f5b52b762e00fafffa3d0d62' `
    -RequireUpdater
```

The verifier rejects missing/mixed files, mismatched firmware/FAP SHA256, wrong pinned Momentum base, missing provenance, and wrong expected LabMate commit. It **never** contacts a USB/COM port, copies a FAP, or flashes firmware. A PASS establishes file self-consistency, **not GitHub download authenticity or physical compatibility**; confirm the artifact's official GitHub Actions origin separately. The mocked PowerShell rejection tests do not prove real hardware functionality.

## Gate 1 — Firmware startup and single-app sanity (after approved installation only)

| ID | Check | Required evidence | Status |
| --- | --- | --- | --- |
| F1 | Test firmware boots and basic OS menu, Back and input work | Operator result + exact build IDs | NOT TESTED |
| F2 | The single LabMate entry launches; shows `v1.8DEV` | Operator result + FAP SHA256 | NOT TESTED |
| F3 | Root order is `MEASURE → OUTPUT → RECORDS → COMM → INFO`; About remains last | Operator screen observation | NOT TESTED |
| F4 | No automatic USB OTG/5 V activation; idle tools do not seize pins | Operator observation | NOT TESTED |

## Gate 2 — External I²C3 functionality

**Pins:** PC0 SCL and PC1 SDA. Firmware API: `furi_hal_i2c_external_acquire_timeout()`. Require a known-safe 3.3 V I²C peripheral for positive-ACK testing; do not infer a device address from host stubs (`0x3C` in tests is simulated). A no-ACK result can also be a bus transfer timeout, so an empty scan alone does *not* prove electrical health.

| ID | Check | Pass condition | Status |
| --- | --- | --- | --- |
| I1 | Enter `COMM → I2C Explorer` on **matching patched firmware** | READY, not `FW API`, no automatic scan | NOT TESTED |
| I2 | Scan an unconnected/known-idle bus | Completes with NONE/no ACK, never fabricates a hit, no freeze | NOT TESTED |
| I3 | Scan a known-safe peripheral with a confirmed 7-bit address | Correct real ACK address displayed; pagination does not change measurements | NOT TESTED |
| I4 | Press OK STOP during scan | Returns to STOP/CANCELLED without deadlock and releases ownership | NOT TESTED |
| I5 | BACK during scan, then re-enter and start again | Returns to menu and can reacquire without stale worker/handle | NOT TESTED |
| I6 | External firmware I²C mutex contention, **only with an independently safe, verified owner** | BUSY/refusal; no arbitrary pin takeover or deadlock | BLOCKED: safe real owner fixture needed |
| I7 | Force probe timeout/fault **only with a safe fixture** | Distinguish non-ACK from transport fault where HAL permits; no leak | BLOCKED: safe fault fixture needed |
| I8 | Repeat STOP and reopen after successful and empty scans | No stuck BUSY, no inherited stale result, no reboot | NOT TESTED |

## Gate 3 — PA4 1-Wire DS18B20

Use one independently verified, compatible, externally VDD-powered **3.3 V** DS18B20 with an appropriate 3.3 V data pull-up. Pin PA4; never assume PB14 is free or auto-enable OTG.

| ID | Check | Pass condition | Status |
| --- | --- | --- | --- |
| W1 | Enter `COMM → 1-Wire Temp` with no sensor | Correct NONE/no-sensor result; no pin leak | NOT TESTED |
| W2 | Read real DS18B20 | Plausible measured reading + valid scratchpad CRC; no simulated result | NOT TESTED |
| W3 | STOP during conversion, BACK, reopen, read again | Cancellation and resource recovery | NOT TESTED |
| W4 | Legacy capture/PWM/UART/Logger active | App-local conflict is blocked safely; no false ownership claims | NOT TESTED |

## Gate 4 — Regression of earlier Stable features

Record **separately**: Button Analyzer START/STOP/RESUME/RESET and preserved completed counts; PWM Studio START/STOP; Counter STOP/RESUME; GPIO Monitor, Frequency and Pulse; UART ESP32 RX/TX RUN/STOP/BACK; Logger/History open and delete confirmation; Profiles S1–S3 LOAD/SAVE/DELETE with real prior data; application exit and re-entry without stuck hardware ownership. Recheck INFO at bottom and COMM directly above. Do not overwrite old CSV or profiles during exploratory tests.

## Stable release boundary

Only after **all required** software, matched-firmware and safe physical acceptance gates are reported and verified may a revised `v1.8` Stable asset be considered. Historical source `v1.8` tag provenance must remain immutable; document exact old and replacement source/FAP SHA256, review release asset updates explicitly, then redownload and independently verify the remote asset. No v1.8.1 or v1.9 feature work until the original v1.8 completion decision is satisfied.

**Evidence classification:** CODE IMPLEMENTED ≠ CI PASS ≠ PHYSICAL PASS. A planned test or generated `.dfu` is not evidence of a device result.
