# LabMate v2.0 — Phase 3D-A Frequency LOW/HIGH admission policy

**Status:** Pure source validation gate implemented, NOT connected to production app capture or sealed Snapshot. No E11 native build for this new code has been reported.

### Source-linked design

- `LabMateDoctorFrequencyLowPC1`: only PC1, a fresh actual LOW IRQ mailbox publication, no mailbox overwrites or exhaust, valid native period, clock, non-wrapped 32-bit result; recomputes expected frequency with the existing LOW period-to-mHz conversion.
- `LabMateDoctorFrequencyHighPB3`: only PB3, a completed hardware TIM2 gate with observed edges; uses the actual tested `labmate_high_gate_evaluate` routine to independently reconstruct frequency, rejects partial windows, counter/clock ambiguities, and native audit exhaust.
- Common gates: correct exclusive live owner; HOLD and source clock faults rejected; same start/stop tick frequency and SystemCoreClock; positive ordered observation window at most 5 minutes; a native publication genuinely observed within 500 ms of STOP; no source mismatch; no claimed zero-frequency diagnosis.
- This policy **does not create any capture evidence**. An app-thread native adapter must still obtain coherent genuine counters/periods and publication times during the SAME capture epoch, avoid timer wraps, confirm native teardown, and call the existing evidence-session and snapshot bridge prior to storing a Doctor-visible reading. A completed Frequency HOLD alone DOES NOT release the native E11 lease; only an owned STOP/BACK or mode-switch teardown may seal it.
- No IRQ writes, HAL calls, Furi dependency, storage changes, firmware flash, GUI changes or device install.
- 34 deterministic positive/negative host cases were run with GCC and Clang with ASan/UBSan using the same source policy and a locally reconstructed frequency-gate signature/math from the repository. The repo runner `scripts/test-v20-phase3d-frequency-host.sh` additionally compiles with the REAL repository gate sources; full owner WSL run is PENDING.

**Next mandatory steps:** native app-thread capture proof, release gate, per-session generation, full host suites, E11 FAP, real-device validation. **v2.0 Stable remains NO-GO**.

**Phase3C E11 build evidence** is preserved separately at `docs/V2_0_PHASE3C_E11_WSL_FAP_BUILD_PASS_2026-10-21.md`.
