# LabMate v2.0 — Phase 3E E11 real-device acceptance matrix (DRAFT)

**Scope:** v2.0 Signal Doctor native Pulse, Frequency LOW/PC1 and Frequency HIGH/PB3, using exact Phase3D reviewed **115104-byte** FAP.  
**Reference binary SHA-256:** `53afa54b70b77d53b5728ab915b10b278a25c3a21f6caf93eb261aa35a68b737`.  
**Status:** **PLAN ONLY — ZERO DEVICE WRITES AUTHORIZED.** Source compilation and ABI PASS != device behavior PASS.

## Independent installation approval gate

Do not install, flash or touch microSD until the user explicitly approves a **non-firmware FAP-only** trial, and existing E11 v1.8 Stable/DEV apps and PC backups, SD profile/CSV data, loader target and rollback path are independently checked. Firmware flash is **not** part of this plan. Any unexpected required firmware update is NO-GO. Compare the actual on-PC FAP SHA-256 to the pinned value before any new test. No automatic cleanup, no mass SD overwrite.

## Electrical and resource safety

- Flipper Zero GPIO is **3.3V digital only**; never attach 5V signals. Verify common ground for externally powered DUT.
- Known previous owner-tested PA7 PWM output → PC1 Frequency/Pulse loopback is a useful reference for 100 Hz/1 kHz. TIM1 PA7 generator is independent from PC1 EXTI; still verify denied ownership and STOP between tests. Power down before rewiring.
- PB3 TIM2 path requires verified safe 3.3V input wiring and no other peripheral owning PB3/TIM2; do not assume it is safely available until the owner confirms their hardware setup.
- If BUSY, HAL lease error, unexpected source switching, battery issues, crashes or app freeze occur: STOP and collect log; do not repeatedly retry or flash.

## Acceptance checklist (no results claimed)

| Test | Procedure / input | Expected | Status |
|---|---|---|---|
| T01 | Start app, navigate all root groups, confirm INFO/About remains last | No layout overlap, historical tool indices preserved, back navigation stable | PENDING |
| T02 | Open Doctor without setting frequency reference | `SET REF FIRST`; no default PASS/FAIL | PENDING |
| T03 | Set 100 Hz expected, 5% frequency tolerance; no capture performed | `NO SEALED DATA`; no synthetic diagnosis | PENDING |
| T04 | On PC1 Pulse, 100 Hz 50% PA7 loopback; do not STOP yet | Doctor cannot invent a sealed result from live UI/HOLD values | PENDING |
| T05 | Pulse STOP after >1 full complete pair; open Doctor, select PULSE and 100 Hz ref, 50% duty | Valid only if same capture generation, source edge audit, resource released. Expected IN RANGE subject to actual measurement | PENDING |
| T06 | Pulse STOP quickly without full paired edge sample | INSUFFICIENT / NO SEALED DATA; never guessed IN RANGE | PENDING |
| T07 | Pulse HOLD then new START and new STOP | prior generation cannot be replayed; fresh evidence only | PENDING |
| T08 | Pulse capture source pin switch PC1 → allowed alternative | old snapshot invalidated; IRQ/lease released before new arm | PENDING |
| T09 | Pulse while an independent service holds same EXTI/pin | BUSY/denial safe, no foreign pin/lease mutation | PENDING |
| T10 | PC1 Frequency LOW 100 Hz reference, native BACK/STOP | sealed Frequency snapshot only after real IRQ period, source proof and lease release | PENDING |
| T11 | PC1 Frequency LOW 1 kHz, nondefault expectation | comparable measured frequency and tolerance verdict, no Pulse duty claim | PENDING |
| T12 | PB3 TIM2 Frequency HIGH verified source, at chosen safe rate | true completed hardware gate and release evidence; no 100ms poll fake | PENDING |
| T13 | Frequency HOLD on PC1 or PB3 then BACK | no stale data replay; HOLD alone is NOT lease release | PENDING |
| T14 | No edges, disconnect, stale counter, bad timebase, unsupported pin | NO DATA/INSUFFICIENT/UNSAFE as applicable; no fabricated NO SIG | PENDING |
| T15 | Any STOP/BACK/reopen | no BUSY/ERR, GPIO callbacks + TIM2 released; prior Stable unaffected | PENDING |
| T16 | CSV/history/profiles and logger functionality smoke test | no unwanted writes or regressions to v1.8 features | PENDING |
| T17 | Explicit UI 128×64 check on both Doctor pages | text, selection, headings/footer legible and not clipped | PENDING |
| T18 | Confirm FAP-only rollback restores previous app without touching firmware or SD data | previous installed Stable resumes with saved data intact | PENDING |

All actual measurement observations must record pin, source, frequency, duty where supported, FAP hash, E11 firmware identity, STOP/BACK behavior, unexpected BUSY/ERR, and the comparison with a known reference. An absent sample is not a measurement PASS. A repeated crash, failed E11 release or user data mutation is an immediate NO-GO.

**Release decision:** v2.0 Stable remains NO-GO until the verified on-device matrix passes, each negative/denial path is observed where practical, and the UI and rollback checks are complete. Any deferred instrument/calibration acceptance must remain explicitly PENDING rather than silently waived.
