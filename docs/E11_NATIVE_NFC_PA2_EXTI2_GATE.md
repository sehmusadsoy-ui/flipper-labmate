# E11 — Native NFC IRQ PA2 + EXTI2 ownership and BUSY lifecycle

**Pinned Momentum:** `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Branch:** `dev/v1.8-completion`, Draft PR #13, no merges or device flashing.  
**Status:** Original NFC IRQ C + firmware allocator **HOST PASS**.
Latest combined full matched Momentum/JS/ONE LabMate FAP/updater software CI
is a separate acceptance gate and MUST finish SUCCESS. Physical NFC,
independent EXTI producers and actual card operation **NOT TESTED**.

## Production source integration

[`scripts/patch_momentum_native_nfc_irq_exti_lease.py`](../scripts/patch_momentum_native_nfc_irq_exti_lease.py)
adds to pinned `furi_hal_nfc_irq.c` and `furi_hal_nfc.c`:

- One exact atomic **internal NFC/RFID_PULL PA2 + shared EXTI2** lease,
  using a new PA2 bit (29) and existing EXTI2 bit (8). Different
  physical pin PB2 competes for EXTI2, while PB14/EXTI14 is independent.
- Reuses the preexisting E11.1c nonasserting
  `furi_hal_gpio_try_add_int_callback` and E11 native
  `furi_hal_gpio_try_remove_int_callback`; refuses any old callback
  rather than overwriting it or asserting. Only a successfully
  registered NFC callback may configure PA2 interrupt mode.
- Private NFC IRQ callback checks its exact held owner. Denied START,
  stale callback, double STOP, missing/mismatched callback and failed
  opaque lease release are fail-closed; STOP must not disable another
  EXTI callback or reset a foreign PA2 pin.
- Adds `furi_hal_nfc_try_init_gpio_isr` with truthful boolean while
  retaining original `void furi_hal_nfc_init_gpio_isr` internal ABI.
- NFC boot initialization now propagates `FuriHalNfcErrorBusy` if
  PA2/EXTI2 cannot be acquired; native chip cleanup/release still runs.
- NFC low-power resume first claims **both native NFC TIM1+TIM17**
  (from the preceding E11 timer stage), then tries PA2+EXTI2. If the
  second claim fails, only the acquired NFC timers are deinitialized
  and the existing error-returning API returns BUSY, without stealing
  another service's GPIO callback.

## Actual native-C fault evidence

[CI #38916131290 — SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38916131290)
compiles/runs genuine original NFC IRQ C callback, START, STOP and the
actual firmware resource allocator (not a rewritten HAL simulator).
It checks denied claim, occupied prior EXTI2 callback, failed callback
registration, repeated START/STOP, normal registered callback dispatch,
mismatched callback, failed release, sticky refusal and exact
mask collision with external PB2 and JS EXTI2. This is not a complete
NFC RF or scheduler test.

For firmware-integrated software acceptance also require
[matched full MNTM-012/firmware/FAP/JS/updater CI #38916167413](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38916167413)
to finish SUCCESS; an earlier OneWire-only package
[#38915550293](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38915550293)
cannot substitute for the NFC-inclusive build.

## Deliberate limits and next owners

This exact owner does **not** globally intercept unrelated direct
GPIO/EXTI writes. NFC IRQ PA2 is an internal pin, whereas CC1101
internal G0 is **PA1**, iButton 1-Wire uses **PB14**, and PB2 is an
external connector pin that merely *shares* EXTI2.

Still OPEN: native serial expansion PB7/EXTI7, external CC1101
TIM17/configurable G0 EXTI callback replacement, native SignalReader
DMAMUX/EXTI, boot/input service callbacks, other native pin reset
utilities, legacy direct interrupt clients and every real-device
coexistence check (HW-12).

**Do not label firmware-global E11 complete.** No firmware flash,
Stable/main merge, PR finalization, replacement of known-working
v1.8 Stable or v1.9 until proper acceptance.
