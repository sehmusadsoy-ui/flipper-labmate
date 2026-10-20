# LabMate v2.0 — UI-00 Source-based Screen & State Inventory

**Date:** 2026-10-21  
**Work item:** UI-00 / P0-02  
**Status:** **READ-ONLY SOURCE INVENTORY RECORDED; GEOMETRY/HOST/DEVICE VALIDATION PENDING**  
**Source ref at inspection:** `dev/v2.0-signal-doctor` at `3673dccec14eb56e06744633b56e5cf65ce8aba8` (before this document commit).  
**Baseline:** Published E11-only v1.9 tag `72eb58d6c65d31f510acf6f532ee23c543a9149d`, FAP 101,468 bytes.  
**Scope:** Inspect current source only; this document is not a v2.0 feature implementation, a test-run log, or a claim of pixel-perfect rendering.

## 1. Immutable navigation inventory

`src/labmate_navigation.h` retains **15 flat tool IDs (0 through 14)**. Its **five root groups** must retain the following order, with About/INFO last:

| Root group | Tools in current child order |
|---|---|
| MEASURE (6) | GPIO Monitor; Frequency Meter; Pulse Analyzer; Event Counter; Button Analyzer; Logic Scope |
| OUTPUT (2) | PWM Studio; Threshold Alerts |
| RECORDS (3) | Data Logger; Log History; Profiles |
| COMM (3) | UART Terminal; I2C Explorer; 1-Wire Temp |
| INFO (1) | About |

`src/labmate_internal.h` defines **17 screen enum entries**, including the root/group menu and the separately dispatched History Detail screen; Scope is one screen enum with additional subpage state. Do not renumber screen/tool IDs or rewrite stored Profiles.

Current `draw_menu` uses the parent/group title at (2,10), a version badge at (70,1) of width 56, a header divider at y=13, up to **three visible list rows** at y=25/37/49, a footer line at y=52 and key hints at y=61. Root UP/DOWN wraps the selection; OK enters the group; within a group OK selects a tool and BACK returns to root. Source-navigation changes do not directly acquire hardware.

## 2. Render-dispatch inventory

`src/labmate_view.c` dispatches the following current display states. All are part of the application-wide v2.0 redesign scope, NOT a Scope-only refresh.

| Dispatch screen | Renderer | Source / characteristic states to test |
|---|---|---|
| Menu | `draw_menu` | Root vs group; selection first/middle/last; 1-, 2-, 3- and 6-tool lists; long titles |
| GPIO | `draw_gpio` | HIGH/LOW, edge count scale, hold/live, selected pin, PA7 busy |
| Frequency | `draw_frequency` | valid/invalid frequency, high/low input, MIN/MAX, hold/live, reset |
| Pulse | `draw_pulse` / `draw_pulse_stats` | measurement vs stats; HIGH/LOW/PERIOD/DUTY invalid/valid, hold/live, pin |
| Generator | `draw_generator` | PWM running/stopped, custom-frequency edit, 1–50 kHz formatting, duty |
| Logger | `draw_logger` | source modes, recording, saved/stopped, SD busy/error, capture conflict |
| History | `draw_history` | empty, busy, read error, list, delete confirmation |
| History Detail | `draw_history_detail` | no file, filename/mode/time, busy/error |
| About | `draw_about` | version, source link, guide pages, terminal page controls |
| Profiles | `draw_profiles` | S1–S3, empty/CRC/error, busy, saved/loaded, delete/overwrite confirmations, PWM/capture conflicts |
| Counter | `draw_counter` | running/stopped/paused, count/time scale, reset, resource refusal |
| Button | `draw_button` | main/contact vs details; press/release, bounce/settle/hold, stopped/resume |
| Alerts | `draw_alerts` | unarmed/armed/latched; source/limit; acknowledge |
| UART | `draw_uart` | active/stopped/busy/error; RX vs 12-character TX editor, baud, receive data |
| 1-Wire | `draw_onewire` | ready/running, absent sensor, busy, CRC error, temperature/read |
| I2C | `draw_i2c` | ready/scanning, busy, no ACK, scan/error, addresses, stop |
| Logic Scope | `labmate_scope_display_draw`, `labmate_scope_pair_view_draw`, `labmate_scope_reference_view_draw` | See dedicated Scope matrix below |

Source implementation locations include `src/labmate_ui_screens.c`, `src/labmate_uart_ui.c`, `src/labmate_i2c_ui.c` and `src/labmate_onewire_ui.c`. All 17 enum cases occur in the current `labmate_view_render_callback` switch.

## 3. Scope page/state safety matrix

`src/labmate_scope_bridge.c` cycles on DOWN **only while capture is inactive**:

| Logical page | Header | Rendering | Controls and state variants |
|---|---|---|---|
| 1 | SCOPE, 1/4 | real PC1 digital plot + status/metrics | OK Run/Stop; DOWN next only when inactive; BACK safe exit; READY, ARMED, LIVE, HOLD, NO SIG, QUIET, FULL, BUSY, UNSUP, ERROR |
| 2 | COMPARE, 2/4 | sequential saved A/B and deltas | LEFT Save A, RIGHT Save B subject to generation/lease validity; empty A/B; UP More |
| 3 | A DETAIL / B DETAIL, 3/4 | five measured timing fields | UP toggles A/B where B exists; empty sample; DOWN page |
| 4 | REFERENCE, 4/4 | chosen target, measured values and verdict | UP preset toggle; PASS, FAIL, NO SIGNAL, BUSY, WAIT; DOWN page |

Scope physical viewport is bounded at **x=2..125, y=15..42**; header divider y=13, measured status y=51, footer divider y=54, footer text baseline y=62. Scope footer columns are x=2,47,85, with the hardware BACK action at x=85. Existing plot guards validate line coordinates and decline stale/invalid completed metrics; preserve these contracts.

Special fail-closed screen: `SCOPE IRQ FAULT / RESTART REQUIRED` is drawn instead of A/B content if native STOP confirmation is not possible. Never replace that warning with a stale comparison or a fabricated waveform. A/B captures are sequential PC1 observations, never simultaneous dual channels.

## 4. Existing UI primitives and discovered consistency issues

- `ui_draw_header`: title baseline (2,10), separator y=13.
- `ui_badge`: 11-pixel-high frame/fill with FontSecondary string at x+4,y+8; caller chooses width.
- `ui_footer_pair`: separator y=52; label baselines y=61; action cells start at x=2 and x=66; format `(key) action` with 10-character bound.
- `ui_key`: individual hint baseline y=61; used in Menu/GPIO.
- Scope instead uses `labmate_scope_ui_header/footer` (header y=13; footer y=54), and fixed `(B)Exit`.
- About, Frequency, Pulse/Stats and History Detail include hand-placed footer texts; they do **not** all use the common footer helper.
- PWM dispatch recognizes `InputTypeShort` and `InputTypeLong`, while most other screens use `InputTypePress`. A cosmetic remapping must not trigger unintended PWM start/stop.
- Many labels and measurement fields are placed at fixed x/y coordinates without a single cross-tool geometry contract. This is a **test coverage risk**, not a demonstrated overflow bug.
- Existing short ASCII-based width/length guards do not prove every rendered value fits under all font settings. Font metrics and chosen glyphs must be verified with the real/stub renderer, not estimated from character count alone.

## 5. Observed input ownership and safe exit

`src/labmate_input.c` routes by current screen to separate input handlers. `src/labmate_input_menu.c` drives menu transitions; measure/output/history/profiles/UART/I2C/1-Wire handlers remain distinct. Scope input uses `labmate_scope_bridge_input`; BACK attempts resource STOP and returns to Menu **only after successful stop confirmation**. Preserve all existing STOP/BACK gates, deferred SD operations, resource refusal and input semantics while refactoring display code.

## 6. Source blob evidence (GitHub read-only)

| File | Observed Git blob SHA |
|---|---|
| `src/labmate_navigation.c` | `762571cb1b03d168330a99194929ba79a994a527` |
| `src/labmate_navigation.h` | `8e2a3cd99f364bbce6930e639640313fcc2371b0` |
| `src/labmate_internal.h` | `ade05ed99bbc4335b6428ba69cbd736395d290b2` |
| `src/labmate_view.c` | `fb94bff13e95968406a8629c755c810787583f0b` |
| `src/labmate_ui_screens.c` | `f99c11e87a979a3257d49f30d84f7a53150d2398` |
| `src/labmate_ui_primitives.c` | `81b00e440ebba508b3f73d7b075e51b273bbbf82` |
| `src/labmate_scope_ui.h` | `ed7379c877c541228f0395710091680b7276d800` |
| `src/labmate_scope_display.c` | `2b57ba967f06052a8df79700c81434c5d5cd86a3` |
| `src/labmate_scope_pair_view.c` | `9f321a172a1504b254afba8cee029e93a7ac5f7a` |
| `src/labmate_scope_reference_view.c` | `e99740cec7dd2413149a9019eb624fb85ef2f6ee` |
| `src/labmate_scope_bridge.c` | `039ec8be0e407af8a077d8f3ca2c219b4240dbd5` |
| `src/labmate_input.c` | `e2ad9282a8807255f18c660f24c5580ce57c90fe` |
| `src/labmate_input_menu.c` | `b0ec8a335af27bc8cf7016a80fc157cb57890418` |
| `src/labmate_uart_ui.c` | `23c256f3cef5ca8cafdae5fcb80243f121003841` |
| `src/labmate_i2c_ui.c` | `162426ea56e82f1f5ba8c5202be2d703049ac445` |
| `src/labmate_onewire_ui.c` | `dfc632bf477eb858d6f5dcd9d1026fe416bd0213` |

## 7. Existing tests to inspect before any UI code change

Identified filenames in `tests/`: `test_labmate_ui_keylabels.c`, `test_labmate_scope_display.c`, `test_labmate_scope_pair_view.c`, `test_scope_reference_view.c`, `test_labmate_scope_navigation.c`, `test_navigation.c.inc`, `test_scope_exit_guard.c`, `test_scope_pc1_pin_gate.c`, `test_labmate_scope_focus.c`. **Their present test execution status has NOT been re-established.** A source/test file being present does not constitute a successful run.

## 8. NEXT gate: UI-01 / 128x64 geometry host validator

Before writing or claiming host test PASS:

1. Capture source and test blob pins; document exact available compiler flags and reproducible host compile/run command for the actual UI stubs.
2. Add test-only rectangle and text/glyph bounding checks for screen 128x64, title/status/footer nonoverlap, Scope viewport clipping, zero/invalid/overflow data, long values, confirmation/busy/STOP states and real control-to-label consistency.
3. Exercise all current 17 screen enum entries and the Scope pages; separately test menu groups and input event types. New Dashboard and Doctor remain **planned** and are not counted as existing views.
4. Run the host test under controlled toolchain; record exact command, output and exit status. A host PASS is not an E11 SDK build or a device PASS.
5. Review a small diff before changing any renderer. Do not modify IRQ, native lease/STOP, CRC Profile, CSV, release assets or firmware in this UI gate.

**Current conclusion:** UI-00 source-based screen/state inventory is recorded, but geometry safety, rendering completeness, and device UX acceptance are **PENDING**, not PASS.
