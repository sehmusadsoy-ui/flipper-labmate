# LabMate v2.0 — Phase3D-B native Frequency evidence adapter

**Development branch:** `dev/v2.0-signal-doctor`; Draft PR #21.  
**Source change:** Complete native app-thread LOW/PC1 and HIGH/PB3 Frequency capture evidence handoff wired to Signal Doctor.  
**Build status for THESE new edits:** **PENDING**. The prior owner's 111,540-byte Phase3C FAP hash is NOT this artifact. Main and published Stable versions untouched.

## Runtime contract (code review, not device proof)

- After successful native PC1 IRQ callback/lease or PB3 TIM2 configuration/enable, Frequency Analyzer only (not Logger) begins a monotonic app session with a source-specific pin, timebase, and generation. A failed lease cannot initialize a valid capture.
- LOW/PC1: a consumed actual pending ISR mailbox publication is copied under `FURI_CRITICAL_ENTER/EXIT` along with real IRQ edge count/last IRQ tick; only the original native period calculation is admitted, not a smoothed or HOLD display number. Coalesced or exhausted mailbox, stale period, clock and counter-wrap ambiguity reject.
- HIGH/PB3: the hook is placed INSIDE `labmate_high_gate_audit_record` successful publication path. Uses actual hardware counter, original native gate cycles and edge count; policy recomputes with the existing `labmate_high_gate_evaluate`. No 100ms poll or UI redraw creates a sample. Clock and counter-generation guards reject.
- App Frequency BACK: captures the last audited source state BEFORE existing `labmate_capture_stop_all`, then checks that IRQ/TIM2 is stopped, app ownership cleared, BOTH native E11 lease checks are false, no sticky release fault and no capture block BEFORE sealing. `labmate_evidence_session_finish`, `labmate_snapshot_bridge_from_capture`, and `labmate_dashboard_store_ingest` apply existing fail-closed evidence contracts.
- Frequency HOLD does NOT stop IRQ/TIM2; thus entering/exiting HOLD abandons and invalidates Doctor epoch/data. Changing PC1/PB3 source invalidates the old epoch; same-pin navigation does not unnecessarily discard it. A new genuine owned START is required to create another accepted epoch. Inactive, malformed or missing capture remains `NO DATA` / `INSUFFICIENT`; no fabricated `NO SIGNAL`.
- Source provenance gates remain a software safety proxy, not a physical promise that hardware delivered losslessly. Native E11 FAP compiler verification and real Flipper tests required.

## Acceptance / provenance

**Previously PASS:** Phase2L 22 suites, Phase3A and Phase3B, Phase3C owner's E11 SDK/FAP build (SHA-256 `7f56e9dad3fc3a20bedb25155d01c5e6c7ffa0812d348a0e89852ed4eb169ef4`).  
**New, pending:** Phase3D-A 34-case pure policy and Phase3D-B source-linked ordering audit on owner's full checkout, full GCC/Clang suite, new pinned E11 FAP compile/link/verifier, live 3.3V GPIO test and LCD rendering. GitHub Actions runs not observed.

**Repeatable no-flash owner command** from a fresh ZIP of this branch:

```bash
LABMATE_E11_WORK="$HOME/labmate-v20-phase3d-build-20261021" \
  bash scripts/build-v20-phase3b-e11-isolated.sh
```

The wrapper first runs every host suite and then copies the protected pinned SDK to a new isolated workspace. It does not flash/install/alter the original SDK. The script basename is historical; its final banner is now version-neutral.

**NO-GO:** v2.0 Stable, device writing, replacing older stable FAP or microSD content, claiming real hardware accuracy or universal native conflict freedom.
