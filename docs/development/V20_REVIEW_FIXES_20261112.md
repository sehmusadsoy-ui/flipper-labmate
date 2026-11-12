# v2.0 review fixes — 2026-11-12

Source-only changes on top of `audit/software-fixes-20261107` (`a3822fe`).
Not compiled against the E11 SDK and not run on a device from this branch.

| # | Problem | Fix |
|---|---|---|
| 1 | Signal Doctor opened with Source already in edit mode (or the help panel on a long OK): the menu opens it on OK Press, the screen reads Short/Long of the same press. | One-shot entry guard in `labmate_input_filter.c`, armed only on the Menu→Doctor OK transition. |
| 2 | Spurious "No signal" in Frequency LOW/PC1 and Pulse: the ISR could stamp a tick newer than the `now` read at function entry, so `now - last` wrapped and looked like a 3 s silence. | Read the kernel tick after the ISR timestamp snapshot (`labmate_measurements.c`). |
| 3 | PB3 input above ~4.29 MHz (uint32 millihertz) showed "No signal". | `frequency_over_range` state; Frequency shows "Over range". No value is published or logged. |
| 4 | "Drifting" stayed latched after any earlier frequency change because it used session Min/Max. | Stable/Drifting uses a ~3 s ring of recent valid readings; Min/Max unchanged. |
| 5 | No hold-to-repeat: Alerts limits needed thousands of presses. | Repeat admitted for value editors only (Alerts Up/Down, PWM custom-edit Left/Right, Doctor edit Up/Down) with 1×/10×/100×/1000× acceleration in Alerts. Navigation, pin changes, RUN/STOP and confirmations never repeat. |

`labmate_input.c`, `labmate_input_menu.c` and the capture drivers are
byte-identical to the frozen baseline. `draw_frequency` differs only by the
two state-text changes that `scripts/audit-v20-e11-ui-completion.py` now
permits explicitly; geometry and draw calls are unchanged.

## Verification

- `sh scripts/test-v20-e11-final-ui-predevice-host.sh`: PASS locally with GCC
  only (Clang sanitizer runtime was unavailable on the review machine).
- `tests/test_threshold.c.inc` covers scaled limit steps; `tests/test_v20_ui05d_pixel.c`
  covers Over range and recent-window Stable/Drifting (291 frequency cases).
- Pending: native E11 build in CI (GCC + Clang), and on-device checks of all
  five items.

## Follow-up (same day): alert notification and Turkish UI

- **Threshold Alerts** now announce a new latch once with two short
  vibration + beep pulses and the red LED (`labmate.c`, notification service;
  the user's system sound/vibro settings apply). Trip logic is unchanged.
- **Turkish UI**: Settings → Language switches English/Türkçe and persists in
  the existing `ui_prefs` record (language byte 1). `labmate_i18n.c` swaps
  English UI literals for entries in `labmate_i18n_table.h` (429 strings)
  and draws ç ğ ı ö ş ü İ procedurally on top of the ASCII-only fonts.
  Renderers and their geometry are untouched; UI sources only gain one
  trailing `#include "labmate_i18n.h"`.
- Translations wider than the English text were shortened or left in
  English so that no label can overflow its approved box. Formatted strings
  (values with units) and a few long legacy ALL-CAPS lines stay English.
- Verified on host only: acceptance runner PASS (GCC), plus a throwaway
  raster test of the mark drawing with the real u8g2 font data. Not yet
  reviewed on the device screen.
