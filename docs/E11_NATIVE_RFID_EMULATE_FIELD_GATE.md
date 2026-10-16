# E11 — Native RFID DMA emulation and dual-timer field ownership

**Scope:** `dev/v1.8-completion` / Draft PR #13 only.  
**Exact Momentum base:** `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Status:** Production HAL and normal/RAW emulation worker source **staged**;
separate actual production-C/firmware allocator host gates **PASS**.
Newest full matched firmware/FAP/JS/updater build is a **separate pending gate**.
No physical RF/emulation measurement, device install, USB, SD or Stable change.

## Native RFID TIM2 + DMA2 emulation

- [`patch_momentum_native_rfid_emulate_dma_lease.py`](../scripts/patch_momentum_native_rfid_emulate_dma_lease.py)
  acquires one exact firmware resource mask for TIM2 **and BOTH DMA2 CH1/CH2**.
  It refuses an already claimed or legacy enabled timer/DMA channel before
  callback, internal RFID GPIO, IRQ, timer or DMA register changes.
- Adds `furi_hal_rfid_tim_emulate_dma_try_start` with a truthful bool
  BUSY; retains the original exported void HAL ABI. The native DMA
  ISR is guarded by held owner + expected clock/channel state, with
  sticky refusal if state disappears unexpectedly.
- Denied START followed by STOP, wrong mask release and double STOP
  never disable a foreign timer/DMA/IRQ. STOP tears down both owned DMA
  channels and timer first and releases the exact opaque handle after.
- Shared DMA2 occupancy excludes **native infrared TX TIM1+DMA2** even
  though the timer numbers differ; TIM2 also excludes Counter, RFID
  capture, infrared RX and native DigitalSequence where applicable.

**Evidence:** compiled/executed genuine patched RFID PWM/DMA C functions
and original firmware lease allocator with denied-zero-write, legacy
TIM2/DMA BUSY, native DMA ISR, normal START/STOP/reentry, failed
preflight/final release, lost clock and cross-service mask collisions:
[CI #38908647175 SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38908647175).
Earlier candidate harnesses #38908413073 and #38908552466 failed
because the extract included a later source segment and strict host
mock variables were initially unused. Corrections did not waive
warnings or remove negative-path assertions.

## Original LF RFID normal and RAW emulation callers

[`patch_momentum_native_lfrfid_emulate_busy.py`](../scripts/patch_momentum_native_lfrfid_emulate_busy.py)
updates genuine native `lib/lfrfid/lfrfid_worker_modes.c` and
`lib/lfrfid/lfrfid_raw_worker.c` call sites:

- Normal emulation attempts the bool HAL START; denied BUSY frees its
  pending buffer, stream and pulse glue immediately and **does not
  enter its DMA event loop or STOP a resource it never started**.
  Optional debug GPIO is set only after successful native START.
- RAW emulation verifies its file contents before attempting DMA;
  no DMA START is attempted after a malformed/failed file load or an
  operator STOP. It runs its receive loop and calls DMA STOP only if
  START actually succeeded.
- An appended `LFRFIDWorkerEmulateRawBusy` event is routed through the
  existing `LfRfidEventReadBusy` into the native RAW emulation scene.
  The popup explicitly shows `RFID BUSY` instead of incorrectly
  describing the condition as an SD read/write error.
- Original exported numeric enum entries and legacy void HAL symbols
  are preserved.

**Evidence:** compiled and executed both actual production-C helper
bodies for denied and successful START, with source-level lifecycle
guards and RAW UI event contract:
[CI #38908966404 SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38908966404).
The normal emulation view does not have a status callback; a denied
start exits its worker without fake RF output and logs BUSY, but a
visible normal-emulation BUSY indication is **not yet proven**.

## RFID field detection: TIM1 + TIM2 + DMA2

[`patch_momentum_native_rfid_field_owner.py`](../scripts/patch_momentum_native_rfid_field_owner.py)
is a separate pinned-Momentum stage:
- One **atomic** lease `TIM1|TIM2|DMA2_CH1|DMA2_CH2`, taken BEFORE
  field GPIO, either timer clock, DMA registers, IRQ or mode state.
  It also refuses already live foreign TIM1/TIM2/DMA channels before
  any field-related peripheral writes.
- Native bool `furi_hal_rfid_field_detect_try_start` is added while
  keeping original void START and STOP API symbols.
- Guarded field frequency check refuses stale/denied/no-clock claims
  and returns a zero reading, rather than reporting fabricated data.
  Owned STOP also disables TIM1 update interrupt before timer teardown,
  restores native field pins only when actually owned, then releases
  the exact mask. Failed releases and unexpected clock/DMA loss are
  sticky fail-closed.
- GitHub's indexed code search for the pinned firmware found the
  HAL definition, header and API entry but no independent native
  higher-level field START consumer. This is a scoped source finding,
  not a guarantee that dynamically linked clients cannot call it.

**Evidence:** original field setup/START/STOP/presence C and exact
firmware resource allocator executed in host fault tests:
[CI #38909551118 SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38909551118).
Test coverage includes legacy TIM1/TIM2/DMA1/2 denial with zero writes,
owned start/field reading/stop, double stop, failed release, clock loss
and conflicts with RFID read/capture/emulate, NFC, infrared and Counter.
No radio/cardiac/USB/SD or Flipper physical test claimed.

## Release and open boundaries

The latest complete E11 RFID changes must pass **one checksum-matched
Momentum firmware + native JS GPIO module + ONE LabMate FAP + MNTM-012
updater package**, exact native source CI, SDK APPCHK and official radio/
option-byte policy comparison. Full candidate:
[CI #38909551244](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38909551244).
Record its final conclusion and provenance before approval; no prior
package substitutes for it.

**Still OPEN:** native Sub-GHz RX/TX TIM2/DMA2 and dynamic mirror-GPIO,
native firmware EXTI/IRQ and internal iButton/NFC/RFID pin helpers,
native infrared unforeseen clock recovery, full concurrent workload/
worker scheduler testing and *every physical device/fixture gate*.
Firmware-wide v1.6/E11 safety remains **PARTIAL**.

**No main merge, Stable v1.8 asset replacement, custom firmware flash,
USB/SD changes, v1.9, physical PASS or automatic release.**
