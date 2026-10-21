# UI-00 — v2.0 screen and interaction inventory (initial source pass)

Status: **SOURCE INVENTORY / PARTIAL**. No claim of pixel-perfect validation or device testing.
Branch: `dev/v2.0-signal-doctor`. Baseline: published E11 v1.9. Scope: read-only inspection of the current branch.

## Screen registry

The central `src/labmate_view.c` switch renders 17 enum screens: Menu, Gpio, Frequency, Pulse, Generator, Logger, Uart, OneWire, I2c, History, HistoryDetail, About, Profiles, Counter, Button, Alerts, Scope.

`src/labmate_navigation.c` groups 15 selectable tools without changing tool IDs:
- MEASURE (6): GPIO Monitor; Frequency Meter; Pulse Analyzer; Event Counter; Button Analyzer; Logic Scope
- OUTPUT (2): PWM Studio; Threshold Alerts
- RECORDS (3): Data Logger; Log History; Profiles
- COMM (3): UART Terminal; I2C Explorer; 1-Wire Temp
- INFO (1): About

HistoryDetail is an additional screen, not a separate root-menu instrument. Scope has subviews for normal display, compare/details, and reference plus an IRQ-cleanup fault path. About has an overview, project page and 15 per-tool guides (17 pages total).

## Display baseline and drawing ownership

`src/labmate_ui_layout.h`: 128x64 canvas; title baseline y=10, header rule y=13, footer rule y=52, footer text baseline y=61. Pair footer origins x=2 and x=66; triple footer origins x=2,45,96.

`src/labmate_ui_primitives.c`: `ui_draw_header`, `ui_badge`, `ui_footer_pair`, `ui_footer_triple`, instrument icon drawings. Footer pair labels are length-limited to ten characters after compact formatting; triple captions have limits of 7/7/5 characters. These limits are not a substitute for verifying actual font metrics and overlap.

`src/labmate_view.c` runs rendering under the app mutex and clears canvas before dispatch. Normal screen redraw is throttled to ~10Hz; pulse/heavy logger views may use ~5Hz at high pulse rates, with immediate key redraw.

`src/labmate_ui_status.h`: GPIO monitor status precedence is ERROR > BUSY > HOLD > LIVE. Preserve these semantics throughout redesign, and do not imply successful resource release when a fault is active.

## Observed interaction and failure-state details

- Root menu: UP/DOWN selection, OK opens a group or launches an instrument (`src/labmate_input_menu.c`); preserve existing ID-to-tool mapping and BACK handling.
- Frequency: entering the screen starts the chosen low/high frequency capture engine; resource ownership must remain unchanged.
- Generator: entering PWM Studio must **not** start PWM; a skip-entry-OK guard exists.
- Counter: enters stopped; requires explicit OK to run.
- Button: enters reset, without enabling IRQ until OK RUN.
- Profiles: LOAD/SAVE/DELETE; destructive actions have an explicit confirmation screen. Block writes while generator/capture/logger is active. Visible statuses include WAIT, CRC, SD ERR, PWM ON, BUSY, SAVED, LOADED, EMPTY, ERR and DELETED.
- History: list, EMPTY, SD READ ERROR, SCANNING, single-file delete confirmation, and a separate read-only detail page. Preserve existing CSV and deletion behavior.
- Scope: normal/compare/detail/reference paths and a prominent `SCOPE IRQ FAULT / RESTART REQUIRED` state; no stale comparison after failed IRQ release.
- About: informational pages and tool guides, not a measuring mode.

## UI risks to test, not yet established failures

1. Long status strings versus top-right badge widths (e.g. 35px and 49px).
2. Pair/triple footer glyph widths, collisions with menu borders, and strings near x=127.
3. Content baselines around y=51 versus the footer divider at y=52.
4. Inverted/selected list rows, missing or stale text in BUSY/ERROR/EMPTY states.
5. Scope special-mode views whose drawing lives in separate files.
6. All combinations of RUN/STOP, HOLD/LIVE, no-trigger, resource denied, release failure.
7. Confirmation screens: no accidental action on entry; BACK cancels without side effects.

## Acceptance plan (UI-00 remains OPEN)

- Enumerate every drawing operation and state branch across `labmate_ui_screens.c`, `labmate_uart_ui.c`, `labmate_i2c_ui.c`, `labmate_onewire_ui.c`, `labmate_scope_*view.c`, and `labmate_scope_display.c`.
- Map input handlers in `labmate_input_*.c` to actual on-screen captions.
- Add deterministic host-only tests: bounds 0<=x<128 and 0<=y<64; label measured width <= container; footer nonoverlap; black/white selection visibility; state priority; empty/error; confirmation and STOP/BACK semantics.
- Do not claim PASS without running tests. No firmware/FAP build, install, flash, release or device/data writes in this document-only step.
- Once source coverage and tests PASS, begin *one instrument at a time* UI redesign using the shared primitives. Preserve existing navigation, memory structures, CSV/profile compatibility and resource policies.
