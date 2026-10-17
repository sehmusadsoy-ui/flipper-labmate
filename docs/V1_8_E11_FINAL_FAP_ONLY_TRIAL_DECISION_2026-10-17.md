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
