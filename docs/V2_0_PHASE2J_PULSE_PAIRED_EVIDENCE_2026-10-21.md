# LabMate Ultimate v2.0 — Phase 2J Pulse paired phase-window provenance

**Date:** 2026-10-21  
**Development:** `dev/v2.0-signal-doctor` → Draft PR #21, base `dev/v1.9-logic-scope`.  
**Result:** Native Pulse publication accounting added; exact production-header host tests **PASS** on GCC and Clang, AddressSanitizer + UndefinedBehaviorSanitizer enabled. Full native E11 SDK/FAP and physical Flipper validation **PENDING**. No installed device, firmware, Stable FAP, CSV, or Profiles changed.

## 1. Source finding: independent normal phase windows are NOT the same individual waveform cycle

The real E11 `src/labmate_pulse_capture.c` has three Pulse update modes:

1. **Normal fast phases:** separate averaging of 16 completed HIGH widths and 16 completed LOW widths. The phase-valid flags may be set independently.
2. **Very short phases:** two simultaneous 128-HIGH / 128-LOW averages when the wide averaging window completes. HIGH and LOW become valid together.
3. **Long phase / extreme duty:** a direct per-transition period width for the long half plus an independent averaging window on the short half.

Consequently, `pulse_irq_high_valid && pulse_irq_low_valid` **does not prove that both values are fresh**. In particular, it cannot certify two phases belong to one *individual physical period*. We must not invent a physical cycle count or use the display's previous period as a new Dashboard acquisition.

The existing app-thread `measurement_update()` copies HIGH/LOW/edge count and validity within `FURI_CRITICAL_ENTER/EXIT`. The GPIO, EXTI lease, 16/128 averaging arithmetic, timeout, UI display, existing pulse statistics, IRQ callback ordering, and STOP/BACK resource release were preserved.

## 2. Implementation — fresh-half paired publication audit

The new pure-C `src/labmate_pulse_pair_audit.h` adds two distinct structures:

- `LabMatePulsePairAudit`: IRQ-written count of **paired phase-update events** and stored matching HIGH/LOW values, raw cumulative IRQ-edge count, fresh-HIGH/fresh-LOW flags, and sticky exhaustion.
- `LabMatePulsePairObservation`: a fixed-size app-thread **coherent copy** of the last successfully paired update, carrying the count, edge marker, HIGH/LOW widths and exhaustion status.

For each legitimate ISR phase update, the IRQ callback sets `new_high`/`new_low`. Only after **both sides have received a genuinely new completed update since the previous pair** may the audit increment. For simultaneous 128/128 publication, both freshness flags are set in the same IRQ completion. A normal 16/16 update can be paired after two separate completions. Partial phase evidence is discarded at short-/wide-window mode changes and at the existing stale-signal reset, **without rolling back the publication counter**.

Incorrect/overflowing HIGH+LOW arithmetic, zero phase, wrapped/repeated hardware edge counter, or overflowing pair count makes this session's audit permanently exhausted. A new capture start resets it **only after the native EXTI callback and E11 lease are acquired and callback delivery disabled**, before callback enable. Failed acquisition/HOLD/UI repaint cannot reset the count or mask a fault.

The per-interrupt audit call is skipped for edges that did **not** complete either averaged phase, reducing overhead for the 10 kHz signal use case (~20,000 IRQs/s).

The app-thread reader copies the audit together with existing HIGH/LOW counters **within its current IRQ critical section**. This auxiliary publication observation is not yet consumed by Dashboard or the Phase 2B Snapshot bridge; in particular, a pair count is not an independent physical completed-period count. **No new on-device tool/menu was exposed**.

## 3. GitHub source identity

| Artifact | Git blob SHA |
|---|---|
| `src/labmate_pulse_pair_audit.h` | `ed7ce88885e26db63b1cd4d0330e0fb2a69908cb` |
| `src/labmate_internal.h` | `b0ee45cef0ada7842426c00be198389c5fd6e0fd` |
| `src/labmate_pulse_capture.c` | `d49cd90c7c7387b6561016ff4eb042320750c98e` |
| `src/labmate_measurements.c` | `b45c4b163dad81ec6fccef0e7c8a081e44dac94d` |
| `tests/test_v20_phase2j_pulse_pairs.c` | `ade7948e1f9de35433aa40e25905bcf1b95a88a0` |
| `scripts/test-v20-phase2j-host.sh` | `1c800ecf811615fda374008c065fbd8b83a55cd0` |

The exact pure-C production header and the test fixture were created in the isolated host filesystem, then independently `git hash-object`-matched against connected GitHub source. The real native ISR and app-thread call sites were read back from GitHub and inspected separately; the complete native `pulse_capture.c` translation unit was **not** host-compiled against Flipper HAL.

## 4. Actual host verification

GCC 14.2 and Clang 17.0 compiled and ran the **exact GitHub** `labmate_pulse_pair_audit.h` + `test_v20_phase2j_pulse_pairs.c` with strict C11, `-Wall -Wextra -Werror -pedantic -O1 -g`, `-fsanitize=address,undefined` and `-fno-omit-frame-pointer`. Both exited 0:

```text
Phase2J Pulse paired HIGH/LOW evidence PASS: 1171 scenarios
Phase2J Pulse paired HIGH/LOW evidence PASS: 1171 scenarios
```

Coverage: NULL/missing-copy safety, separate 16/16 updates, same-event 128/128 update, new LOW with stale HIGH, repeated old validity flags, partial-window discard on mode change/stale signal, invalid phase status/zero width/64-bit overflow, repeated/wrapped edge count, UINT32_MAX publication exhaustion and **1,024 sequential paired long-pulse updates**.

A source-linked whole-repository runner was committed:

```sh
sh scripts/test-v20-phase2j-host.sh
```

It examines the actual `LabMateApp` fields, native single-pair-note and reset call sites, app-thread critical-copy call, stale reset and native start order; it then compiles the pure production module with GCC and Clang. `.github/workflows/v20-ui-host-gates.yml` also now triggers on the new files and Pulse native code, and invokes the Phase 2J script.

**Important acceptance limitations:** This full checked-out-repository runner has not been independently executed against an entire repo checkout; GitHub Actions has not shown a successful workflow run, and no pinned E11 SDK/FAP compilation or Flipper hardware test was performed. Source-grep assertions and a pure-header C test are **not** firmware integration proof.

## 5. Next safe gate

1. Verify the full repo CI script suite and E11 SDK build/ABI.
2. Prove native Pulse session generation and a real IRQ-resource teardown result, including sticky release-fault, before a Snapshot may gain `ownership_released=true`.
3. Define quality mapping for missed physical edges and stale paired phase updates; remember pair freshness is **not same-cycle coherence**.
4. Only then wire real Frequency/Pulse producer facts to Dashboard, followed by Flipper physical 100 Hz/1 kHz loopback tests. Preserve v1.8 normal Stable, v1.9 E11 Stable and all original microSD/Profiles data.

**Phase 2J: source-header host PASS. On-device integration and v2.0 Stable: NO-GO.**
