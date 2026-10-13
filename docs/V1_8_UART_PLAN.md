# LabMate v1.8 — UART Terminal development plan

**Current acceptance checkpoint (2026-10-13):** UART Terminal minimum
communication milestone was merged into development `main` as PR #7.
It remains **unpublished as a v1.8 Stable release**. The original Flipper self-loopback
U1–U8 **8/8 PASS**, external ESP32-S2 E1–E6 **6/6 PASS** at 9600/115200,
SR1-R1 baud retention **PASS**, fresh-session ERR recovery **PASS**, ST2
high-rate receive **PASS**, and standalone *real-HAL controlled USART-owner*
BUSY Probe **2/2 PASS** are **operator-reported**. SDK/host CI PASS.
The peer ST2 ended `R:41281 D:0 E:0`; **physical queue DROP (`D>0`)
has not been demonstrated**, despite host mock tests showing 64/64 expected
drops. SBR1 same-screen baud recovery is now **operator-reported functional PASS**
on the updated, SHA256-verified FAP (raw numeric R/D/E not supplied);
independent timing/calibration is unverified. BUSY Probe does not stand in for a simultaneous
unrelated third-party firmware service. PR #7 is **merged to development main**;
official v1.7 Stable untouched. Risk acceptance is documented in
[UART integration acceptance](V1_8_UART_ACCEPTANCE.md). Detailed evidence:
[UART ESP32 + BUSY hardware log](V1_8_UART_ESP32_TEST.md).

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

## Test plan and acceptance (updated after device reports)

- [x] Momentum SDK 87.1 candidate FAP compiles; static/native and
      Windows installer-mock CI checks PASS (run 38326055111).
- [x] Original 11 tool IDs preserved; selected PWM/Counter/Frequency,
      Profiles S1 and Log History regressions PASS after UART use.
      Full destructive/extended regression is not claimed.
- [x] External ESP32-S2 at **9600 8N1**: `ESP32_READY`, `AT` /
      conditional `ESP32_OK` operator-reported PASS.
- [x] External ESP32-S2 at **115200 8N1**: RX/TX and repeated ST2
      bounded traffic PASS; responsive UI, no observed DROP/ERR.
- [x] Explicit Flipper UART TX receives peer's conditional response.
- [x] Repeated START/STOP and BACK/re-entry release/reacquire paths
      PASS in operator's Flipper test; 9600 preserved across re-entry.
- [x] Controlled physical USART BUSY refusal + restart/stop **2/2
      PASS** in separate diagnostic using production UART code.
- [x] Clean-baseline UART ERR counter increment (`E:0 → E:88`)
      and **fresh-session** 9600 recovery operator-reported PASS.
- [ ] Physical UART RX queue `D>0` overflow not shown. Host HAL
      tests confirm 320 bytes → 256 queued + 64 dropped, not physical.
- [x] SBR1 corrected same-screen STOP → change baud → RUN recovery
      **operator-reported functional PASS** on source `12977d2d`
      (FAP SHA256 `f3ce6438280524692908212c0b3c8b4c9a830b7afc467b503aab667d2e7f12d2`).
      No raw E/R/D snapshots provided; no numeric error count claimed.
- [ ] Independent instrumented baud accuracy, longer endurance,
      unrelated simultaneous serial-owner contention, and exhaustive
      screen/calibration test coverage remain unverified.

**Review of actual v1.8 candidate scope:** RX is printable ASCII with
nonprintables shown as periods; visible counters are display-capped;
TX uses an explicit 12-character editor with fixed CRLF; LEFT/RIGHT
change baud only while STOP; STOP/BACK releases UART resources.
Earlier aspirational mentions of HEX view, PAUSE, selectable CR/LF and
timeouts are **not implemented as those independent UI features** in
this candidate. They are deferred design ideas, not acceptance PASS.

**Not this milestone:** automatic protocol decoding, UART bridge to PC,
full-screen text editor, arbitrary voltage level adaptation, USB serial
replacement, I²C or 1-Wire (these are separate scoped features).

Caution: Flipper GPIO is 3.3 V only. Never connect UART to 5 V, RS-232
signal levels, unknown voltage sources, motor controllers or mains.

## Implemented in this candidate (later verified in the specific device checkpoints below)

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

## Final source review checkpoint — 2026-10-13

Read-only review of `labmate_uart.c/.h`, `labmate_input_uart.c`,
`labmate_uart_ui.c`, `labmate_uart_text.c/.h`, navigation, deferred
TX and the CI workflow found the expected bounded ISR-only RX queue,
app-loop draining, non-GUI ISR, explicit TX outside UI mutex,
serial acquire/stop/release ordering, dedicated menu tool ID,
passive 128×64 renderer with capped displayed counts and retained
baud across re-entry. This is **source review, not a new on-device
or pixel-calibrated PASS**. Known UX caveat: `rx_errors` remains
nonzero after STOP/START on the same screen, so ERR can remain lit
without a new error event; re-entering UART resets the session
counters while keeping the selected baud. The rendered R/D/E
values cap at R 999999, D/E 999 although backing counters continue
to accumulate. No production source or FAP was changed by this
review. Physical `D>0` is pending/risk to reconcile before merging
PR #7; optional extra instrumentation must be justified against
the already PASS 115200 ST2, not forced only to trigger DROP.

## SBR1 baud-switch ERR reset — CI and operator-reported device PASS

- **Source fix:** commit `db5392119f84f48ca7391ce8dbab11895d82437c` in
  `src/labmate_uart.c`. Changing 9600/38400/115200 while **STOP**
  begins a fresh RX session: clears R/D/E, old text and stale status,
  preserves TX editor text. Changing baud while **RUN** remains
  forbidden; pressing STOP alone still preserves counters.
- **Host regression:** commit `12977d2dd4dfa661a790e3d8ce9dc5d73258d8e4` in
  `tests/test_uart_hal_host.c`. Exercises prior ERR and DROP, denial
  of RUN-time baud change, STOP-only reset of old counters/display,
  preservation of `AT`, and new-baud RX success with E0 D0.
- **CI VERIFIED PASS:** GitHub Actions run
  [38434053595](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38434053595)
  completed both the Momentum development FAP build (including host UART
  assertions) and Windows installer-mock safety job **success**; the
  stable publishing job correctly **skipped**. Run artifact
  `labmate` (artifact ID `11831648607`) is unexpired and the
  artifact's own provenance reports exact source head
  `12977d2dd4dfa661a790e3d8ce9dc5d73258d8e4`. ZIP digest
  `ea9ab7490194998db0472746fa70ebde9bea01cc2ea2678d34e50b3607422175`
  is **NOT** the standalone FAP hash; deployment must independently
  match the packaged `SHA256SUMS.txt` to the extracted `labmate.fap`.
  **Subsequently installed with SHA256 verification and launched 9/9
  transfer chunks** on Flipper COM7. The operator then reported all
  requested SBR1 functional device steps PASS. Previous UART/ST2/BUSY
  tests remain tied to their own original binaries; they are not
  re-attributed to this FAP.
- **Physical user report (2026-10-13):** after this precise procedure,
  the operator answered **"hepsi passs"** ("all passed"). Accordingly
  same-screen baud correction, returned `ESP32_READY`, and STOP/BACK
  are functional **PASS (operator-reported)**. The user did not supply
  the requested numeric 9600 E count or raw R/D/E snapshots; preserve
  those as unavailable rather than inventing totals. See the
  [dated SBR1 device checkpoint](V1_8_UART_ESP32_TEST.md).
- Physical DROP `D>0` remains **NOT TESTED** regardless of
  SBR1 outcome. PR #7 is integrated in development `main` under
  [documented acceptance boundaries](V1_8_UART_ACCEPTANCE.md);
  v1.7 Stable unchanged.
