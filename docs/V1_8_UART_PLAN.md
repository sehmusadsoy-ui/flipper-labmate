# LabMate v1.8 — UART Terminal development plan

**Status:** UART RX/TX **development candidate implemented** and SDK 87.1
CI PASS. **First two real Flipper local-loopback checkpoints U1–U8:
8/8 PASS** (operator-reported, 2026-10-13). Basic baud variants,
UART STOP/BACK cleanup and selected legacy-tool/data regression passed.
**External 3.3 V peer interoperability, BUSY/overflow behavior,
independent baud calibration and UART endurance remain PENDING.** This branch was created
from the already merged, CI-passing Counter STOP/RESUME baseline
(`main`, PR #6). No Stable release, installer or tag is changed.

## Goal

A practical Flipper Zero UART serial console for verified,
**3.3 V-compatible** MCU peripherals. The first useful milestone must
receive and transmit real external serial data on an actual device.
Opening a static terminal-looking screen is not feature completion.

## SDK / pin compatibility gate (before writing HAL calls)

1. Check **Momentum SDK API 87.1** serial HAL declarations and exposed
   hardware serial IDs, pins, GPIO alternate functions and firmware
   serial resource ownership.
2. Verify the appropriate external UART pins from authoritative Flipper
   hardware pinout for the firmware and physical GPIO numbering. Do not
   guess pin numbers or drive PA7/PB3 as serial pins.
3. Use a documented serial acquire/init/start/rx-callback/tx/end/release
   lifecycle, respecting existing console / debug / expansion ownership.
   A failed acquire must show a clear BUSY/ERROR state and must not
   release a resource belonging to another app.
4. Explicitly check conflict handling with LabMate TIM1 PWM,
   TIM2 Counter/Frequency and EXTI Pulse/Button ownership.
5. Ensure RX ISR only copies bounded bytes into a ring buffer; it must
   never draw on the GUI or perform SD I/O.

## v1.8 UART v1 scope (ordered)

- **RX-first:** fixed-capacity ring buffer, byte/drop counters, nonblocking
  UI polling under the existing app-thread/mutex model; input overflow
  flagged rather than silently corrupting memory.
- **Terminal:** 128x64 legible text/HEX presentation with selectable
  baud and stream pause (PAUSE freezes display only; capture state is
  explicit). Keep input line endings visible, clear screen action explicit.
- **TX:** explicit send action with bounded buffer, selectable CR/LF and
  no unintentional transmissions when navigating screens.
- **Baud and error:** choose only supported firmware baud settings.
  Actual baud generation, framing/error handling and RX/TX throughput
  must be validated with a real second device.
- **Cleanup:** close the UART session on BACK, on app exit, on any
  resource or initialization failure and on change of active baud.
- **Navigation:** append new tool ID/screen enum values without
  renumbering original 11 tools, profile IDs or saved logger formats.
  Add a dedicated `labmate_uart_*` owner instead of expanding the
  previously refactored `labmate.c` monolith.

## Test plan and acceptance

- [ ] SDK 87.1 compiles: serial HAL symbols and pins verified against
      the exact build SDK; existing native/static checks still PASS
- [ ] All prior 11 tools work; Profiles S1 and older CSV history retained
- [ ] UART 9600 8N1 incoming message displayed on a real Flipper
- [ ] UART 115200 8N1 received without GUI corruption or lockups
- [ ] App TX line arrives intact at the external 3.3 V UART endpoint
- [ ] RX overflow, timeout and repeated start/stop are bounded and visible
- [ ] BACK exits UART and leaves serial pins/resource in a safe state
- [ ] Serial resource conflict denies access cleanly, without corrupting
      generator, Counter, Pulse, Button or microSD state
- [ ] Real-device smoke/regression screenshots and measured results
      reviewed **before** merging the UART PR or claiming completion

**Not this milestone:** automatic protocol decoding, UART bridge to PC,
full-screen text editor, arbitrary voltage level adaptation, USB serial
replacement, I²C or 1-Wire (these are separate scoped features).

Caution: Flipper GPIO is 3.3 V only. Never connect UART to 5 V, RS-232
signal levels, unknown voltage sources, motor controllers or mains.

## Implemented in this candidate (not yet verified on physical Flipper)

- USART 8N1 at `9600`, `38400`, or `115200` baud (select while STOP).
- Flipper GPIO header **pin 13 TX, pin 14 RX** (USART), as specified in
  [Flipper expansion protocol hardware pinout](https://developer.flipper.net/flipperzero/doxygen/expansion_protocol.html).
  Firmware Expansion must not be controlling a connected module. The
  app checks `expansion_is_connected` and fails with BUSY without
  disconnecting a currently connected expansion module; otherwise calls
  `expansion_disable` before UART acquisition and re-enables the
  service on cleanup.
- ISR callback enqueues single RX bytes in a bounded 256-byte
  `FuriStreamBuffer`; the main loop drains at most 256 bytes per tick,
  renders printable ASCII, converts nonprintables to periods, and shows
  capped RX/drop/error counters. No storage/GUI/mutex calls inside ISR.
- UART starts STOP. OK toggles UART RUN/STOP; UP clears the visible
  buffer; LEFT/RIGHT select baud when STOP; DOWN enters TX editor when
  RUN; BACK leaves and releases USART.
- TX editor: up to 12 editable uppercase/digit/punctuation characters;
  UP/DOWN cycle character, LEFT/RIGHT change position, OK explicitly
  queues sending text with CRLF, BACK returns to RX.
  TX executes on app thread after releasing GUI mutex, and waits for
  completion before any subsequent STOP/deinit request.
- Separate `labmate_uart.c/.h`, `labmate_uart_text.c/.h`,
  `labmate_uart_ui.c`, `labmate_input_uart.c`. Main coordinator
  remains under 200 lines, legacy tool IDs and saved profile format intact.

## Real Flipper local-loopback test suite — U1–U8 complete

**Result: 8/8 user-reported PASS.** All tests were on the previously
installed test candidate; code commit and SHA256 remain those documented
under checkpoint A. These results were supplied by the device operator,
not independently instrumented measurements.

### Checkpoint B — U5–U8: 4/4 PASS (operator report, 2026-10-13)

- **U5 PASS:** 9600 and 38400 baud selected while stopped; AT local
  loopback observed after RUN/TX SEND at each.
- **U6 PASS:** repeated UART RUN/STOP and BACK/re-entry operated
  without freeze or unexpected BUSY; UART entered STOP.
- **U7 PASS:** PWM Studio, Event Counter, Frequency Meter, Profiles S1
  and existing Log History remained functional following UART use.
- **U8 PASS:** loopback removed with UART stopped, LabMate app exited
  and relaunched; no reported freeze or lost settings/history.

U5–U8 do not demonstrate an external serial peer, electrical timing
accuracy, UART error/overflow warning under stress, or a real resource
conflict with another UART owner. Those are separate remaining
acceptance gates.

## First real Flipper test suite (in progress)

### Checkpoint A — U1–U4: 4/4 PASS (operator report, 2026-10-13)

The operator completed the first on-device checks using the exact
development candidate from [CI run 38305108729](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38305108729),
code commit `e5708831573d16140e0c71387d78ef4875b7b0bf`,
FAP SHA256
`466115746C4420903D21CE3CABA6A0532C799F1117CAC3406D9FF90F015A56BE`.

- U1 **PASS:** COMM menu → UART Terminal accessible.
- U2 **PASS:** initial STOP state and default 115200 baud.
- U3 **PASS:** OK RUN followed by DOWN enters TX editor.
- U4 **PASS:** SEND `AT` then BACK into RX view displays `AT`
  on Flipper TX 13 → RX 14 local loopback.

These PASS reports established the initial 115200-baud local loopback.
Checkpoint B subsequently passed U5–U8. External two-way UART,
electrical/timing validation and BUSY/overflow/error behavior remain
unverified and mandatory before merging PR #7.


**Preparation:** Stop PWM and fully exit LabMate before rewiring.
Remove other UART/expansion attachments. The simplest first exercise is
a short, directly wired **Flipper pin 13 TX → Flipper pin 14 RX**
self-loopback with a verified 3.3 V jumper, no external power supply.
Never connect 5 V/RS-232/unknown voltages to GPIO.

- [x] U1: `v1.8dev` shows COMM → UART Terminal; old 11 tools still reachable
- [x] U2: UART opens STOP, default 115200, pin label `TX13 RX14`
- [x] U3: OK RUN works and no BUSY/ERR, DOWN enters TX editor
- [x] U4: TX editor initial `AT`; press OK SEND; RX view shows
      `AT` loopback; repeated sends increase byte count without crash
- [x] U5: STOP, select 9600 with LEFT/RIGHT, RUN, send `AT` and
      confirm correct RX; verify second 38400 baud setting too
- [x] U6: STOP/START repeatedly and BACK leave UART without freezing;
      re-entry starts STOP; no background UART resource retained
- [x] U7: PA7 PWM Generator, PB3 Counter/Frequency, Profiles S1 and
      saved CSV History remain usable after UART screen
- [x] U8: Remove loopback only while UART STOP; exit and relaunch app;
      no freeze or corrupted state

**After self-loopback:** verify external 3.3 V UART peer RX and TX
at 9600 and 115200, overload/drop counters, error status and BUSY
when another service owns the serial port. An internal loopback alone
does **not** prove interoperability with a separate MCU.

Do not publish or merge as a UART-functional release until user-reported
device tests and, separately, MCU interoperability tests are reviewed.
