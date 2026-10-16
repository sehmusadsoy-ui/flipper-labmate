# E11 — Native LF RFID READ / RAW BUSY lifecycle and scene gate

**Branch:** `dev/v1.8-completion` / Draft PR #13.  
**Pinned Momentum:** `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Status:** Normal read and RAW read BUSY handling **staged, host-tested**;
normal-read matched firmware CI also SUCCESS. The **latest combined RAW +
UI source** full firmware/FAP/JS/updater CI still requires separate
SUCCESS before full software acceptance. No physical acceptance or
Stable/main changes.

## Why these stages are necessary

TIM1 carrier and TIM2 capture have safe native resource claims, but
their old `void` callers continued as if a denied START succeeded.
That could falsely announce card reading, loop indefinitely or create
RAW files despite never starting capture.

## Normal READ worker — implemented stage

`scripts/patch_momentum_native_lfrfid_read_worker_busy.py` updates
pinned `lib/lfrfid/lfrfid_worker_modes.c`:

- Calls bool `furi_hal_rfid_tim_read_try_start` before announcing
  ASK/PSK start; on carrier BUSY it returns a distinct local
  `LFRFIDWorkerReadBusy` state without attempting capture.
- Preserves original stabilization but honors STOP during that delay.
- Starts capture with bool
  `furi_hal_rfid_tim_read_capture_try_start`. If capture is BUSY,
  releases only its previously acquired carrier, resets that carrier's
  owned pin path, frees the temporary stream/pair and returns BUSY.
- Both read/retry loops break on BUSY instead of forever cycling ASK/PSK.
  Read-start callbacks occur only after **both** native timers started.

**Evidence:** actual extracted production-C helper paths and audited
call-order host [#38906188632 SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38906188632).
Earlier normal-read full pinned firmware + one integrated FAP + JS/updater
[#38906213089 SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38906213089).
That build predates RAW recording and UI stage and **does not validate
their combined firmware**.

## RAW recording worker — implemented stage

`scripts/patch_momentum_native_lfrfid_raw_read_busy.py` changes the
actual `lib/lfrfid/lfrfid_raw_worker.c` and adds an ABI-compatible,
appended `LFRFIDWorkerReadRawBusy` enum result.

- Acquires both the carrier and capture using the bool HAL STARTs
  **before opening or writing the SD RAW recording file**.
- Retains the original 1500ms stabilization in 100ms STOP-aware units.
  STOP mid-stabilization and capture denied after carrier START unwind
  only the acquired carrier; a denied capture does not execute its STOP.
- On BUSY it reports RAW BUSY, frees temporary buffers and returns
  without falsely reporting a file error or modifying RAW file content.
  On a genuine file error it preserves the existing error callback.
- On a successfully acquired session, owned capture and carrier STOPs
  run even if file-open/header/writes fail.

**Evidence:** original C start helper execution + no-file-before-acquire
source audit [#38906641928 SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38906641928).
This is host evidence, not proof of SD filesystem behavior on device.

## Native RFID UI — implemented stage

`scripts/patch_momentum_native_lfrfid_busy_ui.py` modifies original
native LFRFID worker callback and firmware application scenes:

- Appends new `LFRFIDWorkerReadHardwareBusy` and
  `LfRfidEventReadBusy` events without renumbering old constants.
- Routes normal-read BUSY through worker callback to
  `lfrfid_scene_read.c`, which displays an `RFID BUSY` popup rather
  than a success or a silently endless read screen.
- Routes RAW BUSY through `lfrfid_scene_raw_read.c`. Its timer is
  stopped, an RFID BUSY warning appears, `state->error` becomes true
  and the existing successful ASK-to-PSK/done transition is blocked.

**Evidence:** [UI actual callback C and source lifecycle host
#38907128889 SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38907128889).
The source-specific UI stage gate is separate from whole firmware
acceptance.

An early combined CI attempted to demand the later UI callback from
the earlier normal-worker-only test, correctly failing that stage
`#38907128508`. The test was made stage-aware at commit
`053d632`; the final combined run must still complete successfully.
Do **not** promote pending/failing bundles to PASS.

## Still open — cannot close E11/v1.6

1. RFID TIM2 + DMA2 CH1/CH2 **emulation** remains direct/unleased.
   Field detection uses TIM1 + TIM2 + DMA2 in a composite sequence and
   is likewise unowned; these need atomic mode-specific claims and
   upstream BUSY/STOP handling.
2. Native Sub-GHz RX/TX, CC1101 G0 and optional debug-mirror pin
   arbitration remain uncoordinated with RFID and infrared TX DMA2.
3. Comparator/EXTI20 and native internal GPIO utilities are not all
   lease-enforced. Optional READ_DEBUG_GPIO mode still needs a separate
   EXTI/pin review. Global timer-claim preflights cannot protect
   clients that use registers directly.
4. Tests run **real extracted helper and callback production C**, and
   full CI compiles real firmware, but are not exhaustive native worker
   scheduling/fault-injection or end-to-end UI/SD behavior tests.
   On-device acceptance and any later custom firmware installation
   remain **DEFERRED / HARDWARE PENDING**, with backup/rollback and
   explicit operator approval required.

**Rules:** No firmware flashing, no USB/SD writes, no Stable/main merge,
no v1.9 and no firmware-global E11 COMPLETE from these partial stages.
