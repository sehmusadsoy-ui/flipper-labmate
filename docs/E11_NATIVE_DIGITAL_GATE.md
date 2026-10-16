# LabMate v1.8 E11.1q — Native DigitalSequence TIM2/DMA Ownership

**Development branch:** `dev/v1.8-completion` / Draft PR #13.  
**Baseline:** pinned Momentum `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Release:** **NOT APPROVED. NO DEVICE FLASH, USB/SD WRITE OR MAIN/STABLE MERGE.**  
**Native firmware-wide E11:** **OPEN / PARTIAL**.

## Software integrated

The exact-source, fail-closed patch
`scripts/patch_momentum_native_digital_sequence_lease.py` adds
`lib/digital_signal/digital_sequence.c` as a cooperating lease client.
Its all-or-nothing claim covers TIM2 plus DMA1 channels 1 and 2;
for the eight LabMate external connector pins the composite also owns
the matching physical GPIO pin. Nonconnector/internal GPIOs receive only
the TIM2/DMA core claim; **their individual GPIO configurations are not
claimed**.

The claim precedes every output-pin initialization, DMA and timer write.
A failed claim does not configure GPIO and does not start transmission.
A legacy native owner with an already-enabled TIM2 clock or DMA channel
is refused after the claim, before peripheral writes. Failed release
retains the opaque handle and blocks reuse. The STOP path releases after
the actual timer/DMA teardown. Unexpected loss of the clock is a sticky
fault: no other owner's timer is disabled. Optional
`DIGITAL_SIGNAL_DEBUG_OUTPUT_PIN` is deliberately refused because
an extra output pin cannot be atomically claimed by the present mask.

The native public `digital_sequence_transmit` remains **void**:
BUSY is logged but cannot be returned to callers through the existing
API. This is a usability limitation to address before any claim that
all native feature flows are safely migrated.

## What was actually tested

- The genuine patched firmware resource lease C source executes under
  host tests in `tests/test_v18_native_digital_sequence_lease.py`.
  Verified: 8 GPIO aliases, TIM2 exclusion with Counter/Pulse, DMA masks,
  I2C/Monitor collision, denied overlapping masks and stale/partial
  release behavior.
- Exact pinned native source patch preflight and postpatch firmware
  audit for TIM2 claims; all unreviewed native critical changes rejected.
- [Full MNTM-012 updater and matched firmware/FAP/JS CI #38833510893](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38833510893):
  **SUCCESS** for the predecessor before the optional-debug-pin guard.
  Real paired firmware/FAP compile and APPCHK, JS plugin and official
  MNTM-012 radio/option-byte comparison **PASS; CI only**.
- Final candidate with extra debug-pin fail-closed change:
  [CI #38833710815](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38833710815);
  check the completed workflow before claiming it PASS. No physical
  DigitalSequence, RFID, radio or cross-app measurements were run.

## E11 still OPEN — no unsafe shortcut

**Firmware-global ownership remains incomplete.** Native SubGHz
RX/TX, RFID read/emulation/field, NFC TIM1, iButton TIM1 and other
timers/GPIO/EXTI clients are not all under the shared contract. Their
state machines and many public APIs are `void`, or own ISR and DMA
configurations before/after timer enabling. Simply changing
`furi_hal_bus_enable` into a silent no-op, wrapping only LabMate or
relying on an uncoordinated `is_enabled` check can leave a service
half-started and damage radio/RFID functionality. A BUSY-capable
owner lifecycle, coordinated call sites, stop/recovery and independent
real-C regressions are needed for each service before E11.1 is closed.

Physical tests requiring owned fixtures remain documented as
**DEFERRED / HARDWARE PENDING** until material is available. They are
never silently counted PASS. Full firmware/FAP installation and Stable
release still require a separately reviewed recovery plan and explicit
device approval. Published v1.8 Stable and `main` remain unchanged.
