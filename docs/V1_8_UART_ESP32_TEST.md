# LabMate v1.8 UART ↔ ESP32 Interoperability Test

**Status: ESP32-S2 UART E1–E6 = 6/6 operator-reported PASS (2026-10-13), including bidirectional 115200 and 9600 baud. SR1 UART STOP/BACK/re-entry FAIL diagnosed as lost baud selection (fix pending CI/device validation); BUSY/resource ownership and controlled overflow remain PENDING; PR #7 is draft.**
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
physical device. The operator observed the test firmware's periodic `ESP32_READY`
on Flipper RX (E1 PASS) and the conditional `ESP32_OK` reply after
LabMate sent `AT` (E2–E3 PASS). The operator can reinstall
Marauder after completing tests.

Prepared and operator-reported compiled and uploaded successfully
(external ESP32 ↔ Flipper E1–E3 later passed on device):
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

## External UART checkpoint — E1–E3 3/3 PASS (operator report, 2026-10-13)

- **E1 PASS:** Flipper UART RX shows periodic `ESP32_READY` generated
  by the separate ESP32-S2 Wi-Fi Devboard at 115200 baud/8N1.
- **E2 PASS:** With LabMate RUN and TX editor open, the operator
  explicitly sent `AT\r\n` toward ESP32-S2.
- **E3 PASS:** Flipper RX displayed the ESP32 test firmware's
  **conditional** `ESP32_OK` response. That response is produced
  only after the ESP32 sketch receives `AT`, so it demonstrates
  the external Flipper TX → ESP32 RX direction as well as return RX.
  A USB serial monitor log was not separately supplied or required
  for this functional echo-response test.

**Scope:** Results are operator-reported functional checks, not an
independent timing/electrical calibration or stress validation.
The original LabMate FAP and ESP32 peer firmware remain unchanged
for E1–E3. **No external UART result is inferred for E4–E6.**

### Completed test instructions for E5 and E6 (historical)

- E5: Keep both sides at **115200**, send `AT` several times and
  observe `ESP32_OK` each time, toggle LabMate STOP/RUN three
  times, BACK/re-enter the UART page and ensure the RX keeps
  receiving `ESP32_READY` without BUSY, crashes or unexpected
  TX. Note any `ERR` or `DROP` indicators.
- E6: STOP UART, power down before removing the Wi-Fi Devboard.
  After disconnecting it, check PWM Studio PA7, Counter PB3,
  Frequency Meter, Profiles S1 and existing CSV Log History.
  Existing records must remain intact.
- E4 **requires matching ESP32 peer baud**. The flashed sketch
  initializes at **115200 every reboot**. Changing only Flipper to
  9600 produces an expected baud mismatch, *not* a functional
  failure. Defer E4 until a safe method of setting both baud
  rates to 9600 is prepared (e.g. compile/flash peer sketch
  configured to boot at 9600 while detached from Flipper).
  Do not attach USB power to the seated Devboard to send a
  configuration command without verifying the board's
  power-isolation behavior.

## External UART E5/E6 checkpoint — both PASS (operator report, 2026-10-13)

- **E5 PASS:** Operator reports repeated 115200-baud `AT` ↔
  `ESP32_OK` exchanges, UART STOP/RUN cycles and exit/re-entry all
  succeeded, without reported freeze or unexpected resource conflict.
- **E6 PASS:** Operator reports PWM Studio, Counter, Frequency Meter,
  Profiles S1 and Log History remained usable after stopping UART
  and safely removing the ESP32-S2 Wi-Fi Devboard. Previous records
  were preserved.
- These are **operator-reported** observations; not independently
  instrumented. Functional external UART E1/E2/E3/E5/E6 total **5/6
  PASS**. E4, BUSY conflict, overflow and sustained-traffic checks
  have not been marked PASS.

## E4 preparation — dedicated 9600 baud peer sketch (not flashed)

Separate 9600-boot variant prepared at
[`tests/esp32_s2_wrover_uart_peer_9600/esp32_s2_wrover_uart_peer_9600.ino`](../tests/esp32_s2_wrover_uart_peer_9600/esp32_s2_wrover_uart_peer_9600.ino).
It is based on the operator-proven 115200 sketch; only
`currentBaud` initialization and the USB startup log's default
baud label were changed to **9600**. The 115200 sketch remains
unchanged for reproducibility.

1. Confirm LabMate UART **STOP**, other GPIO generators stopped.
   Power off/disconnect safely; remove Devboard from Flipper.
2. Connect the *detached* ESP32-S2 board to Windows by its own
   USB-C data cable. Verify the USB VID `303A` and actual serial
   COM number. It may not still be `COM12`.
3. Arduino CLI (core `esp32:esp32@3.3.12`) compile the 9600
   variant with FQBN
   `esp32:esp32:esp32s2:CDCOnBoot=cdc,UploadMode=cdc`.
   **Only** upload to verified ESP32 port after successful compile
   and operator confirmation. This overwrites the previously
   flashed 115200 peer test sketch, not the Flipper FAP.
4. Unplug ESP32 USB, and with devices unpowered correctly seat
   the board in Flipper. Start LabMate UART in STOP,
   select **9600**, then RUN.
5. **E4 PASS criterion:** both periodic `ESP32_READY` and
   the conditional `ESP32_OK` after sending `AT\r\n` appear,
   with no unexpected BUSY, ERR, DROP or lock-up.
6. Report observations; 9600 peer firmware may later be replaced
   with original Marauder via the user's own restoration procedure.

**Important:** changing only Flipper to 9600 while running the
original 115200 ESP32 peer causes an expected baud mismatch.
Do not power the ESP32 independently via USB while it is seated
on Flipper without validated isolation.

## E4 9600-baud sketch build AND upload — PASS (operator reports, 2026-10-13)

The operator ran `arduino-cli compile` targeting
`esp32:esp32:esp32s2:CDCOnBoot=cdc,UploadMode=cdc` using the
dedicated 9600-baud sketch at
[`tests/esp32_s2_wrover_uart_peer_9600/esp32_s2_wrover_uart_peer_9600.ino`](../tests/esp32_s2_wrover_uart_peer_9600/esp32_s2_wrover_uart_peer_9600.ino).
The terminal showed:

- `Sketch uses 304748 bytes (23%) of program storage space.`
- `Global variables use 49000 bytes (14%) of dynamic memory.`
- `ESP32-S2 9600 BUILD PASS`.

**9600 firmware upload now user-reported PASS**. After recompiling and
checking the ESP32 USB port, the operator's PowerShell output concluded:

```
Hard resetting with a watchdog...
New upload port: COM12 (serial)
ESP32-S2 9600 UPLOAD PASS
```

This confirms a successful reported upload of the dedicated 9600 test
sketch to ESP32-S2 COM12; the pasted final lines do not independently
show every preceding esptool flash block. **E4 hardware UART test was subsequently performed and reported PASS**
by the operator; see checkpoint below. The upload log independently
shows only completion, not physical UART test measurements. The
Flipper-side LabMate FAP and its previous v1.7 Stable release have
not been changed.

**Flash gate completed (operator report):** dedicated 9600 sketch was
built and uploaded via the USB COM12 link. No more firmware upload
is needed for the immediate E4 functional test.

**Previous E4 operator test procedure (completed):** with Flipper UART STOP and any
external USB power unplugged, detach USB-C from ESP32 and reconnect
the official devboard to the Flipper header in the correct orientation,
with no extra jumper or power wire. Start LabMate COMM → UART; while
STOP, use LEFT/RIGHT to set **9600** (NOT the default 115200), then
OK to RUN. Observe periodic `ESP32_READY` after several seconds,
then DOWN → TX editor `AT` → OK SEND → BACK to RX; expect conditional
`ESP32_OK`. Verify no BUSY/ERR/DROP and that RX counters increase.
Mark E4 PASS only after the operator reports both messages at 9600.
If the response does not appear, report exactly what the Flipper shows
and keep E4 pending/FAIL as appropriate.

## External ESP32-S2 checkpoint E4 — PASS (operator report, 2026-10-13)

After successfully compiling and flashing the separate `currentBaud =
9600` peer sketch, the operator selected 9600 on Flipper UART while
STOP, entered RUN and reported:

- `ESP32_READY`: **PASS** (ESP32 → Flipper).
- Flipper TX `AT` → conditional `ESP32_OK` RX: **PASS**
  (Flipper → ESP32 → Flipper).
- **E4 9600 external UART PASS**; overall external E1–E6 = **6/6
  user-reported PASS**.

This corroborates functional UART interoperability at **115200 and
9600 baud, 8N1**. The result is not an instrumented baud-rate
accuracy measurement or a controlled overflow / ownership conflict
test. Those remain separate acceptance gates.

### Next low-risk test — sustained low-rate receive (SR1 pending)

Use the *already flashed* ESP32-S2 9600-baud firmware, without
reflashing or changing wires. LabMate UART STOP → select **9600** → RUN.
Wait **2 minutes** while the ESP32 peer sends `ESP32_READY` roughly
every 3 seconds; then note `R:`, `D:`, `E:` and status badge,
and ensure the GUI remains responsive. STOP, BACK, then re-enter
UART to verify resource cleanup. **SR1 PASS** is warranted only
if UART stays usable, RX count rises, no unexpected BUSY, and
`D:0 E:0` under this moderate rate.

This checks stable ordinary RX service, **not** the overflow branch.
It must not be recorded as proof that DROP/ERR warnings work. A
controlled stress/overflow test, and a legitimate existing serial-owner
BUSY conflict, remain PENDING.

## SR1 regression — FAIL after UART BACK/re-entry (operator report, 2026-10-13)

**SR1 result: FAIL.** The operator reported a continuously
increasing RX count (approximately **R:440** at one observation),
**D:0**, but after step 4 (STOP → BACK → re-enter UART), the text
changed into dots (`..............`) and **E incremented
together with RX**. This is not an RX-buffer overflow report;
the observed ERR likely reflects UART framing/noise errors.

**Root cause found in source:** UART input menu handler called
`labmate_uart_reset(&app->uart)` on *every* UART screen entry.
That reset sets `baud_index = 2`, silently reverting the UART to
**115200**. The ESP32-S2 peer is now running the dedicated **9600**
baud sketch, so an operator who re-enters and presses RUN without
resetting baud encounters a 9600↔115200 mismatch. ASCII renderer
turns nonprintable characters into `.`. This is consistent with
all reported symptoms; confirm by observing UART baud after re-entry
and retesting 9600.

**Development fix prepared (not yet device-installed or verified):**
the UART menu now invokes `labmate_uart_reenter` to preserve selected
`baud_index`, while clearing per-session text/counters and ensuring
hardware stays STOP. A source guard was added to prevent reverting
to reset-on-every-entry. A fresh Momentum SDK CI and Flipper
device retest are mandatory before marking this fix PASS.

**Immediate workaround on old FAP:** after re-entering UART,
verify displayed baud, STOP, select **9600**, then RUN.
If desired, clear the visible terminal via UP.
Record new R/D/E observations. No ESP32 reflash is required.

The earlier E1–E6 tests **remain operator-reported PASS**, since
those tested proper matching baud rates; this new SR1 issue is a
separate lifecycle setting-preservation regression.

## E1–E6 external peer PASS/FAIL matrix

- [x] **E1, ESP32 → Flipper:** With both UARTs at the sketch's default
      **115200 8N1**, ESP32 sends `ESP32_READY` about every 3 s;
      LabMate RX view displays it legibly.
- [x] **E2, Flipper → ESP32:** LabMate TX editor explicitly sends
      `AT\r\n`. If Flipper then receives the *conditional*
      `ESP32_OK`, this also confirms the ESP32 received `AT`;
      separate USB Serial Monitor logs are optional, not necessary.
- [x] **E3, Response:** ESP32 returns `ESP32_OK\r\n` only after
      it receives `AT`; Flipper UART RX shows the correct response
      (not merely another `ESP32_READY`).
- [x] **E4, 9600:** With both UARTs stopped/reconfigured to **9600**,
      repeat E1–E3; avoid interpreting setup/boot noise as PASS.
- [x] **E5, Lifecycle:** Repeat short exchanges, STOP and START UART,
      then BACK and re-enter. No freezes, unexpected repeated TX, or
      continuously increasing drop/error counters under modest traffic.
- [x] **E6, Regression:** Disconnect only after UART STOP and
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

### Previous E1 setup (completed; historical procedure)

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

## Board-specific test sequence — completed initial 115200 tests (historical procedure)

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
