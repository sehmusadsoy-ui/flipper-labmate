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

[Capture-only full matched Momentum firmware/FAP/JS/updater
CI #38904996042 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38904996042).
That workflow applied the exact stage after READ TIM1, compiled a matched
firmware + one LabMate FAP + JS plugin + MNTM-012 updater and checked
APPCHK and official package policy; no device/SD/USB writes. This
preceded native LFRFID worker and UI BUSY stages, which have **separate
later exact-source full build gates**.

## Explicit unfinished paths

1. The normal LFRFID READ and RAW recording consumers have now been
   migrated in later stages to bool STARTs with distinct BUSY, STOP
   cleanup and native scene warnings (see
   [READ/RAW worker gate](E11_NATIVE_RFID_CALLER_BUSY_GATE.md)).
   These host gates **do not** prove all native RFID clients, user
   UI scheduling or physical recording acceptance; latest combined
   full firmware candidate requires its own successful CI conclusion.
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
