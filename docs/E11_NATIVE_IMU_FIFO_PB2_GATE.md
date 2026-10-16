# E11 — Native JS IMU ICM42688P FIFO IRQ on PB2 / EXTI2

**Pinned original Momentum:** `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Scope:** only `dev/v1.8-completion` Draft PR #13; no firmware flash,
no SD/USB modifications, no Stable/main merge.

**Status:** Genuine original production ICM42688P FIFO IRQ C driver and
firmware lease allocator [#38933011284 HOST SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38933011284).
The IMU-inclusive full MNTM-012 firmware, one LabMate FAP, native
JS GPIO module and updater checksum/policy CI
[#38933103357](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38933103357)
has a separate conclusion to verify before software-build acceptance.
This host test is **not a physical IMU, FIFO timing or SPI PASS**.

## Confirmed pinned caller chain and actual pin

`applications/system/js_app/modules/js_vgm/imu.c` creates its native
ICM42688P instance with
`icm42688p_alloc(imu->icm42688p_device, &gpio_ext_pb2)`.
The old `ICM42688P.c` FIFO enable first changed chip FIFO registers
over SPI and GPIO mode and then blindly removed any existing EXTI
callback before registering its own. Its STOP similarly removed any
callback regardless of ownership.

**PB2 + EXTI2** is the same shared physical interrupt line already
cooperatively owned by NFC's internal **PA2/EXTI2**, external CC1101
RX **PB2/EXTI2/TIM17** and any other EXTI2 listener. Sensor SPI chip
select is separate **PC3**; a PB2 IRQ claim is not ownership of every
optional SPI, radio or PC3 function.

## Changes and fail-closed contracts

[`patch_momentum_native_imu_fifo_exti_lease.py`](../scripts/patch_momentum_native_imu_fifo_exti_lease.py)
modifies the real production C source, header and IMU worker:

- The new `icm42688_fifo_try_enable` returns bool while the old void
  entrypoint is retained for ABI. Only the pinned known PB2 IRQ pin
  is supported. Unsupported arbitrary IRQ-pin choices are denied.
- Firmware-wide `FURI_HAL_LEASE_IRQ_PB2` atomically claims both PB2
  and EXTI2 **before FIFO SPI register writes, GPIO mode changes
  or callback manipulation**. E11's original native GPIO
  compare-and-register refuses an occupied EXTI2 slot without
  overwriting or asserting. Denied START does not perform the
  FIFO GPIO/SPI side effects.
- The callback wrapper checks live exact ownership and sticky fault
  before passing a valid interrupt to the worker context.
  STOP compare-and-removes only its exact callback and sensor owner
  before changing IRQ GPIO mode or turning off FIFO over SPI. Denied
  STOP cannot alter another service's EXTI callback. A failed lease
  release or unexpected callback replacement makes the owner sticky.
- The production JS IMU worker now calls the bool start rather than
  assuming the old void method succeeded. An explicit semaphore
  handshake lets `imu_start` report failed setup and end its
  worker thread rather than waiting indefinitely for FIFO events
  or presenting a sensor as active without interrupts. The handshake
  wait is bounded and its completion/failure paths join the worker
  and release thread resources.

## Automated evidence and limits

Genuine patched native ICM42688 FIFO C (callback wrapper, START, STOP,
allocation/free) is compiled/executed with a fault-injection fixture,
and the **actual firmware allocator** is compiled/executed for
cross-owner collisions.

[Host CI #38933011284 SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38933011284)
covers native NFC/external CC1101 shared EXTI2 and V2 external radio TX
mask, absent claim, stale occupied callback, no GPIO/SPI writes
on denial, normal START/STOP, duplicate STOP, callback mismatch,
failed release, denied different pin and stale callback guard.
The IMU worker handshake is source-audited; its actual scheduling,
sensor calibration, FIFO packet parsing, SPI transport and
physical retry/recovery are **not claimed runtime-tested**.

Other E11 issues still OPEN: external radio plugin v1 `void` RX
status propagation, alternative IMU GPIO choices, GPIO PC3/SPI
interaction and native system-input compatibility, exceptional
sticky-fault recovery, protocol-level on-device acceptance.
Hardware test **HW-17 is deferred**.

**Never claim firmware-global E11 COMPLETE, physical PASS or v1.9
from a host-C test or successful firmware build alone.**
