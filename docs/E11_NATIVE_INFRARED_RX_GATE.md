# E11.1t — Native infrared RX TIM2 lease (development only)

**Commit baseline:** pinned Momentum `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Development branch:** `dev/v1.8-completion` / Draft PR #13.  
**Release status:** source and CI review only; **NO FLASH**.  
**Firmware-global E11:** **PARTIAL**. RX integration is not infrared TX.

## Native RX source integration

Exact-source transformer
`scripts/patch_momentum_native_infrared_rx_lease.py`
changes `targets/f7/furi_hal/furi_hal_infrared.c`
and firmware resource-mask enumeration/allowlist. RX uses
**TIM2** and an internal infrared receive GPIO (not LabMate's
eight external GPIO). Its new canonical
`FURI_HAL_LEASE_NATIVE_IR_RX_TIM2` mask overlaps Counter,
PulseReader, DigitalSequence and other cooperating TIM2
holders but does not incorrectly claim an external GPIO.

RX `void` START acquires a lease before changing the infrared
receive GPIO alternate function, clock, timer, interrupt callback
or state. It rejects if the lease is held, if a noncooperating native
service already has the TIM2 clock enabled, or if this infrared
session holds a sticky unresolved release fault. A denied
`void` START cannot report a BUSY code to the unmodified
`infrared_worker_rx_start` interface; the worker thread may
remain active but receive no pulses. Timeout configuration and STOP
are made hardware-safe and no-op on denied START.

While active, RX IRQ and timeout modifications require a retained
lease, running RX state and an enabled TIM2 clock. On unexpected
clock loss, it becomes sticky and refuses to modify IRQ/timer
registers or release potentially stale resources. On owned STOP,
its bus/IRQ are disabled before releasing the exact claim.
Failed resource release preserves the opaque handle and forbids
a new START. The firmware lease table is atomic **only across
cooperating services**.

## Actual host and firmware evidence

[Exact production RX C + actual firmware resource allocator
CI #38891712004](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38891712004)
**SUCCESS** on source `80d2a689f8ae4c1dc3eab3f3901e3c90812144f1`.
The instrumented host C test executes true pinned RX
START/STOP/timeout/ISR C and real firmware resource lease C,
including denied first claim with **zero hardware writes**,
already-enabled native TIM2, faulting preflight lease release,
normal START/IRQ/timeout/STOP, idempotent denied STOP,
failure to release after STOP, unexpected native clock loss,
TIM2 collision with Counter/PulseReader/DigitalSequence and
unrelated TIM1 coexistence. Strict `-Werror -pedantic`.

[Full matched Momentum firmware + LabMate FAP + JS plugin +
updater CI #38891777756](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38891777756)
was initiated against new RX source `15042024678e9432149f214f61e9008dfe644a10`.
**Only a completed SUCCESS workflow permits a full-build PASS
claim**; record exact hashes only from that job's logs.

## High-priority work NOT finished

**Native infrared TX remains UNMIGRATED.** The pinned native
`furi_hal_infrared_async_tx_start` routine uses **TIM1**, DMA2
channels 1/2 and sometimes the external **PA7** pin. It
allocates buffers/semaphore before turning on TIM1 and
registers DMA ISRs, and its public START returns `void`.
The infrared worker may enter STOP or WAIT and block on a
semaphore if a naive firmware lease check simply skips START.
A correct TX integration needs:

1. Canonical atomic TIM1+DMA2 channel 1/2 claim, adding
   external PA7 when that is the selected output;
2. an explicit BUSY-aware native worker START and controlled
   no-start cleanup to prevent STOP/WAIT hangs;
3. DMA buffer/semaphore allocation failure rollback, ISR
   completion ownership and timer/IRQ teardown with correct
   opaque lease release, plus PA7 output detection ownership;
4. strict real patched C negative-path tests and paired
   full firmware/FAP/updater CI.

**Other global risks:** native RFID/Sub-GHz direct TIM1/TIM2,
NFC/infrared/other GPIO interrupt aliases and direct
register bypasses still exist. RX-only PASS does not close
firmware-global v1.6 resource management.

No user device was connected, flashed or written. Equipment
dependent device/physical tests remain
**DEFERRED / HARDWARE PENDING** by prior user decision.
Published `main`/v1.8 Stable stay unchanged.
