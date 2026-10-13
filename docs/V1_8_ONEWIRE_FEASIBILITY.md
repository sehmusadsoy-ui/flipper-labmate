# LabMate v1.8 — Optional 1-Wire DS18B20 Feasibility

**2026-10-13 | W1 host codec + Momentum SDK CI PASS; W2 inert SDK ABI-link CI PASS, but hardware GPIO ownership still OPEN. No sensor measured.**
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
  exposes Maxim CRC-8. Momentum
  [`targets/f7/api_symbols.csv`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/targets/f7/api_symbols.csv)
  marks the public 1-Wire host header, `maxim_crc8`,
  `onewire_host_alloc/free`, `start/stop`, `reset`, `write`
  and `read_bytes` **+ exported** for FAP apps (source review PASS).
  **Exact Momentum SDK ABI-link and compiled physical driver
  validation remain pending**, separate from the pure decoder.
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
- Strict C11 host tests and the model isolation guard were
  **independently confirmed PASS** from the exact
  [GitHub run 38466126162](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38466126162)
  job logs: `1-Wire DS18B20 HOST codec: CRC, signed range,
  resolution masks, conversion gate, rounding PASS` and
  `1-Wire DS18B20 pure codec isolation / unconfirmed-reading safety PASS`.
  The Momentum SDK production-development FAP build and Windows
  installer mock both concluded `success`, while the v1.7
  publication job was `skipped` as expected.
  **Exact CI source SHA:** `7aac37c889024f2e4a3a94f9faaa3c11caf843c9`.
  Its separately built `labmate.fap` has SHA256
  `f3ce6438280524692908212c0b3c8b4c9a830b7afc467b503aab667d2e7f12d2`
  according to the job log; artifact `labmate`, ID `11848003135`.
  This is an **unpublished development artifact**, not an installed
  or physical sensor-tested application.

The decoder is not a reader: there is **no bus reset, sensor address
selection, conversion command, power control, scratchpad transaction
or GPIO session here**. The source is compiled by the existing
`src/*.c` FAP glob but has no runtime entry or menu hookup.

## W2 partial — inert SDK ABI proof CI PASS, GPIO ownership still OPEN

A separate `tests/flipper_onewire_api_probe/` app builds
`labmate_onewireapiprobe.fap` as an inert proof of exported
Momentum 1-Wire symbols. Its app entry takes typed function addresses
so the dynamic imports must link, then exits immediately without
allocating/starting a host, reading or writing a 1-Wire pin, sending
temperature commands, enabling power, or touching another application's
GPIO. The isolated
`.github/workflows/v18-onewire-api-probe.yml` installs the Momentum
development SDK, compiles the proof, verifies a checksum and saves
an artifact. Its separate
[GitHub run 38466409736](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38466409736)
is now **independently confirmed PASS**: explicit no-hardware-call
guard PASS, Momentum SDK uFBT `LINK/FAP/APPCHK` PASS and artifact
upload PASS. **Exact source SHA:**
`84e65dbec774163aae6e3006a8f2f522a44c08e9`.
ABI artifact `labmate-onewire-abi-probe`, ID `11848518279`
(stored separately from production `labmate.fap`).
This compiled proof **must not** be installed as a thermometer.

This ABI step verifies signatures/linkage only, not safe pin ownership.
The later hardware driver still needs an explicit non-concurrent,
STOP/BACK-safe GPIO ownership design; a source-level example cannot
certify that user hardware has a DS18B20 or suitable voltage.

## Safety and scope gates (all require separate evidence)

| Gate | Acceptance | Status |
| --- | --- | --- |
| W0 | Momentum source/example audit; isolate from I²C PR #8 and v1.7 Stable | Source review done |
| W1 | HAL-free CRC/temp codec with strict native host tests and SDK compile | **CI PASS** (38466126162, source 7aac37c8); no physical readings |
| W2 | Verify exact development SDK host exports and choose a validated GPIO ownership/lifecycle design | **Source + inert ABI-link CI PASS** (38466409736, source 84e65dbe); GPIO ownership/STOP-BACK still OPEN |
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

**Decision:** W1 host/SDK gate is verified PASS and the W2 ABI-link subgate is PASS. Next research concerns exclusive GPIO/iButton ownership, lifecycle, 3.3 V and no automatic external power. The full W2 hardware resource gate and W4 real-device measurements remain NOT TESTED. No real Flipper temperature reading can be called PASS yet.
