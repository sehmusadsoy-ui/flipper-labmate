# LabMate v1.8 UART ↔ ESP32 Interoperability Test

**Status: PLANNED / PENDING. No external ESP32 PASS has been reported.**
The user identified an **ESP32-S2-WROVER Flipper Dev Board**. The
official Flipper Wi-Fi Developer Board schematics were checked:
https://cdn.flipperzero.one/Flipper_Zero_WI-FI_Module_V1_Schematic.PDF
(ESP module pins and header connector sheets).

The official board's Flipper USART pins 13/14 are already wired to the
ESP32-S2's **GPIO44 RXD0** and **GPIO43 TXD0**, respectively.
Ground is shared through the board connector. No additional UART jumper
or voltage supply wire is needed when the original board is correctly
plugged into Flipper. Do not assume this pinout for aftermarket boards.

**Firmware preservation gate (consent given, upload not performed):**
The operator reports their ESP32-S2-WROVER Wi-Fi Devboard currently
runs Marauder and explicitly agrees to replace its firmware temporarily
for UART testing, with an independent reinstall plan afterward.
Flashing an Arduino test sketch **replaces the firmware**. No flash,
backup, firmware restoration, or on-device test has yet been performed
by the assistant. The operator must use the board's native USB-C
connection and choose the proper ESP32-S2 target/port.

Prepared (not uploaded, not compiled or device-tested):
[`tests/esp32_s2_wrover_uart_peer/esp32_s2_wrover_uart_peer.ino`](../tests/esp32_s2_wrover_uart_peer/esp32_s2_wrover_uart_peer.ino).
Uses ESP32-S2 **UART1** remapped to RX GPIO44 / TX GPIO43 and separate
native USB CDC for debug prints, default 115200/8N1, periodic
`ESP32_READY` and `AT` -> `ESP32_OK` responses. Change baud by entering
`9600`, `38400`, or `115200` in Arduino USB Serial Monitor.
Arduino IDE compatible board family: `ESP32S2 Dev Module` and
`USB CDC On Boot: Enabled`, `Upload Mode: Internal USB`.
Confirm upload options before flashing. Sources:
https://docs.espressif.com/projects/arduino-esp32/en/latest/api/serial.html
https://docs.espressif.com/projects/arduino-esp32/en/latest/tutorials/cdc_dfu_flash.html

## Validated existing baseline

- Flipper's USART is TX GPIO header **13** / RX GPIO header **14**;
  source: https://developer.flipper.net/flipperzero/doxygen/expansion_protocol.html
- User-reported Flipper self-loopback U1–U8: **8/8 PASS** (see
  `docs/V1_8_UART_PLAN.md`). This does **not** prove a separate peer.
- The original test binary was from CI `38305108729`, code
  `e5708831573d16140e0c71387d78ef4875b7b0bf`, SHA256
  `466115746C4420903D21CE3CABA6A0532C799F1117CAC3406D9FF90F015A56BE`.
- LabMate currently offers 9600 / 38400 / 115200 baud, 8N1;
  editable TX text starts as `AT` and explicit SEND appends CRLF.
  Received bytes are rendered as printable ASCII in the UART RX screen.
- PR #7 remains **draft**, unmerged; official `v1.7` Stable untouched.

## Model gate — confirm before assigning ESP32 pins

Board identification completed as **ESP32-S2-WROVER Flipper
Dev Board** (official Wi-Fi Devboard pin map verified from the V1
schematic). The Espressif Arduino-ESP32 API supports selecting
RX/TX pins:
https://docs.espressif.com/projects/arduino-esp32/en/latest/api/serial.html

Espressif's ESP32-DevKitC documentation explicitly warns that
GPIO16/17 are user-available only on ESP32-WROOM/ESP32-SOLO-1
variant boards, not ESP32-WROVER:
https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32/esp32-devkitc/user_guide.html

**Do not assume GPIO16/17 for every ESP32.** Confirm pins on the
actual board's printed legend/datasheet before preparing the precise
wiring diagram or final sketch.

## Electrical and ownership safeguards

- Both GPIO serial interfaces must use **3.3 V logic**, idle-high
  standard non-inverted UART, **8N1** on the same baud rate.
- ESP32 powered by its own normal USB connection; Flipper by its usual
  power source. No 5 V, VIN or 3V3 supply wire is connected between them.
- **Common ground** required: Flipper GND ↔ ESP32 GND.
- **Cross data lines** only after board pin confirmation:
  Flipper GPIO13 USART TX → ESP32 selected UART RX;
  ESP32 selected UART TX → Flipper GPIO14 USART RX.
- Remove the earlier Flipper 13→14 self-loopback jumper first;
  stop UART/PWM and disconnect power when adjusting connections.
- Do not use hardware-level RS-232, 5 V UART, unverified modules,
  boot-strap pins, flash/PSRAM pins, or another UART already owned by
  the ESP32's USB programming/debugging connection.
- Do not reconnect or change wires while an active UART session is RUN.

## Minimal peer firmware behavior (once model known)

Use a UART distinct from the ESP32's USB serial monitor UART.
Arduino API: `HardwareSerial` or supported `Serial1/Serial2`,
with `begin(baud, SERIAL_8N1, rx_gpio, tx_gpio)`.
Write a short `ESP32_READY\r\n` at initialization or periodic
intervals only while testing. Read a line terminated by CRLF; on exact
ASCII `AT` respond `ESP32_OK\r\n`. Forward RX/TX status to USB
Serial Monitor without copying unrelated data or collecting any secrets.

Keep the parser bounded (max ~32 bytes). Switch baud to match Flipper
for each verification round. Avoid automatic transmissions during
rewiring. Exact pin definitions and copy/paste-ready sketch will follow
after identifying the ESP32 board, to avoid driving reserved pins.

## E1–E6 external peer PASS/FAIL matrix

- [ ] **E1, ESP32 → Flipper:** With both UARTs at 9600 8N1, ESP32
      sends `ESP32_READY`; LabMate RX view displays it legibly.
- [ ] **E2, Flipper → ESP32:** LabMate TX editor sends `AT\r\n`
      explicitly; ESP32 USB Serial Monitor logs receipt of `AT`.
- [ ] **E3, Response:** ESP32 returns `ESP32_OK\r\n`; Flipper UART RX
      shows the correct response (not only local echo).
- [ ] **E4, 115200:** With both UARTs stopped/reconfigured to 115200,
      repeat E1–E3; avoid interpreting setup/boot noise as PASS.
- [ ] **E5, Lifecycle:** Repeat short exchanges, STOP and START UART,
      then BACK and re-enter. No freezes, unexpected repeated TX, or
      continuously increasing drop/error counters under modest traffic.
- [ ] **E6, Regression:** Disconnect only after UART STOP and
      powered-down rewiring; reopen PWM, Counter/Frequency, Profiles S1
      and Log History, confirm saved data unchanged.

## Separate remaining stress/conflict gates

- [ ] Demonstrate a legitimate serial-owner conflict: UART refuses
      acquisition with BUSY **without seizing** another service's
      handle; restore original service after releasing UART.
- [ ] Verify RX overflow/drop and error badges under a controlled
      test without crashing, blocking UI or corrupting storage.
- [ ] Assess sustained RX traffic/baud timing with suitable equipment;
      no unsupported calibration claims.

**No merge / no v1.8 Stable** until external peer and required
stress/resource checks are reported PASS or explicitly reconciled.

## Operator preparation in Arduino IDE (not yet executed)

1. Stop LabMate UART/PWM and **remove the Devboard from Flipper**.
   Use a known data-capable USB-C cable for the Devboard's own USB
   connector. Distinguish the Devboard's new serial port from the
   Flipper's original COM7.
2. In Arduino IDE, install the **Espressif Systems esp32** board package
   using the official stable Boards Manager JSON:
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
3. Open
   `tests/esp32_s2_wrover_uart_peer/esp32_s2_wrover_uart_peer.ino`.
   Board: **ESP32S2 Dev Module**. For native USB Serial Monitor,
   **USB CDC On Boot: Enabled**, **Upload Mode: Internal USB**.
4. Press Verify/Compile before any firmware write; report errors rather
   than changing board/flash settings speculatively.
5. For initial USB enumeration where needed: hold Devboard **BOOT**,
   press/release **RESET**, then release BOOT; select the newly
   appearing Devboard serial port. This is distinct from Flipper COM7.
   Follow Espressif USB CDC documentation:
   https://docs.espressif.com/projects/arduino-esp32/en/latest/tutorials/cdc_dfu_flash.html
6. Only after successful Verify and correct Devboard port identification,
   press Upload. Then press RESET to launch sketch if required by
   USB-C flashing. USB serial monitor at **115200 baud** is separate
   from GPIO44/43 hardware UART used by LabMate.
7. Do not presume an upload succeeded; report Arduino compile/upload
   output and observed sketch messages. The Flipper-side FAP is
   unchanged from the previously user-tested v1.8dev UART candidate.

## Board-specific test sequence — consent given; preparation/upload still pending

1. Identify firmware currently running (Blackmagic, Marauder, custom).
   Preserve or arrange a recovery path before any Arduino upload.
2. With the module detached from the Flipper, use its native USB-C
   connection to prepare/program the Arduino peer. If using Arduino IDE,
   target ESP32S2 Dev Module, enable USB CDC On Boot, and select
   Internal USB upload mode. This sketch is **not verified on this
   particular board** and may need adjustment after initial compile.
3. When power is disconnected and all GPIO tools are stopped, seat
   the module normally in the Flipper's header. The board internally
   provides TX↔RX crossed lines and common ground, no extra jumper.
4. Open LabMate COMM → UART, check STOP / 115200, then press RUN.
   The module should produce `ESP32_READY` about every 3 seconds.
5. Open TX editor, send `AT` (CRLF) explicitly. Back to RX; check
   that `ESP32_OK` appears. Because the visible terminal has only
   two rows and READY is periodic, a reply may scroll rapidly;
   inspect RX byte counts as additional evidence.
6. For baud 9600/38400: use the board's USB Serial Monitor to
   set baud first, then match LabMate UART while stopped. Do not
   change wiring while either device is communicating.
7. Record outcomes E1–E6 and any BUSY/ERR/DROP conditions; leave
   PR #7 draft until these are verified.

No claims of ESP32 external PASS until the operator actually returns
device results. Do not overwrite an installed debugging/pentest
firmware merely for a smoke test without informed agreement.
