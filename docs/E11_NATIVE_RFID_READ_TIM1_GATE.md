# E11.1w — Native RFID read TIM1 cooperative owner

**Branch:** `dev/v1.8-completion` / Draft PR #13.  
**Base:** pinned Momentum `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Status:** native **read carrier TIM1 only**. Firmware-global E11 OPEN.
No Stable/main/device changes, and **no flash permission**.

## Implemented

Exact pinned-source script `scripts/patch_momentum_native_rfid_read_tim1_lease.py`
adds an explicit `FuriHalLeaseTim1` alias for native RFID carrier
read and whitelists it in the existing firmware resource allocator.
It patches `furi_hal_rfid_tim_read_start` by retaining the legacy
void wrapper and exposing a bool
`furi_hal_rfid_tim_read_try_start(float, float)`.
The owner claim is taken **before** TIM1 bus enable, read GPIO
configuration, timer registers or outputs. A foreign enabled TIM1,
lease BUSY, and sticky previous failure all reject without touching
hardware.

Active `read_continue`, `read_pause`, `set_read_period` and
`set_read_pulse` require the currently held lease and an enabled
TIM1 bus. STOP requires the same owner; a denied START followed by
STOP never shuts off another firmware service's TIM1. Failed
release and unexpected loss of the TIM1 bus retain an opaque,
nonreusable faulting session claim. Current GPIO reset paths
elsewhere in RFID HAL are **not** fully migrated by this stage.

## Evidence and boundaries

[**Native RFID READ original C and real firmware allocator host
CI #38902785963 — SUCCESS**](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38902785963).
The strict host C test compiles and runs the actual patched
carrier read START, continue, pause, retune and STOP, including
legacy BUSY with zero GPIO/TIM writes, repeated start, normal
release, failed preflight/STOP release and unexpected timer loss.
The actual firmware resource allocator rejects overlap with
PWM, iButton, NFC and infrared TX TIM1. This is **not** device
or other RFID mode validation.

[**Full matched Momentum firmware + single FAP + JS/updater
candidate CI #38903026814**](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38903026814).
This newer paired CI includes the updated
`check_v18_native_legacy_tim2_contract.py` safety audit:
only the exact reviewed RFID read-owner signature is allowed
while its still-unmigrated TIM2 read-capture, DMA-emulation,
TIM1+TIM2 field detect and native Sub-GHz paths must remain
unmodified. Check the workflow's final conclusion before
asserting full build PASS or recording binary checksums.

**Explicit remaining RFID-native modes:** read capture TIM2 +
capture ISR, TIM2 DMA emulation DMA2 CH1/CH2 and IRQ, and
field detection using **both TIM1 and TIM2 plus DMA2 CH1/CH2**.
Each requires a proper atomic full resource owner and status
propagation into existing protocol call sites, with GPIO,
timers, ISR and DMA acquired together before any state
mutation. Neither the read-only lease nor CI compile proves
native RFID/sub-GHz coexistence or device RF safety.
See `docs/E11_NATIVE_RFID_OWNER_PLAN.md`.

Other native IRQ/EXTI and GPIO bypasses remain open.
Hardware-dependent acceptance is **DEFERRED / HARDWARE PENDING**.
Never promote firmware-global E11 or v1.6 resource safety to
COMPLETE on this stage alone.
