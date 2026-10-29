# LabMate Ultimate v2.0 E11 — COMM pixel/UI acceptance and open deviations

Date: 2026-10-29  
Target: patched Momentum E11, Flipper Zero 128x64, firmware API 87.1  
Branch: `dev/v2.0-e11-legacy-ui-harness-review-20261029`  
Scope: ONLY the three COMM renderers: UART receive, I2C explorer, 1-Wire temp.  
**Gate: host/source-link PASS; real Flipper pixel/raster acceptance PENDING.**
This was written before device installation; the 2026-10-29 update below
supersedes its original **no-install-yet** planning language. Do not read
that historical wording as the current installation status.

## 2026-10-29 device deployment and owner visual approval

- **USB install completed:** one canonical `/ext/apps/Tools/labmate.fap`
  (177804 bytes, SHA-256
  `160e1c2c7e5f63418bf641fc7b5ab9a72f5bb45219126d914b94185654d10e7e`).
  Old FAP was read back/verified and saved to the PC first; new device
  write/readback PASS in operator-submitted console log.
- **Visual design decision:** owner reports the unified application screens
  look consistent and premium and explicitly approves **UI design
  consistency**. Design iteration is closed; preserve current graphics.
- **Do not reclassify C01–C09 as individual PASS:** a state-by-state on-device
  screenshot and all external electrical tests have not been documented.
  These are separate quality gates, not prerequisites for recording the
  owner's overall visual approval.
- **Next active track:** hardware functionality and exception handling
  using [UI freeze / hardware handoff](V20_E11_UI_FREEZE_AND_HARDWARE_HANDOFF_2026-10-29.md).
  No new FAP build, firmware flash or automatic re-install was performed
  by this documentation update. Stable remains blocked.

## Source-of-truth and preservation

- `src/labmate_uart_ui.c`: UART RX display only. The same function's UART TX branch remains visually unchanged, including its hidden DOWN-to-TX access from RX Live.
- `src/labmate_i2c_ui.c`: output of the original read-only `labmate_i2c_runtime_snapshot`. **4 real addresses per page** from `LabMateI2cView.row_address[4]`; pages continue via **UP/DOWN**, never LEFT/RIGHT.
- `src/labmate_onewire_ui.c`: display only, still accepts successful DS18B20 `Measured` with `has_temperature`, range -55.0..+125.0 C, and 9..12 bit resolution. CRC/power/lease statuses are supplied by untouched driver.
- NO change to input handlers, serial baud presets, scan algorithm, I2C timing, DS18B20 converter, pin assignments, ownership, firmware, storage, CSV or profile data.
- Shared `ui_kit_tag` is 9px tall, right-inclusive x=123, y=12; state chips remain right-aligned x-right=127 at y=0.
- `ui_frame` is a short **carousel tween**, NOT an ongoing clock: the three COMM renderers now use the existing `ui_pulse_phase`, which advances at about 33ms when animations are enabled. Thus the Live ring toggles every 15 phases (~495ms before refresh quantization); I2C SCL visualization shifts its synthetic 10-pixel phase. Existing normal display refresh remains about 10Hz. With Motion disabled the decorative animation remains static; measurement and scanning still work.

## Nine target visual states — manual on-device acceptance

| ID | Tool/state | Expected | Manual gate |
|---|---|---|---|
| C01 | UART receive / Ready | Chevron and correct chip; RX pin 14 and TX pin 13; baud pill; three zero-valued counters; OK Start and LR Baud | PENDING |
| C02 | UART receive / Live | Live glyph pulses; actual Received/Dropped/Errors; OK Stop, LR Baud visible but input refuses baud change while active | PENDING |
| C03 | I2C explorer / Ready | Single 3.3 V tag, PC0 SCL/PC1 SDA context or logged short fallback, dotted idle bus, OK Scan | PENDING |
| C04 | I2C explorer / Scanning | Animated **illustrative** SCL square-wave and SDA pulse, text Scanning bus..., OK Stop; no claim of electrical measurement | PENDING |
| C05 | I2C explorer / Found | 28x10 px non-selectable ACK-address chips, genuine 4-per-page model, count/plurality, UP/DOWN Page only for page_count > 1, OK Scan again | PENDING |
| C06 | I2C explorer / No reply | No reply status, framed No devices panel and Check wiring and pull-ups (whole-text fallback permitted), OK Scan again | PENDING |
| C07 | 1-Wire temp / Ready | One 3.3 V tag, DQ pin PA4, a *single* external VDD warning, --.- with C, OK Read | PENDING |
| C08 | 1-Wire temp / Done | Only CRC-valid converted value, signed decimal + degree ring + C, reported resolution 9..12-bit, Done check, OK Read again | PENDING |
| C09 | 1-Wire temp / No reply | No reply chip, DQ/power guidance, --.- instead of reused temperature, OK Read | PENDING |

Additional distinct states **must not masquerade as target states**:

- UART blocked = Busy; invalid baud = Error; completed nonzero data + inactive = Stopped. A stopped zero-byte session is indistinguishable from never started in current model; it currently displays Ready and remains an explicitly accepted limitation of the display-only scope.
- I2C firmware timed API absent = Error; local bus refused = Busy; scan failure = Error; cancelled = Stopped. Never convert incomplete/aborted probe into No reply or Found.
- 1-Wire lease/bus conflict = Busy; CRC/invalid measurement/power-on 85C candidate = Error; conversion explicitly stopped = Stopped. Never render a successful temperature for these cases.

## Manual image capture checklist (not yet executed)

1. Capture **actual 128x64 on-device pixels**, not an approximate-font mock, for C01..C09 when the corresponding real runtime state is reachable. Keep other states as DEFERRED if no sensor or bus stimulus is available.
2. Check one back chevron at x~2..5, status chip inside 0..127, no title/status collision, no clipped words. Record the **exact abbreviated header/text** if a real firmware font forces fallback.
3. Check tag `3.3 V` at x-right=123, y=12 on I2C and 1-Wire. UART context has no such tag.
4. Check no historical `STOP` on the never-started UART screen; no `R:0 D:0 E:0`, `OK START / LR BAUD`, duplicated external VDD warning or bottom Back/Exit/Menu.
5. Compare real key action, not only the label: UART OK/LR and unchanged DOWN→TX; I2C OK and UP/DOWN page change; 1-Wire OK during conversion stops, otherwise reads; BACK exits with unchanged resource safety.
6. With animations enabled, compare two Live frames and two I2C Scanning frames for change. With animations disabled, ensure scanner and sensor still function without moving decorative pixels.
7. Verify the UI reads no imaginary ACK addresses, does not show a truncated temperature as valid, and cannot convert an error or cancelled scan into Done/Found.
8. Annotate each test as PASS, FAIL, DEFERRED or BLOCKED with screenshot, exact FAP SHA-256, firmware commit, date, and an observed behavior. Never treat the host drawing test as physical evidence.

## Known differences from sheet_comm_v2 (not silently approved)

| Difference | Reason / effect | Status |
|---|---|---|
| Long FontPrimary titles may become FontSecondary or shorten to UART / I2C / 1-Wire | Status chip at x-right=127 has priority; title/collision guard refuses clipping | OPEN visual review |
| UART Received / Dropped may become Recv / Drop | 42px counter columns cannot contain every label with the actual font | OPEN visual review |
| I2C context may show SCL0 / SDA1 | The full SCL PC0 · SDA PC1 line cannot always share y=20 with the 3.3 V tag | OPEN visual review |
| I2C Found shows 4, not 8 addresses on a page | Real view model is row_address[4]; changing it is outside display-only acceptance | ACCEPTED functional constraint; visual signoff OPEN |
| I2C Page uses UP/DOWN not LEFT/RIGHT | Actual unchanged input map | ACCEPTED functional constraint |
| Long status explanations may switch to whole short strings | Text width is measured, no clipping | OPEN visual review |
| UART Live has hidden DOWN→TX editor access not disclosed by bottom chip | User explicitly excluded TX screen and required unchanged input | OPEN UX follow-up |
| 2-frame glyph morph / 3-frame Ready→Found dither not implemented | Requires reliable per-Comm transition state; not inferred from one-shot ui_frame | OPEN animation enhancement |
| 500ms Live pulse is approximate ~495ms | Existing 33ms UI clock and ~10Hz visible redraw, no blocking timers | OPEN physical visual review |
| Missing BigNumbers minus/period detected via Canvas glyph-width query; fallback draws only those marks in Primary | Protects signed and empty readings; requires real-font pixel confirmation | OPEN visual review |
| UART stopped with zero RX bytes looks Ready | Session history not stored; display-only patch cannot distinguish | OPEN semantics, no data-model change |

## Automated pre-device checks

- `sh scripts/test-v20-e11-comm-current-host.sh` — extracts **current production UART/I2C/OneWire function bodies**, builds via GCC and Clang, tests display-only behavior and bounded geometry under conservative stub font metrics. Includes explicit checks that constant `ui_frame=6` does not freeze Live chip or I2C SCL animation when `ui_pulse_phase` changes. NOT a real-device raster.
- `sh scripts/audit-v20-e11-predevice.sh` — wider regression gate for all current tools and supported data/ownership tests; does not imply hardware PASS.
- GitHub E11 native review workflow — compile the exact development candidate with its pinned patched Momentum E11 FBT/SDK, `SDKCHK` + `APPCHK`; review only, **NO USB installation**.

## Release/install boundary

- **Current state (2026-10-29):** the operator-authorized USB install was
  completed and its readback PASS was logged; the app remains a
  **v2.0DEV candidate**, not a Stable release.
- The currently installed visually approved `/ext/apps/Tools/labmate.fap`
  must not be replaced automatically. Do not install a new file or run
  new FAP builds merely for documentation or stylistic experiments.
- Keep the **verified previous FAP PC backup** and the single canonical
  name. Any later source change requires its own full FAP SHA, new
  backup, intentional USB consent and readback. No firmware flashing.
- Owner overall visual approval is **complete**; detailed unusual-state
  pixel screenshots and electrical UART/I2C/DS18B20 tests remain OPEN.
- Stable promotion remains blocked on the device-level functional
  and broader deferred hardware matrix.
