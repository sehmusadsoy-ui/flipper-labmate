# LabMate v1.8 final-label candidate — FAP-only trial readiness (NOT AUTHORIZED)

**Date:** 2026-10-17 · branch `dev/v1.8-completion` · Draft PR #13.
**Decision:** The offline final-label candidate and prior E11
firmware binary comparison are **PASS**, but **NO DEVICE WRITE IS
AUTHORIZED** by source review, CI or the operator's agreement
to defer equipment tests. This is a constrained *future* decision
memo, not a PowerShell installer or an instruction to flash.

## Why we are not repeating a full firmware flash

The previously tested matched E11 pair, with operator A–G
36/36 functional PASS, H0/H2 real native JS PA7 reads and
PWM RUN/STOP PASS, runs the patched `mntm-dev`
firmware (base `d3f89dfe`) and `v1.8DEV` LabMate.

The exact pinned review images were *both downloaded
independently* and compared by CI
[#39040017389](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39040017389).
The old vs new `firmware.dfu` content is identical
apart from **one embedded version/build-date digit**
(`16-10-2026` → `17-10-2026`)
and the corresponding DfuSe suffix CRC field.
The output plugin `js_gpio.module` is byte-identical.
The final FAP is a newly compiled version-label candidate,
not byte-identical to the deployed E11 FAP. Firmware
compile alone does not prove current *installed* DFU hash
matches the archived candidate, nor does it authorize
installing even just the new FAP.

**Preferred conditional approach:** if further read-only
live identity, current FAP byte backup and binary/SDK
compatibility review agree, a single narrow **FAP-only trial**
may avoid unnecessary full updater/radio/resources/option-byte
side effects. This is preferable to flashing a whole firmware
solely to change the LabMate About badge. A failure or
identity mismatch is a **STOP**, not license to use
full updater, bypass guards or force recovery.

## Exact candidate identity (review only)

| File | SHA256 |
| --- | --- |
| Current operating E11 trial `labmate.fap` | `2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0` |
| Final-label RC `labmate.fap` | `393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61` |
| Original trial `firmware.dfu` | `88d12fee4edb4fa0ec042a1b526ddb41b8db36aeb9554c6a9a8aef1c37e4e1b0` |
| Final-label review `firmware.dfu` | `e7460ab56d72a77bca1c096496ee6dd6d59044bd314ad4cb78559c3aeff72c8b` |
| Both bundles `js_gpio.module` | `fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a` |

Original E11 trial Actions: `#38966248325`, checked
source `ba379f20fb29369501e1057f570a911f71ac83f8`.
Final-label RC Actions: `#39035056937`, checked
source `99cb65d0194dc59d423cfa439c90618ac6b9f114`.
Strict date/CRC binary compare Actions: `#39040017389`.

No new app/source behavior is intentionally changed:
the temporary build overlay only substitutes the UI version
macro `v1.8DEV`→`v1.8` in a throwaway
Momentum build workspace. The Git branch remains DEV.
Independent on-device final binary acceptance still required.

## Before considering a *separately authorized* trial

1. **Stop all activity:** PWM, Counter, GPIO capture and
   COMM operations STOP, LabMate fully exited,
   no external GPIO wire, qFlipper closed while
   using any COM CLI. No SD delete/save/restore.
2. **Read-only identity gate:** on-device firmware
   identity (`mntm-dev` base, API) and exact
   previously pinned installed E11 app FAP,
   `js_gpio.fal`, `js_event_loop.fal`
   plus resource Manifest MD5 must match
   the independent local pinned E11 source package.
   A firmware label/prefix alone is not a full
   firmware binary fingerprint; no alternate
   firmware/API is automatically accepted.
3. **Byte-preserving current app recovery:** take a
   new **PC-only** copy of the actual on-device
   `/ext/apps/Tools/labmate.fap`, record SHA256,
   compare MD5 with the device, and retain it
   with the existing full E11 package, known-good
   backup and signed/verified provenance.
   Never delete or replace the only fallback.
4. **Final binary provenance:** fetch exact
   review-only `#39035056937` artifact,
   verify source/run and all original
   SHA256/Manifest/updater consistency; ensure
   extracted `labmate.fap` SHA matches above.
   Do not use a similarly named old installer
   pinned to another source/binary.
5. **Operator consent:** present in plain language
   that **only one app FAP file** would be
   replaced temporarily on *their* Flipper,
   its exact before/after SHA256 values, the
   planned one-shot revert, and that no firmware,
   radio, option byte or other app/user data
   update is intended. Obtain explicit approval
   for those concrete device-write steps.
   The prior approval to defer equipment-based
   H1/I²C/DS18B20 tests is **not this approval**.

## After a future explicitly approved *app-only* write

These are acceptance criteria, **not completed steps**:

- Independently read back exact new
  `/ext/apps/Tools/labmate.fap` identity;
  verify only that named destination changed.
- Boot genuine single LabMate app, check
  version badge **v1.8**, INFO/About last,
  root `MEASURE → OUTPUT → RECORDS → COMM → INFO`.
  Full app EXIT and reopen, PWM STOP default,
  no crashes.
- Repeat focused safe GPIO/Counter/Button/COMM
  STOP/BACK and prior 3.3V internal loopback
  where a verified lead is available;
  never presume exact-pair PASS solely from
  earlier `v1.8DEV` tests.
- Real 3.3V ESP32-S2 UART peer read/write,
  STOP/BACK and bounded errors **if available**.
  Do not call old UART historical results a
  new `v1.8` paired PASS.
- Test Logger with a **brand-new nonhistorical
  CSV filename only after its separate recording
  scope and backup are agreed**; preserve all
  existing History unchanged. Profiles may be
  written only to an independently confirmed
  disposable EMPTY slot with separate consent
  and preceding slot/data backup; otherwise
  Profile **write persistence remains PENDING**,
  not PASS. Read-only History and S1
  presence can be retested without alteration.
- Native H1 real simultaneous other-client
  `GPIO pin BUSY`, positive real I²C ACK,
  DS18B20 temperature/CRC, independent
  oscilloscope/off-state, exceptional global
  timer/DMA/IRQ third-party RF and actual
  rollback/restore remain recorded
  **DEFERRED/NOT PASS** by agreement.

If any candidate/installed identity differs, if
the app fails loading or reports firmware API
conflict, if STOP fails, data changes unexpectedly,
or firmware operation is requested: **STOP**
and preserve evidence. Do not automatically
reflash, invoke qFlipper repair, change custom
firmware, overwrite profiles/CSV or
reinstall any older FAP without an additional
reviewed recovery decision.

## Stable release integrity is a SEPARATE decision

The public `v1.8` release and tag still
refer to the original reduced-scope binary
`119c44bb854030a73a60fa205d38770bf77f048bb166ab379a03135c1de5f3b0`
and source `02b05639364d6dd71f5eb70456eca379c59218cb`.
Replacing its `labmate.fap` asset alone creates
a source-to-tag mismatch unless explicit
new-build provenance and release metadata
are handled deliberately. A `v1.8.1`
release is **not planned** per operator policy.
Nothing is published, retagged, merged to
`main` or installed here.

**Disposition:** offline final-label candidate is
READY FOR **READ-ONLY OPERATOR PREFLIGHT REVIEW**,
not authorized for a FAP write or v1.8 Stable
publication. v1.9 remains HOLD.

## 2026-10-17 — Owner **explicitly authorizes the controlled app-only trial**, conditioned on preflight

The operator replied **"onay veriyorum"** to the explicitly
described one-file `/ext/apps/Tools/labmate.fap` final-label
device trial: first read-only firmware/app/native-plugin/
resource identity checks and preserved current FAP PC
backup, then **only after those PASS**, a possible
narrow FAP-only replacement (no firmware/radio/option
bytes, no overwrite of CSV, Profiles or any other apps).
This supersedes this memorandum's earlier
"not authorized" wording **for the named conditional
FAP-only trial only**; it is NOT blanket permission
for an updater, USB recovery, install against an
unverified firmware, backup deletion, Stable
publication or v1.9 promotion.

**Phase 1 host implementation prepared, not yet run on the owner device:**

- `scripts/check_v18_e11_final_fap_prewrite_ro.py`
  verifies exact locally pinned original E11 FULL review
  bundle source/run/firmware/FAP/JS hashes, extracts
  expected Event Loop and new Manifest hashes, compares
  `device_info` and remote MD5s of exact
  `/ext/apps/Tools/labmate.fap`,
  `/ext/apps_data/js_app/plugins/js_gpio.fal`,
  `/ext/apps_data/js_app/plugins/js_event_loop.fal`
  and `/ext/Manifest`. It then uses
  `storage read_chunks` **only** to copy the installed
  81,532-byte FAP to a brand-new PC backup folder,
  asserts independently pinned SHA256
  `2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0`,
  re-reads remote identity MD5s and writes a
  PC-only SHA/provenance status with an incomplete marker
  preserved on any failure. There is NO Flipper write,
  rename, upload, JavaScript run or reset in phase 1.
- `scripts/run-v18-e11-final-fap-prewrite-ro.ps1`
  discovers the operator's previous H0 V3 PASS
  transport and SHA-pinned original local E11 bundle,
  retrieves only the read-only helper sources from
  fixed commit `7e49d33ea0020f79afbdec21679521c3a10e0bac`,
  and runs the prewrite check exactly once, with no
  retry and a new PC backup output. Its own
  PowerShell syntax was parsed only on CI, never
  executed against any device by the project agent.
- Strict mock transport negative tests in
  `tests/test_v18_e11_final_fap_prewrite_ro.py`,
  CI [#39040942746](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39040942746)
  ended **SUCCESS**, including PowerShell parser.
  CI proves safety test logic in mocks, **not a
  physical prewrite PASS**.

**Operator action currently pending:** run phase 1
on own stopped, unwired, USB-connected Flipper with
qFlipper closed and post the exact prewrite summary
and new PC backup path (not device identifiers
or private file contents). In a mismatch or
timeout, **STOP**. No new app file has been
loaded to the Flipper yet and no upgrade is
automatically triggered.

Once phase 1 PASS is reviewed, stage separately
the exact offline final-label FAP
`393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61`,
require its independent source/run+SHA checks and
the preserved old FAP backup, then use a separate
one-shot app-only command. This is **not** a
full firmware update.

## 2026-10-17 — First operator prewrite attempt **INCOMPLETE**, Python return-type defect corrected (no device write)

Operator ran the previously SHA-pinned read-only PowerShell
helper on COM7 after stopping and exiting LabMate.
Original paired E11 folder was discovered under the
user's TEMP `LabMate-E11-Trial-*/E11-FULL`.
The pinned native FAP, JS GPIO/Event Loop and Manifest
MD5 identity evaluations reached the backup phase.
The device-to-PC transfer displayed
`>100%, chunk 10 of 10`; the leading `>`
is upstream Momentum's **download direction
character**, not **more than 100 percent** progress.

The actual prewrite helper then emitted:

```text
E11 FINAL PREWRITE NOT ACCEPTED: incomplete/oversized FAP readback
NO FAP UPLOAD AUTHORIZED FROM THIS OUTPUT. DO NOT RETRY BLINDLY.
E11 PREWRITE REFUSED - NO DEVICE WRITE.
```

**Root cause confirmed from exact pinned Momentum
`scripts/flipper/storage.py`:**
`FlipperStorage.read_file()` builds a `bytearray()`
and **returns a `bytearray`** even after a complete
read. Our prewrite verifier (first issued in
`d57f71f10636a927621519ea51f70862dfaf6b67`)
erroneously required `isinstance(content, bytes)`,
making this rejection unconditional for any ordinary
successful upstream transfer. The emitted error did
**not** distinguish a wrong file length from the
return-type mismatch, and **no actual final received
byte count was logged**. This incident is **not**
evidence that the installed FAP was damaged.

Important secondary upstream risk: its
`read_file` uses a single `port.read(chunk_size)`
per chunk, counts requested rather than actual
received bytes, and could return short data after
serial timeout. Therefore the new verifier still
requires **exact 81,532 bytes, pinned SHA256, pinned
device MD5** and a second MD5 screen before it writes
a PC-only copy. It accepts only `bytes` and
`bytearray` as input and freezes a validated
`bytes(content)` value prior to writing. It rejects
short reads or even same-length tampering; no
USB retry occurs automatically.

**Actual status of first attempt:**

- No FAP backup folder with an accepted copy was
  created by the Python helper; only the parent
  PC backup collection folder may exist.
- Existing Flipper app, firmware, SD
  data and resource files were **not changed by
  this read-only helper**; no new FAP was uploaded.
- **E11 final-label prewrite on actual device:
  INCOMPLETE**, not PASS. H1 and previously accepted
  A–G/H0/H2 evidence unchanged.
- Operator was told not to rerun the old command
  blindly.

**Corrected source:** `scripts/check_v18_e11_final_fap_prewrite_ro.py`
commit `c39e791051cfb1108507fbaa372a4a7f91cbcb65`,
with strict synthetic actual-`bytearray`, `bytes`,
short read, corrupt equal-length read, wrong type,
wrong manifest, changed-MD5 and backup-overwrite tests
commit `cf4f911437f8930643c01ef2b0a3d0959b89293f`.
Mock CI
[#39042895162](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39042895162)
**SUCCESS**; all integrated software regressions
[#39042895193](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39042895193)
**SUCCESS**. Operator handoff was repinned to
the exact fixed helper revision
`cf4f911437f8930643c01ef2b0a3d0959b89293f`,
with additional PowerShell-parse-only CI
[#39042932931](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39042932931)
**SUCCESS**.

**Next action:** One *new* explicitly reviewed
**read-only prewrite attempt**, using the
corrected handoff (never old discarded version),
only if Flipper remains stopped/unwired and qFlipper
closed; first copy goes into a NEW empty PC
backup folder. Any new mismatch or timeout
is **STOP/no automatic retry**. Do not proceed
to phase-2 FAP-only replacement until this
actual prewrite copy, live resource hash screens
and local provenance all pass. No firmware/full updater
authorization is implied.

## 2026-10-17 — Final-label trial phase 1 **ACTUAL DEVICE PREWRITE PASS**

Following correction of the pinned Momentum `FlipperStorage.read_file()`
`bytearray` acceptance bug, the operator ran the strictly hash-attested
corrected read-only PowerShell helper **once** on their own COM7 Flipper,
with LabMate fully exited, PWM STOP, external GPIO leads removed and
qFlipper closed. The new read-only device / PC backup checkpoint succeeded:

```text
DUZELTILMIS BETIK DOGRULANDI
E11 V1.8 FINAL PREWRITE: PINNED DEVICE IDENTITY + PC FAP BACKUP ONLY
NO INSTALL/FLASH/SD WRITE/APP RUN/RESET, AND NO AUTOMATIC RETRY.
>100%, chunk 10 of 10 @ 123.95 kb/s
E11 FINAL PREWRITE IDENTITY AND PC FAP BACKUP PASS - DEVICE READ ONLY
old_fap_sha256: 2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0
new_candidate_sha256_not_installed: 393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61
device_identity: PINNED E11 LABEL/APP/JS/EVENT_LOOP/MANIFEST MATCH
E11 FINAL PREWRITE PC FAP BACKUP PASS; DEVICE READ ONLY.
BURADA DUR: Yeni FAP henuz yuklenmedi.
```

**Confirmed by operator evidence:** pinned custom Momentum label and base,
the exact installed E11 old FAP, native JS GPIO and Event Loop plugins,
and resource Manifest matched the original paired E11 package MD5.
The source verifier accepted the byte-exact **81,532-byte** actual old
FAP readback against the pinned old SHA256, screened its MD5 twice,
and created a **new PC-only backup**:

```text
C:\Users\sehmu\Documents\LabMate-FAP-PC-Backups\E11-before-v18-final-b7370882610140aa871dbdf8b61cf53d\installed_E11_v18DEV_before_final_label.fap
```

The directory includes `PREWRITE_READONLY_REPORT.json` and
`READ_ONLY_PC_FAP_BACKUP_VERIFIED.txt`; no historical data, firmware
or SD files were modified by the helper. The `>` progress prefix
comes from the pinned Momentum read/download tool; `>100%` is NOT
a claimed greater-than-100% transfer.

**Scope:** FINAL FAP **PREWRITE PHASE 1 ACTUAL DEVICE PASS**.
This is not a `v1.8` app installation, not an independent
firmware-image readback, and not final-label UI/UART/CSV/Profile
acceptance. The old `v1.8DEV` binary is still installed. Next gate
is offline validation/staging of **exact new candidate**
`393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61`
with preserved immutable PC backup, followed only by a separately
reviewed one-FAP on-device update step. Do not run a full firmware
updater, touch other apps/recordings or mark Stable published yet.

## 2026-10-17 — Actual GitHub RC ZIP independently fetched; exact final single FAP bytes verified (PC ONLY)

Following actual phase-1 Flipper/old-FAP PC backup PASS,
the reviewed GitHub Actions artifact ID `12101802257`
from run `#39035056937` was **downloaded directly
from GitHub** to the analysis container (not to the
operator's Flipper) as
`v18-FINAL-LABEL-E11-PAIRED-REVIEW-DO-NOT-FLASH.zip`.
ZIP SHA256 independently matched
`2c1aa236e566f784c9b94b1da55b6e572e26e8863aeef84972722d1c0eba36bf`.

Exact ZIP content inventory was **seven file members**
(no duplicate/unknown filename), and independent SHA256
over each of the four binary members matched the original
GitHub CI `SHA256SUMS.txt` and pinned expectations.
`PROVENANCE.txt` records exact LabMate source
`99cb65d0194dc59d423cfa439c90618ac6b9f114`,
exact run `39035056937`, Momentum base
`d3f89dfe2ef6b01839201598e9be1590cba80322`,
and native patch diff fingerprint
`1b3851dfa4de1f62d33430c5a7a4cf563f68da4ebfa01fe332fe7984b7630d80`.
Nested full-update TAR member `firmware.dfu` SHA256
agreed with the independently pinned candidate DFU; the
radio binary SHA256 matched reviewed official MNTM012
fingerprint `134a9af448d2bc35995600c9e95723a387c144c2d1adea671086f16f95d327df`.
The ZIP has **NOT** been flashed, run or installed.

Only the final FAP member was extracted to a
**separate PC-only review artifact** named
`labmate_v18_FINAL_REVIEW_ONLY.fap`:
**81,528 bytes**, SHA256
`393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61`.
No internal binary modification was made. The user may
download that standalone reviewed file for an offline
backup-vs-candidate identity check; it must not be
installed merely because this offline source audit PASSED.

Added source guard
`scripts/stage_v18_final_fap_pc_only.py`,
synthetic adversarial tests
`tests/test_v18_final_fap_pc_only.py`, CI
`.github/workflows/check-v18-final-fap-pc-only.yml`;
[CI #39043508705](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39043508705)
**SUCCESS**. The guard requires an independently
sha-pinned final paired review archive and old
device PC-only FAP backup with read-only identity
report, before allowing a new PC-only FAP staging copy.
CI is mocked and did not read the operator's local PC
files. Their actual offline candidate+backup crosscheck
and any on-device FAP replacement remain next separate steps.

**Current result:** Phase-1 real device old FAP backup
PASS; actual final RC package archive source/hash PASS
offline; old-vs-final FAP swap **NOT PERFORMED**;
v1.8 final About/UI physical acceptance **PENDING**,
Stable release untouched, v1.9 HOLD.

## 2026-10-17 — Actual PC-only old/new pair gate PASS; phase-2A safe stage prepared (NOT EXECUTED)

Operator independently checked on Windows and reported:

```text
E11 OLD FAP PC BACKUP PASS
E11 FINAL v1.8 FAP PASS
E11 PREWRITE REPORT PASS
E11 FINAL PC-ONLY PAIR CHECK PASS - NO DEVICE WRITE
```

This combines their earlier actual on-device prewrite and
backup proof with the downloaded exact 81,528-byte final FAP
SHA256. It **does not** mean the final FAP is already on Flipper.

A source-audited safer phase-2A approach is now prepared.
At pinned Momentum source, `storage write_chunk` opens its
destination using `FSOM_OPEN_APPEND` and cannot replace
the old LabMate FAP safely. The CLI's `storage rename` uses
`storage_common_rename_safe` and refuses an existing
destination. Accordingly an app-only transaction is split
into **two explicitly gated operator-observed phases**:

- **Phase 2A stage-only:** make one new non-application
  sidecar file `/ext/apps/Tools/labmate.e11-new-stage`,
  **not** `.fap`. Before its first device write,
  verify the actual old FAP PC backup/report, new candidate
  exact SHA256, original E11 bundle, firmware label/base
  and native JS Event Loop/GPIO/Manifest resource MD5,
  and require both reserved stage and future-backup
  destinations to be ABSENT. Write solely that named
  non-app stage path, check 81,528 bytes and MD5 on
  device, recheck old active FAP unchanged and plugin /
  Manifest MD5. On error **STOP without retry,
  deletion or automatic recovery**. Existing
  `/ext/apps/Tools/labmate.fap` remains unmodified
  regardless of staging success/failure.
- **Phase 2B final promotion (NOT YET PREPARED,
  NOT YET EXECUTED):** only after an
  independently reviewed actual device 2A PASS,
  consider two explicitly scoped safe renames
  to preserve the old FAP under
  `/ext/apps/Tools/labmate.e11-pre-final.bak`
  and promote the verified staged bytes to
  the normal LabMate app path. Must independently
  attest postwrite/live FAP, old copy and original
  firmware resources. Any lack of parity is a
  STOP and separately reviewed recovery action.
  No full updater, firmware flash or user-data change.

**Prepared, mocked source, not actual owner-device PASS:**
`scripts/stage_v18_final_fap_on_device_one_file.py`,
`tests/test_v18_final_fap_on_device_stage.py`,
`scripts/run-v18-e11-final-one-fap-stage.ps1` and
`.github/workflows/check-v18-e11-final-fap-stage-guard.yml`.
[Host stage CI #39044976177](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39044976177)
**SUCCESS**; combined PowerShell syntax and stage guards
[CI #39045061455](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39045061455)
**SUCCESS**. The immutable wrapper source is
`903a55b67d7df94e0654c32952606bc258e21fc9`
and independently checked SHA256 is
`a5ee23a1145fca6782d05c2a615dfb08f9c2f27165a49aea551308082da2b869`.
It downloads source from immutable stage/test
commit `39662e195e0aa748e12f0b5acfeb5aaf6c862f48`.
The wrapper itself was CI-checked for syntax, not
run against a real device by the agent.

**Current gate:** PC original/new FAP pair **PASS**;
phase-2A source/mocks **PASS**; actual Flipper
sidecar stage **NOT YET RUN**; phase-2B old
app rename/new FAP promotion **NOT PERFORMED**.
The original old FAP PC backup shall remain untouched.
Stable publication and v1.9 HOLD.

## 2026-10-17 — Owner phase-2A first real stage attempt **NO-GO: CLI Ready consumed as the first response**

The operator ran the exact SHA256-verified PowerShell
stage-only helper, which printed:

```text
E11 FAP STAGING BETIGI DOGRULANDI
E11 FINAL ONE-FAP STAGE: creates ONLY one non-app .e11-new-stage sidecar.
SOURCE APP PRESERVED. NO FIRMWARE, MANIFEST, JS, USER DATA WRITE.
E11 FINAL ONE-FAP STAGE NO-GO: unexpected staging write command echo
STOP; DO NOT CLEAN UP/RETRY, DO NOT RENAME OLD APP.
E11 FINAL FAP STAGE FAILED; DO NOT RETRY/RENAME/DELETE ANYTHING.
```

**Device 2A FAIL / ABORT, NOT PASS.** Pre-write gate had
checked exact old app, firmware label/base, native JS, Event
Loop, Manifest MD5 and that both reserved paths were
absent. However the stage script reached its first
`storage write_chunk` command and rejected the initial
response before sending any FAP payload bytes.

The exact installed Momentum source
`applications/services/storage/storage_cli.c`
opens a target in `FSOM_OPEN_APPEND` and prints
`Ready\r\n` **as the first line** for
`storage write_chunk`, then waits for binary
payload. Its Python `FlipperStorage.send_and_wait_eol()`
first sends command and then **returns the first line**.
The stage helper incorrectly expected an empty first
return (`b""`) and planned to read `Ready` on
a *second* EOL call. Our first host mocks wrongly
returned empty first line, masking the real transport
error. This is the protocol bug, **not a reported
corrupt firmware/FAP or an accepted stage completion**.

Because the device opened the non-app target before
sending `Ready`, a **zero-byte / partial sidecar may
exist** at `/ext/apps/Tools/labmate.e11-new-stage`.
No FAP binary block was sent by the stage helper prior
to the reported abort. The original app file was
not a write destination in the helper; nevertheless,
**its post-abort actual MD5 has not yet been measured**,
so no blanket post-abort device-state PASS is asserted.
Do not infer stage absence from a Python exception.
Preserve the old working FAP and PC backup.

Pinned Momentum `cli_vcp.c` stops its shell and
breaks/frees its pipe upon a VCP disconnect.
Before any further read-only CLI inspection,
the owner should close all serial programs,
disconnect USB, reconnect USB to establish
a fresh CLI session, with LabMate stopped/exited.
**NO device reset/firmware flash** is requested.

**Corrective offline work, not a device permission:**

- Added read-only post-abort
  `scripts/check_v18_final_stage_after_abort_ro.py`,
  which is restricted to `device_info`,
  `storage stat` and `storage md5` on exact
  old E11 FAP, four native/resource paths,
  reserved stage and old-backup location.
  It distinguishes absent, empty, partial/full
  stage sizes; captures current old FAP and native
  MD5, and **never uploads, renames, removes,
  rewrites or auto-cleans**. New mock CI
  [#39045573509](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39045573509)
  **SUCCESS**, including parser-only PowerShell
  wrapper from commit
  `145c9aca215b900ea587e71edddb1863087b2c42`
  SHA256
  `623dead86bd8999f763cf65f9e51654a1f63834570added95c61b03db8d05e37`.
- Corrected production stage helper to require the
  **first** EOL return to be `b"Ready"` and
  only then send binary; upgraded mocks to match
  actual native source, including unexpected-first-
  response refusal. It must NOT be used for an
  immediate stage retry on the same destination:
  the existing path may be present and must be
  reconciled separately. No cleanup is authorized.
- Phase-2B original FAP safe rename and new FAP
  promotion are **NOT EXECUTED** and withheld
  pending actual read-only reconciliation and
  an independently assessed non-destructive route.

**Immediate next operator action:** run exactly one
fresh read-only abort state check after a clean USB
disconnect/reconnect, report only sanitized stage
status and old app/native parity. If CLI remains
unresponsive or an unexpected file/size/hash exists,
**STOP and do not rerun scripts, reset,
delete sidecar or rename an app**. Stable,
firmware, user CSV/Profiles, Draft PR and
v1.9 gates are unchanged.

## 2026-10-17 — Owner's post-abort exact on-device read-only state: OLD APP PASS, EMPTY SIDECAR

After one unplug/replug USB reset of the stale CLI pipe, the operator ran the
independently SHA-pinned stage-abort read-only script exactly once on COM7.
Their live results:

```text
active_old_fap: PINNED E11 SHA-BACKED MD5 + SIZE MATCH
js_gpio_eventloop_manifest: PINNED E11 MD5 MATCH
reserved_backup_target: ABSENT
stage_status: PRESENT EMPTY 0 BYTES
stage_md5: d41d8cd98f00b204e9800998ecf8427e
safe_to_retry_old_stage_script: NO
final_v18_fap_installed: NO
device_writes_performed_by_this_check: NONE
E11 STAGE ABORT READ-ONLY STATE RECORDED — NO RETRY OR FAP PROMOTION
```

**Real device diagnostic ACCEPTED, source stage upload still NO-GO.**
The pre-existing active old E11 app (81,532 bytes), JS GPIO/Event Loop and
Manifest match their independent MD5 identities. The failed first
`write_chunk` created a `0-byte` non-app sidecar
`/ext/apps/Tools/labmate.e11-new-stage`; its MD5 is the well-known
MD5 of empty bytes. No candidate payload was accepted, no old backup
path exists, and the final FAP has **not** been installed.

**Recovery scope decision:** Preserve this exact empty sidecar. No
deletion/cleanup is necessary or authorized. A new *independently tested
and reviewed* one-shot writer can in principle append the pinned candidate
only after re-checking that sidecar is **still exactly 0 bytes with empty
MD5**, the old FAP/resource IDs are unchanged, old-PC backup is valid
and the destination backup path is still absent. Never retry the old
stage script, write to the old FAP, or treat this read-only PASS as a
stage-upload PASS. Any identity mismatch or failed transfer means
**STOP, preserve evidence, do not automatically retry or clean up**.
Firmware flash, Stable release, app promotion and v1.9 remain on HOLD.

## 2026-10-17 — Exact empty-sidecar resumed-write gate prepared (host only, **not run**)

In response to the operator's real post-abort report that the old
app/native resources PASS and `labmate.e11-new-stage`
exists as **0 bytes** with MD5 `d41d8cd98f00b204e9800998ecf8427e`,
we deliberately chose **no deletion, renaming or automatic
cleanup**. The pinned Momentum `FSOM_OPEN_APPEND` path
can write only to that still-empty nonapp stage after
it is independently checked again. The faulty first
stage script must **never be reused**.

Prepared independent source
`scripts/resume_v18_final_fap_from_empty_stage_once.py`,
10-case native-Ready-first simulated transport test
`tests/test_v18_resume_empty_stage_once.py`,
operator wrapper
`scripts/run-v18-e11-resume-verified-empty-stage.ps1`,
and workflow
`.github/workflows/check-v18-e11-resume-empty-stage-once.yml`.
[Pure host mocked stage #39045995763](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39045995763)
**SUCCESS** and
[combined PowerShell parser + host mocks #39046073195](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39046073195)
**SUCCESS**. These are **not device tests**.

The new code's strict gates, before sending a single
raw stage payload byte:

- Requires the exact original 81,532-byte old app
  backup + read-only two-MD5 PC report, original
  firmware/FAP pinned local provenance, exact
  81,528-byte final candidate FAP SHA256 and
  source/transport path.
- Rechecks the **actual** COM7 device firmware
  identity and old FAP/native GPIO JS/Event Loop/
  Manifest MD5; installed old app must remain
  `File, size: 81532b`.
- Requires the **same nonapp stage** path
  `/ext/apps/Tools/labmate.e11-new-stage`
  to be exactly **0 bytes** and have independent
  empty-content MD5 `d41d8cd98f00b204e9800998ecf8427e`;
  absent/non-empty/unknown-file responses REFUSE.
  Reserved internal old-app backup destination
  must still be absent.
- Requires `Ready` as the **first** native
  `write_chunk` reply; sends only that stage
  path's bytes, checks SD file size after every
  4 KiB-or-smaller acknowledged chunk, and
  checks exact final stage length/MD5 plus
  unchanged original FAP and native resources.
  NO remove/rename/flash/CSV/Profile operations.
  On any mismatch or USB interruption STOP with
  **no retry**. A partial sidecar remains in
  place pending separate review.

Exact immutable handoff wrapper commit
`01d4f089fe62dc3630bac6cc6af4dec2ba9a1dcd`
has independently computed SHA256
`be0996eb4121905818aa9b6459fdb83d63f270d4cde7804db48e54761a42ba91`.
It downloads only helper code pinned to
`3aff361687d57e11dae8b0a7c2cc989bb1ad8d02`.
No previous old-stage helper is invoked or reused
for the upload.

**Gate at this writing:** actual prewrite PASS and
actual aborted-stage read-only state PASS. Host
one-shot empty-sidecar protocol and guard PASS.
**Actual empty-stage payload upload not yet run**,
old `labmate.fap` still installed, 2B promotion
not executed, public Stable/main/v1.9 untouched.
The existing conditional operator consent covers
only this narrow app-only trial path, not cleanup,
firmware update or release publication.

## 2026-10-17 — SECOND real stage NO-GO, CLI echo-model error; ALL DEVICE WRITES PAUSED

Operator independently hash-checked the approved one-shot helper, but
the stage attempt **again aborted before FAP payload transfer**:

```text
E11 BOS STAGE BETIGI DOGRULANDI
E11 v1.8 2A: ONE-SHOT APPEND INTO VERIFIED EXISTING ZERO-BYTE NONAPP STAGE
E11 v1.8 EXISTING-EMPTY-STAGE NO-GO: stage CLI not Ready on first response line; STOP, do not retry
E11 ZERO-SIDECAR STAGE NOT VERIFIED. STOP. Do not retry.
```

**Status:** Real device stage transfer **NO-GO**, NOT PASS.
The new helper accepted the old-app/native/checkpoint preflight and reached
the first `storage write_chunk`. It rejected the first CLI response before
sending application payload. This does **not** prove the stage remains empty
now, and the old FAP/native post-abort state has **not** yet been re-read.
No hardware update/retry/cleanup is authorized on these observations.

**The exact source-backed defect, not guesswork:**
Pinned Momentum
`lib/toolbox/cli/shell/cli_shell_line.c::cli_shell_line_input_normal`
prints each typed character with `printf("%c", combo.key)`.
`cli_shell_line_input_cr` then emits `printf("\r\n")` *before*
dispatching the command. Therefore the first CRLF-delimited line contains
the **echoed command text**. The storage CLI
`storage_cli_write_chunk` then emits `printf("Ready\r\n")`
as a SECOND line after opening the sidecar, and
`FlipperStorage.send_and_wait_eol()` **returns the first line**.
Pinned upstream `FlipperStorage.send_file()` already calls
`send_and_wait_eol()` once without interpreting that first returned line,
then reads the next CRLF-delimited line to detect errors and send bytes.

Both our first host mocked script (incorrectly expecting first response
empty) and second host mocked script (incorrectly expecting Ready first)
misrepresented the actual CLI shell's echoed-command line. This is a
test-fixture defect as well as an implementation defect. **Do not silently
count the previously green mocks as evidence the real-device protocol
was right.** The failure is confined to the transfer-handshake tool based
on the available evidence and is not a demonstrated LabMate GPIO/timer
firmware bug.

**Corrective offline source/test work completed:**
`scripts/stage_v18_final_fap_on_device_one_file.py::append_staged_chunk`
now requires the full **EXACT echoed command text** on first EOL,
then literal `Ready` on second EOL, and sends **NO binary bytes**
unless BOTH match. Host simulator mocks in
`tests/test_v18_final_fap_on_device_stage.py` and
`tests/test_v18_resume_empty_stage_once.py` now faithfully
simulate two native CRLF lines, with adversarial malformed-command
echo, malformed Ready and short transport tests. Latest
independent [stage host CI #39046391251](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39046391251),
[repaired one-shot host CI #39046421535](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39046421535),
[final integrated host CI #39046421523](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39046421523)
are **SUCCESS**. These are **HOST-only** and NOT a new device acceptance.

**Operator safety instruction for now:** STOP all new device writes,
do not rerun either previous stage script or any amended script,
do not reset, delete/rename/recover a sidecar, install a FAP,
or flash firmware. Keep the old verified PC FAP backup immutable.
When the owner is ready, first establish a fresh USB CLI session
and run the already approved, fixed-path **read-only aborted-stage
inventory and MD5 check** again to establish whether the existing
sidecar is still empty and the old app/native hashes unchanged.
Only after the exact resulting state is recorded should any future
one-shot stage write be separately reviewed; no third upload
attempt is being requested in this response. Phase 2B app promotion,
Stable publication and v1.9 remain HOLD.

## 2026-10-17 — Second actual abort FOLLOW-UP LIVE READ-ONLY PASS; serial echo preflight staged (NO FAP writes)

Owner performed the previously trusted, immutable, read-only COM7
`run-v18-e11-stage-abort-readonly.ps1` **once after the second failed
staging attempt**, using a fresh USB connection. Exact reported outcome:

```text
E11 SALT OKUNUR KONTROL DOGRULANDI
active_old_fap: PINNED E11 SHA-BACKED MD5 + SIZE MATCH
js_gpio_eventloop_manifest: PINNED E11 MD5 MATCH
reserved_backup_target: ABSENT
stage_status: PRESENT EMPTY 0 BYTES
stage_md5: d41d8cd98f00b204e9800998ecf8427e
safe_to_retry_old_stage_script: NO
final_v18_fap_installed: NO
device_writes_performed_by_this_check: NONE
E11 STAGE ABORT READ-ONLY STATE RECORDED — NO RETRY OR FAP PROMOTION
```

This *second* live readback independently confirms the installed
operator-tested v1.8DEV FAP and its paired native JS/event loop/manifest
are unchanged, and the sidecar remained completely empty after the
second aborted CLI attempt. It is **not** proof of any new v1.8 FAP
write or application boot; no stage bytes transferred. The preserved
PC backup remains the only accepted recovery artifact for the old FAP.
**No automatic repeated upload** is permitted.

The serial source review found our two false host assumptions about
`send_and_wait_eol()` command echoes. We now have native-source evidence
of CLI character echo, command-finalizing CRLF, and separate
`write_chunk` Ready, but **no actual device capture of this precise
two-line framing before starting a new write**.

To replace that missing evidence without another append attempt,
created **read-only** `scripts/probe_e11_cli_echo_stat_ro.py`. It
sends **only** a fixed harmless `storage stat` of the already known
empty sidecar and measures the first echoed command line and
second size line, validates prompt framing, and rechecks old FAP,
native resource MD5, stage empty-size/empty-MD5 and absent future
backup target. It never sends a `storage write_chunk`, append,
rename, remove, launch, reset or firmware command. This probe can
verify the live CLI command echo for a *stat command*; it does NOT
directly validate the write_chunk Ready handshake and does not by
itself authorize staging.

Source:
`scripts/probe_e11_cli_echo_stat_ro.py`;
mock/negative tests:
`tests/test_e11_cli_echo_stat_ro.py`;
PowerShell handoff:
`scripts/run-e11-cli-echo-stat-ro.ps1`.
[Host-mock+PowerShell syntax CI #39046959395](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39046959395)
**SUCCESS**. No serial hardware access was made by the CI.
The immutable checked operator wrapper is at commit
`e34926ef2a1354e2ebad7fe12a6ee02234a91d10`,
SHA256
`6e9407c78577d45e515275acd8ab4358e30ecd06382e600b6c6341067ba05f48`.
Internally it pins Python source
`b150466978a3f8735f78de974b76a4a740010881`.
No operator execution of this *new* echo probe has yet been reported.

**Gate:** all device writes remain PAUSED; a read-only live
command-echo probe is the only proposed next operator action.
If framing differs or CLI hangs, STOP and report, no repeat,
cleanup, reboot or FAP swap. Old `v1.8DEV` stays active, final
`v1.8` FAP PC-only, Draft PR #13 not merged, Stable unchanged,
v1.9 HOLD.

## E11 native echo probe operator result — 2026-10-17

Actual COM7 read-only check returned `EXACT_COMMAND_ECHO`, `EXPECTED_EMPTY_FILE`, pinned old active FAP size 81532 and MD5 PASS, native resources MD5 PASS, stage PRESENT EMPTY 0 bytes with verified empty MD5, reserved backup target absent. `write_chunk_ready_probed: NO`; no FAP upload, app replacement or firmware/data change. The real first CLI line is the command echo for a stat command. This result is not a successful binary upload test. Previous faulty stage scripts remain prohibited.

## Final reviewed ONE-SHOT non-app empty-sidecar stage handoff (2026-10-17, NOT YET RUN)

Source-backed actual device CLI echo evidence is recorded immediately
above. The original retired `run-v18-e11-resume-verified-empty-stage.ps1`
wrapper **must not be used** because it pins a flawed Ready-first helper.

Prepared a distinct operator handoff
`scripts/run-v18-e11-empty-stage-echo-verified-once.ps1`,
immutable source ref
`5c535ff2f37bd66ed1afc5851cb4acb63f25c4f6`,
independent ASCII source SHA256
`3375790133c11829db22c0d7fa6b2ac8ad195b72600cf4c4c6d9d7ec7f10b497`.
This wrapper pins tested helper code to immutable commit
`8f35e5a782743cc1019f322dfcd53445ac61cd3a`
(which includes corrected **native CLI command echo first,
Ready second**, strict zero-stage MD5/size, old original E11
FAP/native resource checks, actual previous verified PC old
FAP backup and final candidate SHA256 checks, per-chunk size
attestation and stage-complete MD5).

[Dedicated combined host CI #39048221398](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39048221398):
**SUCCESS**, including PowerShell parser, immutable source pin
screen and modeled native shell echo second-line Ready transfer.
This **is not** an actual successful device upload.

**Permitted stage-only behavior if the operator chooses to execute:**
append exactly 81,528 reviewed candidate bytes to an ALREADY
PRESENT `/ext/apps/Tools/labmate.e11-new-stage`
ONLY if it is STILL **0 bytes** and matches empty MD5.
No app promotion, no rename, no deletion, no old-FAP write,
no firmware, Manifest, other apps, CSV or Profile modification.
On the first anomaly, STOP and preserve the current stage state;
NEVER automatically retry or clean up, even after a partial chunk.
The old working app, PC old FAP backup and Stable remain unchanged.

**Current status when this handoff was prepared:** prewrite,
PC old/new pair, and real device post-abort/native CLI read-only
PASS; corrected stage procedure HOST PASS. **Third actual stage
upload not yet executed**, no new final-label app installed,
all final functional acceptance and release gates PENDING.

## 2026-10-17 — ACTUAL PHASE 2A FULL STAGED FAP PASS; PHASE 2B PREPARED IN HOST CI

Owner's exact E11 device report following the pinned echo-first,
Ready-second one-shot staged transfer:

```text
stage_fap: SHA-BACKED DEVICE MD5 / SIZE MATCH
stage_path: /ext/apps/Tools/labmate.e11-new-stage
stage_md5: 8d44e6ecce500036a8314a8c0e961806
stage_bytes: 81528
active_old_labmate: PINNED OLD MD5 + SIZE UNCHANGED
native_js_manifest: PINNED RESOURCE MD5 UNCHANGED
old_pc_backup: PINNED VERIFIED
new_v18_fap_installed: NO
firmware_flash: NO
stage_update: ONLY EXISTING EMPTY NONAPP SIDECAR
automatic_retry_or_cleanup: NEVER
E11 v1.8 EXISTING EMPTY STAGE FULL VERIFIED PASS - OLD APP PRESERVED
STOP; PHASE 2B APPLICATION PROMOTION NOT PERFORMED
```

This is the first REAL DEVICE stage acceptance. The on-device
81,528-byte staged FAP MD5 `8d44e6ecce500036a8314a8c0e961806`
was compared independently with the byte-verified PC candidate
81,528-byte SHA256
`393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61`
and MD5 `8d44e6ecce500036a8314a8c0e961806`.
The original 81,532-byte active E11 `labmate.fap` remains
unchanged by device MD5/size; verified original FAP PC backup
exists. No original active app file rename, app load, firmware
update, old data mutation, Stable release or v1.9 start.

**Phase 2B source-only groundwork, NOT executed on user Flipper:**
Reviewed installed pinned Momentum C source
`storage_cli_rename()` uses
`storage_common_rename_safe()`; refuses destinations that
already exist, and handles same-filesystem renaming.
`storage_cli.c` prints no payload on successful rename, and
native shell appends CRLF before prompt. Flipper's
`send_and_wait_eol()` receives the exact echoed command
first. Proposed `scripts/prepare_v18_e11_phase2b_safe_promote.py`
with 12 negative and success host-only mock tests
`tests/test_v18_e11_phase2b_safe_promote.py`.
[Dedicated host phase2B review CI #39048792386](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39048792386)
**PASS**; [integrated host regression #39048792395](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39048792395)
**PASS**. These are *simulations* and do not prove
device 2B success.

Phase 2B is **not an atomic transaction** and there
is a real temporary interval when the LabMate app path
does not exist. Intended narrowly scoped two steps,
subject to separate operator acceptance:

1. After rechecking old FAP, full verified staged FAP,
   unchanged native resources, exact local backup and
   **absent** reserved backup target, rename only
   `/ext/apps/Tools/labmate.fap` to
   `/ext/apps/Tools/labmate.e11-pre-final.bak`.
   Verify old backup SHA-backed MD5 + 81,532-byte
   size, old path absent, staged final still intact.
2. Rename only
   `/ext/apps/Tools/labmate.e11-new-stage` to
   `/ext/apps/Tools/labmate.fap`, target now
   absent; verify new installed 81,528-byte
   FAP MD5, previous old backup 81,532-byte
   MD5, staged file absent, native GPIO/Event
   Loop/Manifest unchanged. No FAP app run here.

**Interruption semantics:** If any step times out
or fails after old app is renamed, the app may be
temporarily absent from its normal menu path even
though its original contents remain preserved
in the on-device `.bak` and original PC backup.
NO automatic retry, rollback, delete or reflash:
record exact new state with bounded read-only
diagnostics, then separately decide next action.
If both renames succeed, this is only a file identity
PASS; actual v1.8 GUI/About version, lifecycle,
PWM STOP, UART, Logger and profile tests still PENDING.

Phase 2B device run / operator-specific handoff
**not yet authorized or performed** as of this
document. Maintain DRAFT PR #13, main/tag/Stable
unchanged and v1.9 HOLD.

## 2026-10-17 — Explicit owner approval for E11 v1.8 phase-2B TWO FAP RENAMES

The owner explicitly replied **"onay veriyorum"** to the two specific
same-SD `storage rename` operations, after being told that LabMate's
normal FAP app path could temporarily disappear if interrupted between
renames. This is **not** permission to flash firmware, delete app/data,
perform automatic retry/restore, change other apps, publish Stable,
merge Draft PR #13, or launch v1.9.

**Already proven real device stage-2A:** stage file
`/ext/apps/Tools/labmate.e11-new-stage` contains precisely 81528 bytes,
device MD5 `8d44e6ecce500036a8314a8c0e961806` matching
independent locally verified final candidate. Active previous LabMate
81,532-byte FAP MD5, native JS GPIO/Event Loop, Manifest and PC
old-FAP backup remain unchanged. No final FAP application activation
has occurred as of this note.

**New device operator phase-2B runner prepared, not yet executed:**
`scripts/run-v18-e11-phase2b-promote-two-fap-renames.ps1`
at immutable source revision
`99c791d54fca04e24f2e73125018b55ec6288e01`,
verified UTF-8 ASCII SHA256
`61f86aabbf1de2da05221a7bf2e3067dc85b2444a1a5d7ed710ce4fe71b9fa64`.
It pins all Python preflight/rename code to immutable commit
`086275b82205ad16750fca893e6aa66300f985b4`.
Hard gates: exact original actual device FAP PC backup and 2x
live-read-only report, old candidate source and native plugin/Manifest,
original paired firmware source, independent new final FAP local
SHA256/size, original pinned COM7 H0 transport, and live SD state
(original installed old FAP MD5+size, complete staged new FAP
MD5+size, reserved backup path absent, firmware label/base and native
resource MD5). No writes before all checks pass.

If all gates match, only two `storage_common_rename_safe`
same-directory CLI renames are attempted and each step has exact
command echo and error/prompt verification:
(1) `labmate.fap` -> `labmate.e11-pre-final.bak`,
verify old device backup MD5/size + active app absent;
(2) `labmate.e11-new-stage` -> `labmate.fap`,
verify new active FAP MD5/size + old device backup MD5/size +
stage absent + native resource parity. No auto retry/rollback/delete.
[Phase2B host CI #39049675255](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39049675255)
**SUCCESS** (host mocks + PowerShell wrapper syntax/pin);
separate [host 2B rename CI #39048792386](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39048792386)
**SUCCESS**. **No operator real 2B output yet.**

**Non-destructive interrupted-state classifier prepared BEFORE
physical 2B:** `scripts/check_v18_e11_phase2b_state_readonly.py`,
`tests/test_v18_e11_phase2b_state_readonly.py` and
`scripts/run-v18-e11-phase2b-state-readonly.ps1`, immutable
wrapper revision
`5630369f37684e22a35ebc8574e9b19a30259247`, SHA256
`74f62d3d6bd7be4a677d1211ad31f9e83966dbec28f084d84fe704aa7f127dcc`.
Read-only classifier recognizes exactly
BEFORE_PROMOTION (old active / staged final / no device backup),
BETWEEN_TWO_RENAMES (app absent / staged final / original in bak),
or AFTER_PROMOTION (new active / stage absent / original in bak),
with pinned all-files MD5 and firmware/native resource matching.
[CI #39049683474](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39049683474)
**SUCCESS**. Reject unknown or mismatched states. No automatic
recovery/retry. If phase-2B device action errors after first rename,
operator must STOP, preserve PC backup, and request fresh
read-only state verification — do not rerun 2B.

**Status:** Phase2A actual device PASS; 2B exact owner permission
recorded; source, synthetic tests, read-only recovery plan PASS.
**Phase2B REAL DEVICE RENAMES NOT YET EXECUTED at this note**.
New v1.8 GUI functional, version INFO, PWM default STOP,
button/counter, UART, logger/profile persistence tests PENDING.
Stable/main/unpublished release and v1.9 HOLD.

## 2026-10-17 — ACTUAL E11 PHASE 2B TWO-RENAME FAP PROMOTION: PASS (DEVICE FILE IDENTITY)

The operator executed the previously consented and independently
SHA256-verified immutable phase-2B PowerShell runner on COM7.
Actual user-provided device stdout, copied without reinterpreting
the phase-2B / runtime distinction:

```text
E11 FINAL AKTIVASYON BETIGI DOGRULANDI
E11 FINAL PHASE 2B - TWO PINNED SAME-DIR SAFE RENAMES ONLY
E11 PHASE 2B TWO SAME-DIRECTORY SAFE RENAMES (NOT FULL FIRMWARE FLASH)
result: E11 FAP-ONLY PROMOTION FILE IDENTITY PASS
active_fap: /ext/apps/Tools/labmate.fap
active_new_fap_md5: 8d44e6ecce500036a8314a8c0e961806
old_fap_device_backup: /ext/apps/Tools/labmate.e11-pre-final.bak
old_fap_device_backup_md5: edc86bf6ccb2e9b0215f2903b6f6725f
stage_now_absent: YES
native_js_manifest: UNCHANGED
firmware_flash: NO
user_csv_profiles: NOT ACCESSED
new_v18_app_boot_test: PENDING
stable_release: NOT AUTHORIZED
E11 2B FAP-ONLY FILE PROMOTION PASS - v1.8 DEVICE GUI STILL PENDING
E11 PHASE 2B FILE PROMOTION VERIFIED - DEVICE GUI NOT YET TESTED
STOP HERE. Share output BEFORE launching final LabMate.
```

**GATE: ACTUAL DEVICE PHASE 2B PASS FOR FAP FILE ACTIVATION**, not merely a
host simulation. Both same-directory safe renames completed. The
active `labmate.fap` now holds the final review-only v1.8-label
candidate, exactly the previously stage-2A-verified 81,528-byte
FAP MD5 `8d44e6ecce500036a8314a8c0e961806`
(SHA256 from PC file
`393fe3e52aa710162a42d7299aa053f538b2ee1ad6542755cf402b83c1931b61`).
The original device-tested v1.8DEV 81,532-byte FAP is retained at
`/ext/apps/Tools/labmate.e11-pre-final.bak`, MD5
`edc86bf6ccb2e9b0215f2903b6f6725f`.
Its independently pinned PC copy remains untouched, along
with the complete original E11 candidate bundle. The
nonapp staging filename is absent after rename. The script
revalidated the source/destination file identities,
native JS GPIO/Event Loop/Manifest hashes and preserved
old backup after these changes. It issued NO firmware flash,
no other-app write and no CSV or Profiles mutation.

**Remaining runtime acceptance — NOT YET PASS:**
This proves on-device SD file identity only; it does not establish
that final FAP launches, About shows `v1.8`,
menu ordering `MEASURE → OUTPUT → RECORDS → COMM → INFO`
(with INFO last), reliable STOP/BACK/EXIT or re-open,
PWM starts STOPPED, UART/ESP32 peer behavior, GPIO/timer
resource arbitration, logging, profile/history persistence
or hardware/bench tests on the *new* candidate.
Prior v1.8DEV A–G 36/36 and earlier main Stable physical
test evidence is separate and must not be relabeled as
acceptance of this exact newly installed FAP.

**Next controlled operator step: GUI smoke test without GPIO wiring
or SD write operations.** On device navigate to Applications /
Tools / LabMate, launch exactly once, verify visible v1.8
in INFO/About and INFO is the last root menu item,
verify COMM appears above INFO, check PWM is STOP by default,
use BACK/EXIT, then reopen and exit again. If crash,
missing app, version mismatch or any unsolicited output,
STOP; no automatic retry, recovery, file rename or firmware flash.
No generator RUN, logger START, profile SAVE/DELETE or any
connected external GPIO hardware as part of this smoke test.
The separate H1 LIVE BUSY, calibration, DS18B20/I2C,
switch-bounce and SD fault trials remain deferred until
appropriate physical setup.

**Branch/release:** Keep PR #13 DRAFT, `main`
and existing public Stable tag/assets unchanged, v1.9 HOLD.
Do not infer a new Stable release from this private E11
app-only final-label file promotion.

## 2026-10-17 — REAL installed E11 final-label v1.8 GUI smoke: 5/5 USER PASS

After actual phase 2A candidate FAP staging and phase 2B
protected same-directory two-rename activation passed exact
device MD5/size checks, the operator performed the requested
limited *newly installed final v1.8* no-GPIO-wiring
startup/lifecycle test and reported verbatim:

```text
Açılış: PASS / Menü: PASS / About v1.8: PASS / PWM STOP: PASS / EXIT-REOPEN: PASS
```

**Accepted real physical E11 FAP runtime acceptance, limited scope 5/5:**
new active `/ext/apps/Tools/labmate.fap` successfully launched;
root UI navigation/menu-order inspection passed
(`MEASURE → OUTPUT → RECORDS → COMM → INFO`, with INFO last
as previously requested); INFO/About reports `v1.8`
not `v1.8DEV`; PWM enters **STOP** by default; BACK/complete
EXIT and reopen/exit worked. No GPIO wiring was requested
for this smoke test; no PWM RUN, Logger START, Profile SAVE/DELETE
or destructive SD steps were part of the requested checks.
The operator returned all five PASS, not a video or an independent
digital-capture trace.

Previously proven **file identities remain as recorded in
phase 2B** (new candidate MD5
`8d44e6ecce500036a8314a8c0e961806`
at active FAP, old original E11 FAP MD5
`edc86bf6ccb2e9b0215f2903b6f6725f`
retained in `labmate.e11-pre-final.bak` and a verified PC backup).
This runtime pass is **not** a new post-launch SD MD5 readback.
No firmware, native resources, user CSV or profile write
is authorized or claimed here.

**Pending for this exact new final FAP:** passive navigation
and safe screen-exit tests beyond the five-item smoke;
read-only Log History/Profile review preserving data;
separately authorized disposable scratch CSV/logger and
empty-slot Profile persistence only after backups;
real ESP32-S2 UART peer / STOP/BACK;
Button Analyzer, Counter and PWM under bounded safe loopback;
native JS GPIO/Timer1/Timer2/EXTI owner conflict
including H1 simultaneous BUSY still not proven;
bench calibration, DS18B20 positive, I2C ACK, switch bounce
and fault-path physical cases remain deferred when equipment
is absent. An earlier `v1.8DEV` hardware PASS or the
historically published v1.8 Stable PASS does not replace
the new final E11 FAP acceptance.

**Release boundaries unchanged:** This is a private custom
patched E11 device's accepted file activation + 5/5 GUI smoke,
not a new public Stable artifact, main/PR merge,
cross-firmware compatibility sign-off or v1.9 opening.
Draft PR #13 still DRAFT, Stable/main unchanged.

## 2026-10-17 — REAL installed E11 final-label v1.8 passive-records/UART navigation: 3/3 USER PASS

After the first limited 5/5 runtime acceptance of this exact
newly installed E11 final-label `v1.8` FAP, the operator
completed the separately requested no-wire, nonmutating
follow-up and reported **verbatim**:

```text
Log History: PASS / Profiles S1: PASS / UART STOP-BACK: PASS
```

**Accepted real device scope:** existing Log History CSV
can be opened/viewed and exited with BACK; an existing
Profiles S1 slot can be viewed without save/load/delete;
COMM/UART Terminal opens and returns via STOP/BACK
without transmitting anything. Combined with the
five earlier startup/menu/About/PWM-default/exit checks,
this is **8/8 user-reported safe user-interface checks
on the exact newly installed candidate**. No Profile
LOAD/SAVE/DELETE was approved or claimed and no
CSV data-write operation was part of this check.
UART's STOP/BACK PASS is **not** a live ESP32-S2
RX/TX or baud-rate accuracy test; visual Log History
is **not** a new Logger CSV recording test.

**Gates still open:** real final-candidate Frequency Meter
and Pulse Analyzer signal behavior, PWM output and STOP
under scoped 3.3V loopback, TIM2 Counter and Button
Analyzer physical behavior and resource-release/owner
conflict (especially H1 simultaneous BUSY), real UART
ESP32-S2 peer transfer, disposable scratch Logger CSV
and backup-gated empty Profiles slot write; separately
deferred DS18B20 positive, I2C ACK, switch bounce
and instrument calibration where equipment is absent.
Maintain prior v1.8DEV hardware evidence as *historical
for a different binary*, not an automatic PASS here.

**No SD install/write, firmware flash, resource replacement,
cleanup or Stable publication occurred in these 3 new
screen-level tests.** Preserve the device old-FAP `.bak`
and original verified PC backup, retain Draft PR #13,
existing public Stable/main unchanged, v1.9 HOLD.

## 2026-10-17 — Final E11 v1.8 no-signal instrument screens/exit: 4/4 USER PASS

After actual final-label candidate file activation, operator GUI smoke
5/5 and read-only History/S1/UART screen checks 3/3, the operator
completed the proposed no-wire instrument screen/open/STOP-BACK
checks on that same installed FAP and returned **verbatim**:

```text
Frequency: PASS / Pulse: PASS / Counter: PASS / Button: PASS
```

**Acceptance scope:** Frequency Meter, Pulse Analyzer,
Counter and Button Analyzer were opened and exited safely
on the actual new E11 v1.8 FAP with no externally supplied
signal. Operator-reported UI/lifecycle checks now total
**12/12 PASS** across the separately scoped 5/5, 3/3
and 4/4 groups. This validates safe instrument screen
navigation/return, **not** electrical signal capture,
frequency/pulse timing, TIM2 counter accuracy,
button bounce interpretation, GPIO exclusivity or true
cross-service release/ownership arbitration. A no-signal
readout is not a calibration test.

**Still pending for this exact FAP:** real 3.3V input
measurements and bounded PWM generator with STOP,
Counter/Button electrical tests, real ESP32-S2 UART
peer (the earlier v1.8DEV E1–E6 pass is NOT reused),
native H1 simultaneous competing-resource BUSY,
independent calibration, and backed-up disposable
CSV/Profile write persistence. Sensor I2C ACK and
DS18B20/switch physical positives remain deferred
until appropriate equipment. No new FAP install,
firmware or data alteration is claimed from these
screen-only tests.

**Next recommended scoped gate:** use only previously
verified 3.3V hardware wiring and proven ESP32-S2
UART test peer when actually available; never assume
it is connected or consent to modify its firmware.
Check RX `ESP32_READY`, bounded explicit TX
`AT` → `ESP32_OK`, and repeated STOP/BACK without
unsafe GPIO wiring, at the peer's known baud. If
hardware is not connected/prepared, defer live UART
and proceed with other read-only tests. Stable/main,
device old `.bak`, original old PC FAP backup, Draft
PR #13 and v1.9 HOLD unchanged.

## 2026-10-17 — New E11 final v1.8 FAP external ESP32-S2 at 115200: E1 PASS / one AT-induced ST2 stress, E3 unobserved

Operator report verbatim after the first real external UART test on the
**new installed** E11 final-label v1.8 FAP:

```text
E1 ESP32_READY: PASS / E2-E3 AT→ESP32_OK: FAIL / UART STOP-BACK: PASS
Notlar: fail bastım çünkü karta tx geçince stress test yaptı ama ondandan sona da ESP32_ready geldi sorun olmadı ?
```

**Source-based cause, not an established LabMate defect:** The
currently plausible installed ESP32 firmware is the prior ST2 test
fixture `tests/esp32_s2_wrover_uart_stress_115200/esp32_s2_wrover_uart_stress_115200.ino`,
not the simpler interoperable echo-only firmware
`tests/esp32_s2_wrover_uart_peer/esp32_s2_wrover_uart_peer.ino`.
The actual ST2 sketch's `handleLine()` on exact `AT`
responds `ESP32_OK\r\nSTRESS_ARMED\r\n`, arms a burst after
1200ms and emits `BURST_BEGIN` / up to 20,480 ASCII bytes /
`BURST_END` in a bounded transfer. Once idle it again
sends `ESP32_READY` about every 3s. Thus user-observed
AT-induced stress plus later READY is exactly **consistent**
with the ST2 sketch's intended behavior.

**Evidence rating (do not invent unseen RX):**
- E1 PASS (explicitly saw periodic `ESP32_READY`).
- Flipper STOP/BACK PASS (explicitly reported).
- E2 TX-to-peer **strong functional evidence** from AT specifically
  arming the ST2 sender (assuming this known flashed sketch).
- E3 `ESP32_OK` on the new app is **NOT OBSERVED / not yet PASS**
  because the operator did not report seeing that exact response;
  it may have scrolled out during the stress data burst.
- The original combined E2/E3 check must be listed
  **INCOMPLETE/FAIL to confirm exact string**, not diagnosed as
  broken TX without evidence.
- No numeric `R/D/E`, burst sizes, independent timing or
  error counts were supplied for this *new* E11 v1.8 run;
  old v1.8DEV ST2 R=20569/41281 D=0 E=0 belongs to the
  previous FAP and must NOT be copied into this record.

**Safe continuation:** Do not repeatedly send `AT`
just to seek `ESP32_OK` with the ST2 firmware, because
each `AT` arms another load event. No ESP32 reflash,
USB double-power, FAP change or GPIO reconnection
has been requested/approved. If the user later wants an
isolated E2/E3 text assertion, first identify/choose a safe
nonstress peer firmware and obtain independent explicit
approval for any ESP32 firmware overwrite; alternatively
a scoped one-shot burst test with a prearranged visual
capture could be considered but is not required now.
Maintain Draft PR #13, stable and v1.9 HOLD.

## 2026-10-17 — External UART ST2 follow-up clarified by operator: AT-controlled burst and response present

Following the first combined E2/E3 check being conservatively recorded
FAIL/unconfirmed, the operator provided additional **actual new E11
final v1.8 FAP** observations, verbatim:

```text
ESP32_OK vardı sonra ben AT Batım steres armed yazdı uzunca bir yazı kaydı ve brust end dedi sonra esp32 ready dedi
```

Interpretation limited to evidence:
- ESP32 peer's `ESP32_OK` text **was visibly observed in the
  Flipper UART RX display** during the session. The reported
  chronology places this displayed string **before** the user's
  specifically described last `AT` press; don't assert it was
  unambiguously that last command's reply.
- `AT` then produced `STRESS_ARMED`, a long stream of data,
  `BURST_END` and a return to periodic `ESP32_READY`,
  matching the checked
  `tests/esp32_s2_wrover_uart_stress_115200/esp32_s2_wrover_uart_stress_115200.ino`
  firmware behavior: only its exact `AT` parser arms the
  bounded one-shot stress burst; it also sends
  `ESP32_OK\r\nSTRESS_ARMED\r\n` on an accepted command.
- **E1 RX PASS**, **E2 peer-command reception/TX PASS**, **UART
  STOP/BACK PASS** on installed final E11 v1.8. **E3 observed
  response-string reception PASS in the same session** subject
  to the noted timing limitation; do not present a separately
  timestamp-correlated last-`AT` E3 result.
- The bounded ST2 behavior was visibly completed but there is
  no R/D/E counter log, duration instrumentation, buffer DROP
  proof or exact byte total for this new binary; hence the
  quantitative high-rate/loss-free ST2 gate stays OPEN.

This additional observation **supersedes the previous record's
'E3 exact string never observed' uncertainty**, not the
broader concern that the first test response selected FAIL
because it unexpectedly invoked the existing ST2 firmware.
No additional transmission, peer firmware flash, GPIO
rewire, data mutation or device image replacement was
requested by this follow-up. Avoid further `AT` triggers
until a deliberate separate performance test is designed.
Keep Draft PR #13, published Stable/main and v1.9 HOLD.
