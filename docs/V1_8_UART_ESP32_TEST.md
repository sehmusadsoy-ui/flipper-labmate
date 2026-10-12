# LabMate v1.8 UART ↔ ESP32 Interoperability Test

**Status: PLANNED / PENDING. No external ESP32 PASS has been reported.**
User has an ESP32 board; exact variant/pinout is still to be confirmed.
This is a test plan, not a claim that source or installed FAP changed.

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

Ask for exact board/module (ESP32-WROOM-32, ESP32-WROVER,
ESP32-S3, ESP32-C3, other) and framework (Arduino IDE or ESP-IDF).
The Espressif Arduino-ESP32 serial API supports selecting RX/TX pins:
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
