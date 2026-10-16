# E11 — Native LFRFID worker BUSY propagation gate

**Status: OPEN / PINNED SOURCE AUDIT ONLY.** This is not an
implementation, compilation or physical PASS. Scoped to Momentum
`d3f89dfe2ef6b01839201598e9be1590cba80322`,
`lib/lfrfid/lfrfid_worker_modes.c` and `lib/lfrfid/lfrfid_raw_worker.c`.

## Why the HAL stage alone is insufficient

RFID READ TIM1 and comparator capture TIM2 now expose bool TRY_START
HAL APIs, but the original higher-level LFRFID read worker still calls
both legacy **void** entrypoints. If either resource is BUSY, the
underlying driver now fails closed while the worker can still announce
`LFRFIDWorkerReadStartASK/PSK`, initialize decoder queues, enter a
capture/timeout loop and later reset RFID GPIO pins it never owned.

This is a functional failure even when native HAL successfully avoids
foreign timer/IRQ writes. **Do not promote E11 from partial on the
strength of the HAL host tests.**

## Exact pinned upper caller inventory

1. `lib/lfrfid/lfrfid_worker_modes.c`,
   `lfrfid_worker_read_internal`: calls
   `furi_hal_rfid_tim_read_start(125000,0.5)` or `(62500,0.25)`
   before the stabilization interval and read-start callback, then
   `furi_hal_rfid_tim_read_capture_start(...)` and a buffer/timeout
   loop. Its unconditional normal cleanup includes
   `furi_hal_rfid_tim_read_capture_stop`,
   `furi_hal_rfid_tim_read_stop` and `furi_hal_rfid_pins_reset`.
2. `lfrfid_worker_mode_read_process` currently retries a read on
   `LFRFIDWorkerReadTimeout`, including ASK/PSK cycling. A newly
   surfaced BUSY must not be folded into the timeout branch and
   retried indefinitely: preserve stop/exit semantics and provide a
   truthful status to the caller.
3. `lib/lfrfid/lfrfid_raw_worker.c`,
   `lfrfid_raw_read_worker_thread`: opens/writes the capture file
   header **before** calling void carrier START; then stabilizes,
   invokes void capture START and enters a buffer-write loop.
   A BUSY can otherwise produce an empty/false-looking recording
   and a live loop with no incoming captures. Cleanup currently
   contains unconditional RFID STOP, and a file error waits for STOP.
4. The same raw worker uses legacy
   `furi_hal_rfid_tim_emulate_dma_start` in emulation. DMA ownership
   is **not migrated** by the READ/CAPTURE changes; do not route it
   through an unrelated partial timer-only workaround.

## Production migration acceptance

- Replace relevant READ/CAPTURE void starts with the exact
  `furi_hal_rfid_tim_read_try_start` and
  `furi_hal_rfid_tim_read_capture_try_start`. Claim the carrier
  first and capture second; on denied capture, release the **owned**
  carrier and do not run decoder/capture threads, callback START, or
  reset a foreign GPIO. A denial of carrier must have no subsequent
  capture attempt.
- Surface BUSY distinct from timeout, data absence and file I/O
  errors, and avoid automatic retry/spinning until an owner releases.
  Preserve operator STOP/BACK responsiveness and all earlier worker
  state transitions.
- For raw capture, avoid writing a successful-looking data file
  merely because the card/timer is BUSY. Keep SD/user file
  handling transactional, and do not add an automatic erase of
  existing recordings.
- Regress original LFRFID worker **C code**, not only its source
  strings, with mocked genuine HAL bool TRY_START: denied carrier,
  denied capture after successful carrier, normal read, recording
  errors, STOP during transitions, repeated restarts and GPIO
  pin-reset ownership. Assert denied sessions perform **zero**
  foreign timer/IRQ/GPIO mutations and do not wedge a thread.
- Then run the full pinned Momentum + single LabMate FAP + JS
  plugin + MNTM-012 matched updater/APPCHK comparator gate.
  Physical tests remain separately DEFERRED / HARDWARE PENDING.

**Project boundary:** No firmware install, no main/Stable update, no
v1.9 and no v1.6 E11 resource COMPLETE without closing the native
software BUSY/ownership paths and recording actual-C + full CI evidence.
