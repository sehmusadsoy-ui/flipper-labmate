# LabMate v1.9 — Logic Scope UI rebuild

**Development implementation:** pinned source commit `72eb58d6c65d31f510acf6f532ee23c543a9149d`.
**Status:** Source and verification runner committed; **Windows native host build, real FAP and Flipper visual acceptance are pending**. Keep PR #15 draft and stable v1.8 unchanged.

## Design contract (Flipper Zero 128x64 monochrome)

- Persistent header: prominent title, page fraction, PC1.
- Waveform viewport only on page 1: x=2..125, y=15..42 **inside a full frame**; dotted 7-by-3 graticule plus border time ticks. Grid points are not calibrated voltage/time ticks. All HIGH/LOW transitions inside the viewport must originate from actual PC1 IRQ-copied edges. No fake pre-trigger trace.
- Page 1 compact status baseline y=51. Stop-only trusted metrics are shown as HOLD + frequency + duty when the IRQ/lease has been positively released, clock verified and matching generation latched. If not, use true current state and observed edge count. Do NOT reuse stale frequency while live or after unsuccessful capture.
- Page 2 A/B compare: only sequential actual PC1 captures, A/B frequency+duty plus B-minus-A frequency and duty deltas; never label the inputs as simultaneous channels.
- Page 3 A DETAIL or B DETAIL: FREQ, DUTY, mean actual HIGH, LOW, PERIOD over completed H-L-H cycles, and empty state if no validated snapshot.
- Page 4 REFERENCE: TARGET, FREQ, DUTY, RESULT; PASS/FAIL comes from exact existing full-mHz tolerance evaluation, not rounded LCD labels. Reject stale PASS after preset or measurement changes.
- Lower footer: standalone **parenthesized hardware-key labels**, e.g. (OK)Run, (OK)Stop, (v)Pg, (^)More, (^)Next, (^)Ref, (B)Exit. (B) is the Flipper's hardware BACK button. Each LCD text item has a bounded width, with centered status no longer underlined by the grid.
- Other preexisting LabMate tools' shared key instructions now use the same parenthesized key syntax when they call the existing shared primitives. Their actual button meanings and measurement code are preserved.
- No stored IDs reordered; About/Info stays last in the existing navigation. No changes to GPIO/TIM1/TIM2/EXTI IRQ handlers, UART, CSV, Profiles, SD files, old FAPs or firmware.

## Input map

| Mode | OK | DOWN | UP | LEFT / RIGHT | BACK |
|---|---|---|---|---|---|
| Scope idle | START | Compare | — | Save A/B if valid | Safe exit |
| Scope capture active | Safe STOP | Disabled | Disabled | Disabled | Safe stop/exit |
| Compare idle | START new capture (returns to Scope) | A Detail | A Detail if A saved | Save A/B if valid | Safe exit |
| A/B Details idle | START new capture (returns to Scope) | Reference | Switch A/B if B exists | Save A/B if valid | Safe exit |
| Reference idle | START new capture (returns to Scope) | Scope | Toggle 100Hz/1kHz preset | Disabled | Safe exit |

The native bridge retains strict owned callback/lease teardown and run generation protections; no forced abort on BACK if resource cleanup fails.

## Verification gates (do not falsely mark passed)

1. Exact Git object pins: 10 GUI/app source items and five native C tests checked against source commit.
2. Strict MSYS2 UCRT64 compiler flags: -std=c11 -Wall -Wextra -Werror -pedantic. Five real host binaries test Scope paint confinement/font collisions, A/B vs timing detail, reference PASS/FAIL and stale verdict, 13-edge real focus projection, and shared parenthesized key glyph bounds.
3. Before touching the isolated E11 SDK app source, verify original/source firmware git heads, old application.fam blob, all original UI source blobs, previous 99,376-byte FAP pinned SHA-256 and restore point. Only after five host PASS, back up the old 99,376-byte FAP on the **PC** with disk readback, then copy exactly ten new UI source files into isolated SDK (including new header).
4. Build **only** labmate.fap via native Windows fbt.cmd fap_labmate. Run existing strict E11 exported-API FAP checker, record new full SHA-256/size. No device COM, no install, no flash, no uninstall or firmware updater.
5. Only after Windows logs PASS and independent prewrite read-only checks, seek separate consent for FAP-only replacement. Never reuse a previous-version-pinned installation script. Recheck device/data backups before staging, preserve old active FAP and rollback slot.
6. On Flipper: visually inspect all four pages and fonts; no measured input => no trace or false PASS; PA7->PC1 internal 3.3V 100Hz/50% and 1kHz/50% real waveforms; check freeze/STOP, A/B save and detail, reference 100Hz/1kHz, STOP/BACK releases resources; regress PWM, Pulse, Frequency, Logger and Profiles.

**Installed E11 binary ABI remains not independently attested** even if the SDK app build links against its expected exports. No Stable publication before operator's physical GUI approval.
