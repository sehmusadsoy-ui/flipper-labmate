# LabMate v1.8 UART — Development Integration Acceptance

**Decision date:** 2026-10-13  
**Scope:** accept the UART Terminal **minimum useful communication milestone** into the ongoing v1.8 development baseline after PR #7 review. **Not** a v1.8 Stable or RC release, measurement certification, complete feature-specification signoff, or claim that every deferred physical test is PASS.

## Verified evidence and exact build provenance

- Original local Flipper USART loopback U1–U8: **8/8 PASS, operator reported** (9600/38400/115200, transitions and selected regressions).
- External official ESP32-S2-WROVER devboard E1–E6: **6/6 operator-reported PASS**, including UART 115200/9600 8N1, visible `ESP32_READY`, explicit `AT\r\n` TX and conditional `ESP32_OK` RX.
- SR1-R1: STOP/BACK/re-entry preserves 9600 baud, two-minute RX **device PASS**.
- Deliberate baud mismatch: clean-baseline `E:0 → E:88`, fresh-session 9600 re-entry recovery **operator-reported PASS**.
- ST2 at 115200: two bounded, explicitly triggered ESP32 stress events; cumulative R = **20569** then **41281**, final D = **0**, E = **0**, responsive GUI and STOP/BACK; **PASS for bounded sustained receive**, **not for physical DROP**.
- Controlled USART resource ownership: standalone `labmate_busydiag.fap` real-Flipper-HAL **BUSY REFUSAL PASS** and **RESTART/STOP PASS**, operator-reported. The test reserves the USART handle within the standalone diagnostic, **not** by an unrelated concurrent service.
- SBR1 same-screen STOP → baud change → re-RUN recovery **operator-reported functional PASS**. The operator replied **"hepsi passs"** for the prescribed sequence without supplying numeric post-test R/D/E snapshots; do **not** invent numeric SBR1 results.
- Corrected UART source `db5392119f84f48ca7391ce8dbab11895d82437c`, final host-test source `12977d2dd4dfa661a790e3d8ce9dc5d73258d8e4`. GitHub Actions [38434053595](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38434053595) **build PASS + Windows installer safety PASS**, publishing job SKIP. Exact user-installed FAP SHA256 `f3ce6438280524692908212c0b3c8b4c9a830b7afc467b503aab667d2e7f12d2`; USB port COM7, 9/9 chunks transferred, app launched. Following this successful source CI run, only documentation changed on the PR branch before acceptance.

## Explicitly accepted limitations, **not hardware PASS**

1. **Physical queue DROP/overflow `D>0` remains untested**. Production-code host-HAL fixture forces 320 bytes into a 256-byte queue and correctly registers 64 drops; the physical ST2 traffic did **not** overflow. Queue is bounded and the ISR is nonblocking; do not intentionally generate unsafe/unbounded traffic merely to force a positive DROP counter. Reassess if a real-world overflow problem is reported or calibrated test equipment becomes available.
2. **Independent serial timing, full 128×64 pixel-level readability, long endurance, and third-party simultaneous serial-owner contention** have not been independently instrumented/verified.
3. **Minimal UART UI**: printable ASCII screen with replacement dots for nonprintables, display-capped R/D/E, STOP-only 9600/38400/115200 selector, up to 12-character TX text and fixed CRLF; no dedicated HEX terminal, PAUSE-with-capture, arbitrary/free-text editor, configurable TX newline, protocol decode or PC bridge. These are **not implemented** and may be separately scoped later.
4. 38400 baud was exercised in the **Flipper local loopback**, not verified as an independent external-peer 38400 timing calibration.
5. The ERR indicator can persist during the same session after STOP alone; SBR1 intentionally resets counters/text **when baud is changed while STOP**, preserving the TX command. This is a session UI policy, not proof that prior line errors physically disappear.

## Merge and release boundaries

- **Accept for integration into the v1.8 development `main` branch** if PR #7 is mergeable, CI has passed at the exact production-code snapshot, and source/tag/release protection remains intact.
- This is a documented **risk acceptance for the minimal UART milestone**, not a claim of complete original UART aspirational scope.
- **Never mutate published v1.7 Stable** tag/release or previous Stable artifacts. Do not release v1.8 from this PR.
- Continue v1.8 with a **separate I²C Explorer feature branch** and distinct hardware/SDK pin and resource gate before writing or energizing GPIO.
- Keep detailed trace at [UART ESP32 physical test log](V1_8_UART_ESP32_TEST.md) and [UART acceptance/test plan](V1_8_UART_PLAN.md). Future UART enhancements and true instrumented validation should have their own test evidence.

## Actual integration result (2026-10-13)

- [PR #7](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/7) was marked ready and merged into development `main` with merge commit `6dbea4c9c6909c111b6f6b7600c548347dc13b14` after the gates above were reviewed.
- The physical queue DROP condition `D>0` remains **unverified**, not upgraded to PASS by merge. SBR1 and external UART functional results remain user-reported.
- Development then moved to an isolated **I²C Explorer** Draft PR #8, with no v1.8 Stable/RC publication or change to the existing v1.7 Stable release.
