# LabMate v1.8 — UART Terminal development plan

**Status:** UART work started on `dev/v1.8-uart-terminal`. No UART
instrument is implemented or device-tested yet. This branch was created
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
