# E11.1y — Native RFID TIM2 capture owner (host verified)

**Development branch:** `dev/v1.8-completion`, Draft PR #13.  
**Pinned Momentum:** `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Scope:** RFID comparator **read-capture TIM2 only**. No release,
firmware flash, device installation or Stable/main change.

## Exact changes

- `scripts/patch_momentum_native_rfid_capture_tim2_lease.py`
  refuses any unpinned source or unexpectedly modified previous native stages.
  The script takes an atomic `FuriHalLeaseTim2` claim before capture
  callback/context, timer clock, IRQ or comparator changes.
- Preserves the old void HAL ABI and adds the status-bearing
  `furi_hal_rfid_tim_read_capture_try_start(callback, context)`.
  A cooperative BUSY/legacy already-enabled TIM2 returns false with
  **zero capture hardware writes**. Failed preflight release stays sticky.
- The native original ISR checks the retained handle and timer clock
  before reading/clearing capture flags or invoking the callback.
  STOP after a rejected START is a no-op; owned STOP unwinds
  comparator, IRQ and timer and releases the exact original handle.
  Repeated STOP and missing clock fail closed. Failed final lease
  release forbids re-entry until a controlled firmware recovery.
- The actual pinned firmware allocator recognizes the capture TIM2
  alias. It conflicts with infrared RX and LabMate Counter on TIM2.
  It does **not** reserve external PB3 or PA7: this is an internal
  RFID comparator input, not an external connector capture.

## Evidence

[Original native RFID capture C + real firmware lease allocator host
CI #38904967453 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38904967453).

That CI staged the real pinned native production source, compiled the
capture ISR/START/STOP functions with strict host compiler warnings,
executed denied/no-write, old-clock-BUSY, failed release, real ISR,
normal STOP/re-entry, double STOP and lost-clock cases, and then
executed the actual firmware C resource mask allocator. These are
**host tests**, not device or RF signal validation.

The new full updater workflow must also apply this exact native stage
after the TIM1 read stage, run this actual C gate, pass the strict
remaining-mode safety audit and build one matching firmware, FAP,
native JS GPIO and MNTM-012 package with APPCHK/comparison. Its final
status is a **separate CI gate**; never infer PASS from host success.

## Explicit unfinished paths

1. Existing higher-level RFID consumers still call the *void* capture
   START API. The new bool variant is available but its BUSY handling
   is **not yet routed through all real protocol/app call sites**.
   A rejected hardware start must not leave callers awaiting data.
2. RFID TIM2+DMA2 emulation and TIM1+TIM2+DMA2 field detection
   remain uncoordinated; their DMA/ISR and GPIO lifecycles need
   atomic composite claims and real production C fault testing.
3. Comparator/EXTI-line-20 ownership and native RFID internal GPIO
   utility paths are not fully covered by the new TIM2 lease.
   Native Sub-GHz TIM2/DMA2 and other IRQ owners remain open.
4. Firmware-wide concurrency requires all participating HAL clients
   to honor the lease. Legacy register-level bypasses remain.
   Hardware acceptance is **DEFERRED / HARDWARE PENDING**.

**No firmware-wide E11 PASS, no v1.6 resource COMPLETE, no device
flash and no v1.9 start are authorized by this host gate.**
