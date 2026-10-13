# LabMate v1.8 — Optional 1-Wire DS18B20 Feasibility

**2026-10-13 | Isolated research / host-code gate only.**
Branch: `dev/v1.8-onewire-feasibility` based on development `main` (which already
includes the accepted UART work). **No physical 1-Wire sensor has been
connected, no real sensor reading has been performed, and no 1-Wire UI
or hardware driver is integrated into LabMate.** No new Stable release.

## Why this work is separate from I²C

I²C Explorer Draft [PR #8](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/8)
has verified **G2d simulated 128×64 GUI 5/5 operator device PASS**
and HAL-free scanner models, but real external-bus hardware integration
remains blocked by Momentum `furi_hal_i2c_acquire()`:
the external I²C lock can wait `FuriWaitForever`, and no public bounded
acquire API has been verified. **The 1-Wire branch does not merge PR #8,
reopen its I²C bus, or resolve G1.**

Roadmap [v1.8 Communication Tools](../ROADMAP.md) explicitly lists
1-Wire temperature sensor support **if feasible** after UART/I²C.
This branch investigates that option without forcing I²C hardware
activation or pretending that optional sensor hardware is available.

## Momentum source facts (not hardware validation)

Reviewed [Next-Flip/Momentum-Firmware](https://github.com/Next-Flip/Momentum-Firmware)
`dev` on 2026-10-13:

- [`lib/one_wire/one_wire_host.h`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/lib/one_wire/one_wire_host.h)
  provides `OneWireHost`, `onewire_host_start/stop`,
  `onewire_host_reset`, `onewire_host_write` and
  `onewire_host_read_bytes`.
- [`lib/one_wire/one_wire_host.c`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/lib/one_wire/one_wire_host.c)
  uses open-drain GPIO and microsecond timings and explicitly
  configures the pin. This interface **does not provide a complete
  cross-application GPIO ownership protocol**. A bounded presence
  check is visible in the source, but whole-session timing, callbacks
  and resource conflicts still need independent review.
- [`applications/examples/example_thermo/example_thermo.c`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/applications/examples/example_thermo/example_thermo.c)
  demonstrates DS18B20 ROM skip, conversion, scratchpad read,
  CRC-8 verification and worker cancellation. It defaults to
  `gpio_ibutton` and **automatically enables external OTG power**.
  LabMate must **not copy its automatic power-on behaviour**.
  Conversion may take up to 750 ms at 12-bit resolution; a GUI
  callback must never wait for sensor conversion.
- [`lib/one_wire/maxim_crc.h`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/lib/one_wire/maxim_crc.h)
  exposes Maxim CRC-8, and Momentum API symbol/header export records
  include the 1-Wire host library. **Exact development SDK API-link
  and compiled physical driver validation are still pending.**
- The firmware's own example does **not** establish that any sensor,
  module, cable, GPIO voltage or temperature reading in the operator's
  hardware has been checked. This must stay NOT TESTED.

## W1 pure decoder: current implementation

- `src/labmate_onewire_ds18b20.h/.c` decodes a **9-byte DS18B20
  scratchpad** with standard Dallas/Maxim CRC-8 (reflected 0x8C).
  It uses signed 16-bit sixteenths of a degree Celsius, masks
  undefined fractional bits for 9/10/11/12-bit resolution and
  bounds readings to the specified **-55°C to +125°C** domain.
  It converts to tenths Celsius with signed symmetric rounding.
- Bad CRC, invalid configuration, out-of-range and missing/short
  scratchpads are **separate errors**. On failure no stale temperature
  is returned. `conversion_confirmed=false` also blocks display,
  because **CRC alone cannot prove that a conversion completed**.
  Raw `+85°C` is tagged `power_on_candidate` and cannot alone be
  used to infer an error or successful conversion.
- `tests/test_onewire_ds18b20.c.inc` includes a datasheet-style known
  CRC scratchpad (`50 05 4B 46 7F FF 0C 10 1C`) plus synthetic
  25.0625°C and negative-temperature examples with precomputed CRC,
  corrupted bytes, bounds, 9–12-bit masking and rounding cases.
- `scripts/check_v18_onewire_codec.py` explicitly forbids
  HAL/power/GPIO/canvas/thread calls inside this pure codec and
  prevents premature menu/production UI activation.
- Dedicated test steps were added on this branch to the existing
  Momentum source CI and Windows installer mock workflow.
  **New branch CI is not yet confirmed PASS**; do not claim a
  device-test or CI result without checking its exact workflow/job.

The decoder is not a reader: there is **no bus reset, sensor address
selection, conversion command, power control, scratchpad transaction
or GPIO session here**. The source is compiled by the existing
`src/*.c` FAP glob but has no runtime entry or menu hookup.

## Safety and scope gates (all require separate evidence)

| Gate | Acceptance | Status |
| --- | --- | --- |
| W0 | Momentum source/example audit; isolate from I²C PR #8 and v1.7 Stable | Source review done |
| W1 | HAL-free CRC/temp codec with strict native host tests and SDK compile | Code committed; CI pending |
| W2 | Verify exact development SDK host exports and choose a validated GPIO ownership/lifecycle design | Pending |
| W3 | Read-only one-sensor demo (no automatic external power, no persistent GPIO owner), STOP/BACK/regression host + SDK tests | Pending |
| W4 | Operator verifies a **known safe, compatible** sensor and electrical conditions, then physical no-device + one-device runs | NOT TESTED |
| W5 | Acceptance and explicit review before optional integration; separate Stable decision | Pending |

**Electrical and resource restrictions:** 3.3 V-compatible verified
digital hardware only; no 5 V or unverified pull-ups, no unknown
external power wiring, no auto-OTG, no parasite-power assumption.
Do not use the ESP32-S2 UART stress sketch as a 1-Wire slave.
Do not drive GPIOs while another LabMate capture owner, PWM,
iButton app, I²C application or unrelated service owns them.
Choosing `gpio_ibutton` in upstream examples does not imply
exclusive ownership from an external app. Never forcibly seize
another app's GPIO, manipulate its mutex, or terminate a thread
holding hardware resources. Firmware USB installation and stored
Profiles/CSV history must remain untouched in these W0/W1 tests.

**Decision:** Continue W1 host/SDK testing only. W2/W4 are mandatory
before a real Flipper temperature reading can be called PASS.
