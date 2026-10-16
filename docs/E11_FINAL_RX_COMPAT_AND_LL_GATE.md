# E11 — Matched external CC1101 RX BUSY, direct LL audit and recovery boundary

**Branch:** `dev/v1.8-completion`; **Draft PR #13 remains unmerged**.  
**Pinned upstream Momentum:** `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Scope:** E11/native firmware source-only changes. No device flash,
no Flipper/SD/USB writes, no v1.8 Stable/main mutation or v1.9 transition.

## What is now truly status-bearing

The original `SubGhzDeviceInterconnect.start_async_rx` in
`lib/subghz/devices/types.h` is a **void function pointer** with
`SUBGHZ_RADIO_DEVICE_PLUGIN_API_VERSION 1`. Changing it to bool or
appending an unversioned callback would be binary incompatible for
existing third-party radio plugins.

[`patch_momentum_subghz_ext_rx_status_bridge.py`](../scripts/patch_momentum_subghz_ext_rx_status_bridge.py)
keeps that ABI/layout unchanged. The matched external CC1101 plugin
now calls its real `subghz_device_cc1101_ext_try_start_async_rx`
(TIM17+PB2+EXTI2 owner) and immediately sends an optional
`subghz_devices_report_async_rx_start_result(device,started)` to
the firmware service. The existing `subghz_devices_try_start_async_rx`
returns that truthful status to the Sub-GHz app, preventing a falsely
started worker/speaker on a matched official-radio BUSY result.

The reporting transaction verifies **pointer identity**, accepts only
the first result for the **current** start, and protects its shared
state with short `FURI_CRITICAL_ENTER/EXIT` scopes. The critical
section is NOT held while invoking plugin code. A nested or concurrent
second START is refused; a spurious report outside a pending attempt
or from the wrong device cannot attest to success.

**Compatibility and safety limitation:** A third-party plugin built
against the old v1 ABI that has not adopted this optional result
reporter cannot truthfully report BUSY. To preserve operation of
previously supported radios, the legacy fallback still invokes the
old void callback and logs **status UNVERIFIED**; its inferred boolean
return is *not* a confirmed native lease owner and must not be reported
as an E11 security PASS. An unmatched/copied radio calling itself
`cc1101_ext` but lacking the matched status reporter is explicitly
refused by the newer app, rather than pretending a confirmed
receiver; the original plugin implementation still needs a matched
update. This is deliberately **not** a blanket guarantee about any
unmodified third-party radio plugin.

The old `subghz_devices_start_async_rx` void API and
`SubGhzDeviceInterconnect` size, field order, plugin v1 version and
published entry-point signatures remain unchanged. The new optional
function is an additive SDK symbol. For truly universal status
reporting, a separately negotiated future plugin API/v2 would be
required. Do NOT retrofit an incompatible struct change into v1.8.

### Host evidence

[Genuine original device source + external plugin wrapper
#38945208905 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38945208905)
compiled/executed the real patched C function bodies. Tests confirm
official internal RX true/false, external CC1101 true/false, missing
report, wrong-device and stale report, second-report suppression,
nested attempt denial and the legacy third-party compatibility path.
A deterministic pthread overlap test then covered a genuinely
concurrent second receiver start and verified no overlapping dispatch.

The final host+direct LL audit candidate
[#38945742437 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38945742437)
also included all earlier original C/C++ E11 regression tests.
The most recent matching full no-flash Momentum firmware, ONE LabMate
FAP, JS GPIO, radio stack, MNTM-012 updater, API and option-byte-policy
gate is [#38945772528](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38945772528).
**Final conclusion verified SUCCESS.** This exact candidate includes
firmware-native radio plugin, updated SDK API, one LabMate FAP, JS GPIO,
full MNTM-012 updater checksums and E11 direct LL regression gate.

## Reserved direct EXTI and disjoint native DMA channel audit

[`check_v18_e11_direct_ll_boundary.py`](../scripts/check_v18_e11_direct_ll_boundary.py)
is a negative original-source guard on the pinned, staged firmware,
not a new LL hardware gate/veto:

- GPIO EXTI0..15 registration/removal stays in
  `targets/f7/furi_hal/furi_hal_gpio.c`, which now exposes reviewed
  exact callback compare-and-add/remove. Earlier full-source raw
  native callback inventory excludes only the reserved Momentum
  **system input** registration; system STOP/BACK must remain intact.
- The native system clock's direct LL EXTI18, RTC alarm's EXTI17
  and RFID comparator's EXTI20 are independent **internal peripheral
  interrupt lines**, not aliases of external GPIO EXTI0..15.
  Their original code is kept unchanged, with no artificial
  LabMate global lease blocking RTC/clock/alarm infrastructure.
- Direct TIM1/TIM2/TIM17 EnableCounter callsites in native PWM,
  PulseReader, DigitalSequence, Sub-GHz and external CC1101 are
  enumerated with their existing original-C owner gates.
  Other TIM aliases/modes are covered by their separate E11
  driver-specific source tests, not magically proven by this regex.
- Native SPI transport uses **DMA2 CH6/7**; native USART/LPUART
  use **DMA1 CH6/7** in the pinned source. These channels are
  distinct from tested E11 TIM2 users' DMA1 CH1/2 and
  RFID/IR/SignalReader/CC1101 DMA2 CH1..5. The direct LL guard
  fails if their pinned channel mapping changes without review.

[Full E11 LL audit gate #38945742437 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38945742437)
ran on the actual staged firmware; this is an **enumerated source
mapping** only, not real interrupt/timer coexistence timing evidence.
The guard fails closed if it encounters an unreviewed direct
EXTI enable/disable path, changed reserved system service source or
an altered native SPI/UART DMA mapping.

## Faults and recovery contract

The existing reviewed native drivers do **not** silently reclaim
resources after an opaque release fails, a timer clock disappears,
or the registered EXTI callback is replaced by a foreign owner.
They retain a **sticky fault** and disable repeated START/STOP
manipulation. Host fault injection across LabMate, NFC, RFID, Sub-GHz,
1-Wire, serial expansion, Wiegand, IMU and JS GPIO verifies relevant
no-foreign-register-write denial paths. This is deliberate
fail-closed policy rather than an automatic recovery algorithm.

**Safe exceptional recovery remains an open hardware/whole-system
question:** do not clear a sticky token, free IRQ context or reset
a peripheral merely because a UI screen was closed. Report the
resource as unavailable, stop the attempted workflow and use only
an operator-approved controlled restart with known firmware and
validated physical wiring. No automatic firmware flash or device
reboot was implemented by this stage.

## Explicit acceptance decision

**Software covered and host-verified:** matched native Flipper firmware
owners and their documented default/supported pins, exact callback
lifecycle, CC1101 official plugin RX status, current static LL
channel/EXTI inventory and single-package build (as proven by the matching completed CI).

**Still outside a universal COMPLETE claim:** unchanged third-party
v1 radio plugin void callbacks, nonstandard dynamic GPIO or radio
debug mirrors, unreviewed direct LL aliases or external apps, and
hardware concurrency/recovery acceptance (HW-09 to HW-19).

Do **not** mark firmware-global E11 or v1.6 completely closed, nor
start v1.9, solely from these software/build results. Physical tests
remain `DEFERRED / HARDWARE PENDING` by the existing equipment plan.
