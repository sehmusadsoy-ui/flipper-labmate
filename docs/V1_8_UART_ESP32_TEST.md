# LabMate v1.8 UART ↔ ESP32 Interoperability Test

**Status: ESP32-S2 Arduino CLI compile and USB upload PASS; first external UART test E1 ESP32 → Flipper PASS (user-reported 2026-10-13). E2–E6 and stress/resource checks remain PENDING.**
The user identified an **ESP32-S2-WROVER Flipper Dev Board**. The
official Flipper Wi-Fi Developer Board schematics were checked:
https://cdn.flipperzero.one/Flipper_Zero_WI-FI_Module_V1_Schematic.PDF
(ESP module pins and header connector sheets).

The official board's Flipper USART pins 13/14 are already wired to the
ESP32-S2's **GPIO44 RXD0** and **GPIO43 TXD0**, respectively.
Ground is shared through the board connector. No additional UART jumper
or voltage supply wire is needed when the original board is correctly
plugged into Flipper. Do not assume this pinout for aftermarket boards.

**Firmware preservation gate (consent given, upload completed):**
The operator reports their ESP32-S2-WROVER Wi-Fi Devboard currently
runs Marauder and explicitly agrees to replace its firmware temporarily
for UART testing, with an independent reinstall plan afterward.
The operator flashed the Arduino test sketch, replacing Marauder on
the ESP32-S2 board for this test. The assistant did not access the
physical device. The operator has now observed the test firmware's periodic
`ESP32_READY` on Flipper RX (E1 PASS). Return traffic is not yet confirmed. The operator can reinstall
Marauder after completing tests.

Prepared and operator-reported compiled and uploaded successfully
(external ESP32 → Flipper RX E1 subsequently passed on device):
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

- [x] **E1, ESP32 → Flipper:** With both UARTs at the sketch's default
      **115200 8N1**, ESP32 sends `ESP32_READY` about every 3 s;
      LabMate RX view displays it legibly.
- [ ] **E2, Flipper → ESP32:** LabMate TX editor explicitly sends
      `AT\r\n`. If Flipper then receives the *conditional*
      `ESP32_OK`, this also confirms the ESP32 received `AT`;
      separate USB Serial Monitor logs are optional, not necessary.
- [ ] **E3, Response:** ESP32 returns `ESP32_OK\r\n` only after
      it receives `AT`; Flipper UART RX shows the correct response
      (not merely another `ESP32_READY`).
- [ ] **E4, 9600:** With both UARTs stopped/reconfigured to **9600**,
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

## Windows Arduino CLI compile checkpoint — user-reported FAIL; fix pending

The operator provided the complete original compiler diagnostic on
2026-10-13: `line 15: error: expected unqualified-id before numeric constant`
at `static constexpr size_t LINE_MAX = 31;`, which confirms the
`LINE_MAX` macro collision. Changed the identifier to `UART_LINE_CAP`
in code commit `cdf6ce92aab155167b1f4300a54890d55f5434c6`.

**Corrected build: user-reported PASS** with Arduino CLI, ESP32 Arduino
core `esp32:esp32@3.3.12`, FQBN
`esp32:esp32:esp32s2:CDCOnBoot=cdc,UploadMode=cdc`.
Compiler reported sketch 304,748 bytes of 1,310,720 bytes (23%);
global variables 49,000 bytes of 327,680 bytes (14%), leaving
278,680 bytes. Exit status 0 and conditional PASS output shown.

No ESP32-S2 firmware upload, ESP32 board/COM-port identification or
external communication has been reported yet. Marauder remains on
the board until the operator performs the explicit USB firmware upload.

## ESP32-S2 USB firmware upload checkpoint — PASS (operator report, 2026-10-13)

- User-provided PowerShell/esptool **v5.3.1** upload transcript identifies
  **ESP32-S2** on the previously validated native USB **COM12** port.
- Fresh Arduino CLI compile succeeded: 304,748 sketch bytes (23% of
  available program storage) and 49,000 global bytes (14% of RAM).
- esptool wrote bootloader, partitions, `boot_app0`, and the test sketch.
  Every flash section reported **`Hash of data verified`**.
- Final terminal output: `Hard resetting with a watchdog...`,
  `New upload port: COM12 (serial)`, and
  **`ESP32-S2 UART UPLOAD PASS`**.
- Flash write/verification succeeded; **subsequent** operator-reported
  E1 ESP32 → Flipper reception PASS. E2–E6 are pending.
- The flash replaced the owner's Marauder firmware with prior consent.
  No restoration has been attempted or claimed.

### E1 external RX — PASS (operator report, 2026-10-13)

The operator reported **E1 PASS** after installing and seating the
ESP32-S2-WROVER test board and observing the ESP32-generated
`ESP32_READY` in LabMate's UART RX display at default 115200 8N1.
This is the first confirmed *external peer → Flipper* data path, not
just the previously passing pin 13→14 loopback.

**Not yet verified:** Flipper TX → ESP32, conditional `ESP32_OK`
response, other peer baud rates, buffer overflow, source BUSY conflicts,
and independent timing calibration. No code/firmware changes or fresh
Flipper installation were required by this report.

### Next test — E2 + E3 explicit request/response at 115200

1. Keep the ESP32-S2 devboard in place and powered from its dedicated
   Flipper header, **without adding an ESP32 USB cable** or changing
   live connections. LabMate UART remains RUN at 115200.
2. Press DOWN for TX; verify the editable payload is exactly `AT`.
   Press OK once to send `AT\r\n` to the ESP32 peer.
3. Press BACK once (returns to RX screen; **does not** exit UART while
   TX editor is displayed). Check for `ESP32_OK` in the two-row RX
   display. The sketch also broadcasts `ESP32_READY` every 3 seconds,
   so the reply may scroll; repeat single sends if needed.
4. Record E2 **PASS** when E3's conditional response `ESP32_OK`
   proves the ESP32 received `AT`; record E3 **PASS** when Flipper
   visibly receives `ESP32_OK`. If only `ESP32_READY` is seen,
   E1 still passes but E2/E3 are **not** confirmed.
5. If the result is unclear or fails, report `RUN/BUSY/ERR/DROP`,
   RX byte count and observed text; don't prematurely mark E2/E3 PASS.

The ESP32 USB Serial Monitor is **optional** and should not be
connected while the board is attached/powered via Flipper unless
its power isolation is independently established. E2/E3 require no
extra cables, firmware replacement or Arduino IDE.

### Next immediate test — E1 only, no external GPIO jumper

1. Stop Flipper UART/PWM. Disconnect the original Flipper pin 13 ↔ 14
   self-loopback jumper and USB leads. Power equipment down before
   inserting the dedicated official Wi-Fi Devboard.
2. Seat the devboard in the **correct orientation**, aligning its
   dedicated Flipper header pins. Do not connect extra 5 V, 3.3 V,
   or TX/RX jumpers; the official board includes the signal connections.
3. Start LabMate COMM → UART Terminal, default STOP at **115200 baud**;
   press OK to enter RUN. Wait 5–10 seconds.
4. Expect `ESP32_READY` in the RX text display about every 3 seconds.
   Check the RX count and status indicator.
5. Record **E1 PASS** only on observed `ESP32_READY`. Otherwise report
   **E1 FAIL** with exact state, e.g. `BUSY`, `RX=0`, garbled text,
   `DROP` or `ERR`. Stop before E2–E6 if E1 fails.

## Windows port identity checkpoint — user reported (2026-10-13)

- Arduino CLI `board list` returned `COM12 serial Serial Port (USB) Unknown`.
- Windows `Get-PnpDevice -PresentOnly -Class Ports` showed a USB serial
  device on `COM12` with Espressif USB vendor ID `VID_303A`, product
  ID `PID_0002`. This is consistent with the ESP32-S2's native USB
  interface. The generic `Unknown` board label is not a compile
  failure; FQBN was specified explicitly.
- Flipper was previously on `COM7`, and the operator must never use
  COM7 as the ESP32 upload destination. Before writing, recheck that
  COM12 is still connected and has the same expected VID/PID.
- **Subsequent user report confirmed USB firmware upload PASS**; see
  the timestamped upload checkpoint above.

Recommended controlled upload command: recompile the corrected sketch
with `arduino-cli compile --fqbn
esp32:esp32:esp32s2:CDCOnBoot=cdc,UploadMode=cdc --output-dir
<unique-build-dir> <sketch-dir>` and then use
`arduino-cli upload --input-dir <unique-build-dir>
--fqbn <same-fqbn> -p COM12 <sketch-dir>`, after verifying the active
device ID. The operator should report the final upload exit status;
a native USB port may change or disappear across reset.

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
