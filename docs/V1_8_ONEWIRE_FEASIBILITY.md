# LabMate v1.8 — Optional 1-Wire DS18B20 Feasibility

**2026-10-13 | W1 decoder + SDK CI PASS, W2 inert ABI-link CI PASS, W2b HAL-free lease/STOP host CI PASS. Actual firmware-wide GPIO ownership remains BLOCKED; no sensor measured.**
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

## W2 continued source audit — GPIO/iButton cannot be assumed exclusive

An additional Momentum `dev` read-only source review found:

- [`furi_hal_resources.c`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/targets/f7/furi_hal/furi_hal_resources.c)
  maps **`gpio_ibutton` to PB14, header pin 17**; this is the
  same pin selected by Momentum's thermometer example.
- [`one_wire_host.c`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/lib/one_wire/one_wire_host.c)
  shows `onewire_host_start` directly sets the selected pin to
  **open-drain output** and `onewire_host_stop` restores
  **analog mode**. The reviewed host library does **not** itself
  acquire or hold a firmware-wide exclusive pin-owner token before
  these calls. Therefore its start/stop API **cannot be treated
  as collision detection**; simply choosing PB14 is not safe proof
  that other firmware functions are idle.
- [`furi_hal_ibutton.c`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/targets/f7/furi_hal/furi_hal_ibutton.c)
  also uses **TIM1** in its iButton-emulation HAL path, which
  overlaps a timer used by LabMate's PWM Studio. That is a separate
  reason to review internal/peripheral conflicts; a 1-Wire GPIO
  scratchpad read does not itself establish that any TIM1 session
  is free.

**Architecture decision:** no silent start on PB14 or PC0/PC1, no
assumption that a successful `onewire_host_alloc` means exclusive
ownership, no direct takeover during PWM/iButton/capture activity and
no call to the example's `power_enable_otg`. The pure decoder and
inert ABI proof may be tested in CI without accessing these
resources, but any actual GPIO driver remains **W2 BLOCKED until a
reviewed resource-policy and STOP/BACK lifecycle are available**.
This is a source review only, not an on-device contention test.

## W2b — fail-closed lease and STOP lifecycle model (HOST CI PASS)

Added `src/labmate_onewire_session.h/.c`, independent
`tests/test_onewire_session.c.inc`, guard
`scripts/check_v18_onewire_session.py`, and two strict C11 CI steps.
**These are pure models only**: no `onewire_host_*` calls, no GPIO,
no bus transaction, no actual external lease, no GUI or firmware
record. In particular, `LabMateOneWireArbiterAtomicLeaseSupported`
is **hypothetical mock input**, NOT an API Momentum currently offers.
Never set it to true from an assumption, app-local boolean, a
read-only PB14 pin inspection or a non-atomic "is it busy?" check.

**Deny-by-default prerequisites to enter modeled AwaitLease:**

- A future proven **atomic external PB14 owner/lease service**;
  unsupported and unknown external arbiter states are rejected.
- User-verified **3.3 V-compatible** electrical conditions.
  Unknown/unsafe voltage, automatic OTG activation and parasite
  power request are rejected.
- Only candidate PB14 pin (Momentum iButton port) is modeled;
  PC0/PC1 and other pins rejected to protect current instrument
  owners. **PB14 is not assumed safe just because the example
  selects it.**
- No active capture, GPIO Monitor, PWM Studio, iButton, **RFID**,
  expansion, or unknown other owner. Local flags only report local
  state; they cannot establish a global lock. The assumed
  externally supplied atomic lease is mandatory.

**Async states and STOP guarantees within the model:**

`IDLE → AWAIT_LEASE → READY → AWAIT_OPERATION → READY →
AWAIT_RELEASE → COMPLETED`. A STOP while awaiting a lease
**remains pending**; a late positive grant must proceed to
`AWAIT_RELEASE`, without starting sensor operations. A STOP
during an in-flight operation waits for its recorded completion
before release, and no new operation may begin. An error also
requires confirmed release before `FAILED`; STOP after
release resolves as `CANCELLED`. Generation tokens reject
stale releases/grants; restart and app exit are forbidden while
the model still awaits a lease, operation or release. Token
wraparound is rejected. `session_init` is **initialization-only**
and cannot be used to clear a live/blocked worker.

`labmate_onewire_session_can_exit` expresses **logical model
quiescence only** and is not proof that a real worker joined,
a pin changed to analog mode, any peripheral stopped, external
power is off, or another application released PB14.
This model is **not thread-safe** by itself; a future coordinator
must serialize events and synchronize UI snapshots.

The isolated tests exercise all reject reasons, modeled late
lease after STOP, in-flight STOP, error/release, normal
finish/restart, stale tokens and token exhaustion.

**W2b verified GitHub CI PASS:** [run 38467638118](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38467638118),
exact tested source SHA `606788115f6bfc00ac4ec4c3a170f9c6e8d5f4f1`.
The job logs explicitly reported:

- `1-Wire W2 HOST lease model: deny unknown, no auto power, late lease STOP, confirm release, stale events PASS`
- `1-Wire W2 mock model isolated and fail-closed: PASS (HOST ONLY)`
- The earlier W1 native CRC and conversion safety tests, Momentum SDK development FAP compilation and Windows installer mock also PASS.
- Development `labmate.fap` file SHA256 from job output: `f3ce6438280524692908212c0b3c8b4c9a830b7afc467b503aab667d2e7f12d2` (artifact `labmate`, ID `11849545949`, not a Stable release). The GitHub ZIP digest is a different file's digest.
- v1.7 publishing step SKIPPED by design. Earlier branch runs `38467507230`, `38467361244`, `38467314329` were cancelled/superseded by new pushes, not failed W2b native tests.

Despite this PASS, W2 real GPIO/resource ownership **remains BLOCKED** until an actual supported atomic owner protocol can be found and validated; no physical W3/W4 sensor test or runtime STOP timing may be inferred from simulation.

## W2c — additional Momentum owner audit, RFID collision, and integration freeze

**2026-10-14 source review (not device validation).** The following
Momentum `dev` files were inspected directly; these exact file
snapshots are the basis of the conclusion, rather than a generic
statement about every possible firmware version:

| Upstream source | Inspected content | File blob SHA |
| --- | --- | --- |
| [`furi_hal_gpio.h`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/targets/f7/furi_hal/furi_hal_gpio.h) | GPIO mode setup, interrupts, read/write; **no documented acquire/release by app owner** in reviewed interface | `9e78872bbc6d0bae806a87d22aae42ed02665bb1` |
| [`furi_hal_gpio.c`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/targets/f7/furi_hal/furi_hal_gpio.c) | `furi_hal_gpio_init_ex` enters short critical section to change register state; this is **not** a held owner lock across transactions | `0104dd8989083cc71b1ae496f248aa71240fcb46` |
| [`one_wire_host.c`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/lib/one_wire/one_wire_host.c) | `onewire_host_start` immediately reconfigures its passed pin open-drain; `stop` reconfigures analog; **no global GPIO lease call** in these functions | `62d325cf50c80d8d3c61bf2c4ac2d68e697e4fc3` |
| [`furi_hal_rfid.c`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/targets/f7/furi_hal/furi_hal_rfid.c) | LF RFID's `furi_hal_rfid_pins_field` uses `furi_hal_ibutton_pin_configure` and drives the shared PB14 iButton pin; RFID pin reset also resets PB14 | `34bb3a516002f322e83c87dece7384cbe30251d7` |
| [`loader.h`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/applications/services/loader/loader.h) | `loader_lock` is documented as **locking application start**; not a PB14/RFID/iButton resource arbiter | `da049eaad5529f0a621c1c6cc5764c61b86ce96d` |
| [`expansion.h`](https://github.com/Next-Flip/Momentum-Firmware/blob/dev/applications/services/expansion/expansion.h) | Expansion enable/disable describes supported **serial port** coordination, not ownership of PB14 | `1b0879b1ec4122a9fdd9b99c7a4f6e5d01a392bf` |

**Rejected shortcuts:** a loader lock cannot prove that
background firmware services will avoid PB14; checking a pin's
present mode, taking an app-private mutex, or disabling serial
expansion support also cannot provide a firmware-wide exclusive
atomic PB14 lease. A successful FAP ABI-link or simulated
`AtomicLeaseSupported` input likewise offers no hardware proof.
We have **not established** that every possible future firmware
fork lacks an arbiter; the statement is confined to reviewed
Momentum `dev` public APIs/sources and our available SDK.

**W2b tightened:** `LabMateOneWireEnvironment.rfid_active` is now
part of the **mock** resource denial model along with iButton,
PWM, capture, monitor and expansion. There is no official
global RFID-active read used in LabMate, so a local
`rfid_active=false` alone would be insufficient. An independent
external atomic PB14 lease remains a mandatory precondition.

**New W2c static CI freeze (PENDING):**
`scripts/check_v18_onewire_no_hardware.py` guards the ordinary
`src/*.c` LabMate build against unreviewed OneWire host
imports, PB14 configuration calls, GUI/menu routes or accidental
invocation of the pure decoder/session in production.
The existing standard FAP CI now runs this guard, together with
the updated W2b mock RFID denial tests. This is **source
non-integration evidence only**, not a device permission check.
Do not weaken/remove it without a new, externally verified
atomic owner protocol, reviewed STOP/BACK and electrical
acceptance gates.

**Current W2 decision:** actual DS18B20 driver GPIO acquisition
**BLOCKED**, even though W1, inert W2 ABI and prior W2b
HOST tests PASSED. Only offline designs/tests may progress.
No sensor, ESP32, iButton/RFID hardware, external power or pin
configurations were changed by this work.

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
| W2 | Verify exact development SDK host exports and choose a validated GPIO ownership/lifecycle design | **ABI proof PASS**; **W2b host CI PASS** (38467638118); W2c RFID denial + static no-hardware guard committed, CI pending; **real atomic GPIO owner BLOCKED** |
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

**Decision:** W1 host/SDK, inert W2 ABI-link, and previous W2b HAL-free mock host CI PASS. W2c upstream inspection additionally confirms RFID controls PB14 and the loader/serial expansion interfaces are not GPIO owner leases; W2c amended host tests and source no-hardware guard CI PENDING. The real hardware atomic GPIO arbiter is still unavailable/unverified; W2 integration is BLOCKED and W4 real-device measurements remain NOT TESTED. No real Flipper temperature reading can be called PASS yet.
