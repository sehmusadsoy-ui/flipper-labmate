# E11 — Momentum Accessor Wiegand PA4/PA7 dual EXTI ownership

**Pinned Momentum:** `d3f89dfe2ef6b01839201598e9be1590cba80322`.  
**Development-only:** `dev/v1.8-completion`, Draft PR #13; original
native debug Accessor C++ app. No device flash or Stable/main merge.

**Status:** real original patched WIEGAND C++ ISR/START/STOP and
actual firmware resource-allocator fault tests
[#38931976451 SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38931976451).
Exact matched full Momentum firmware + ONE LabMate FAP + native JS +
MNTM-012 updater [#38932112748](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38932112748)
is a **separate build acceptance**; do not confuse a host C++ PASS
with full firmware build or physical compatibility.

## Why this native component matters

Pinned `applications/debug/accessor/helpers/wiegand.cpp` registers
two EXTI callbacks after directly configuring two GPIOs:
Wiegand D0 **PA4 (EXTI4)** and D1 **PA7 (EXTI7)**.
The old code registered via assertion-based callbacks, then blindly
removed both callbacks and set both pins to analog in STOP. This can
collide with LabMate's PA7 PWM generator, PA4 native PWM/OneWire
resource aliases, other EXTI4/EXTI7 clients and the supported
native Sub-GHz PA7 debug mirror.

[`patch_momentum_native_wiegand_exti_lease.py`](../scripts/patch_momentum_native_wiegand_exti_lease.py)
introduces a single exact mask
`PA4 | EXTI4 | PA7 | EXTI7`, preserving the existing
`WIEGAND::begin()` and `WIEGAND::end()` native ABI and adding
status-bearing `tryBegin()`.

The exact atomic lease must be obtained **before** both GPIO
modes/counters are touched. Existing E11 native GPIO callback
compare-and-register protects both D0 and D1 slots; an occupied D1
slot is rolled back by removing **only this instance's D0 handler**,
then the opaque lease. Never displace a foreign handler. On denied
START, no GPIO pin mode is changed; denied STOP leaves both pins
untouched. Normal STOP removes the expected callbacks and releases
exactly this Wiegand owner. A mismatched callback or invalid release
sets sticky fault; repeated START/STOP cannot reset someone else's
PA4/PA7 pins. The D0/D1 ISR checks that the owner is live and not in
fault state before consuming pulses.

The Accessor caller uses `tryBegin()` and logs the denied resource
instead of asserting; its legacy debug UI still needs a user-facing
BUSY display and separate end-to-end test. We make no claim that a
denied read produces valid card events.

## Actual original-C++ negative path evidence

Native C++ compiled from the pinned patched methods and genuine
firmware C allocator:
[#38931976451 SUCCESS](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38931976451).

Scenarios: claimed resource unavailable; other module already owning
either D0 or D1 EXTI; no GPIO writes on denial; partial first-callback
registration rollback; normal capture START/STOP/re-entry; duplicate
STOP and double-START; replaced callback; sticky invalid release;
exact cross-mask collisions with PWM PA7, EXTI4, EXTI7 and Sub-GHz
PA7 debug mirror. No hardware Wiegand card, electrical pulse-timing
or UI verification is implied.

## Remaining high-priority direct EXTI service

An **additional concrete unsafe GPIO callback replacement** remains
in pinned
`applications/system/js_app/modules/js_vgm/ICM42688P/ICM42688P.c`:
its IMU FIFO enable configures the sensor/GPIO then blindly removes
the existing IRQ handler before registering its own. Its stop also
removes handlers without ownership checks. The *real* JS IMU caller
in `applications/system/js_app/modules/js_vgm/imu.c` selects
`&gpio_ext_pb2`: it directly collides with external CC1101 PB2
and native NFC PA2 through **EXTI2**. A future stage must claim PB2
and EXTI2 before any FIFO/SPI/IRQ change, report FIFO BUSY all the
way to the IMU worker rather than pretending an active sensor, and
protect denied STOP plus stale interrupts. Other custom IRQ pin
assignments must explicitly fail closed.

Firmware-wide E11 is still **OPEN** while that IMU path, legacy
external plugin v1 void RX BUSY status, unknown pin/EXI service
owners, button system service compatibility and physical fixture
acceptance remain. Wiegand hardware check **HW-16** is deferred.
