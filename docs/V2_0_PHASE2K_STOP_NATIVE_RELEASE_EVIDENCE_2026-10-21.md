# LabMate Ultimate v2.0 — Phase 2K native lease release truth and STOP/BACK

**Date:** 2026-10-21  
**Development:** `dev/v2.0-signal-doctor`, Draft/Open PR #21 → `dev/v1.9-logic-scope`.  
**Acceptance:** **source-verified isolated host PASS; full-repository workflow, pinned E11 SDK/FAP and real device PENDING**. Stable, firmware and microSD remain untouched.

## 1. Safety defect: advertised free owner before lease return

In the E11 native source review, Frequency LOW PC1, Pulse EXTI and Button PC1 STOP handlers were clearing their software owner **before** inspecting `furi_hal_resource_lease_release(...)`. TIM2 Frequency HIGH and Counter could also clear ownership despite a pending native TIM2 claim or unsafe stop.

This matters because a detached callback / cleared `active` flag does **not** prove the E11 firmware has returned its resource lease. Advertising `LabMateCaptureNone` with a stale handle risks a misleading free state even when new capture is blocked by a sticky fault.

### Narrow source correction

- `src/labmate_frequency_capture.c`: Frequency LOW PC1 only clears its owner and pin after a **true** lease-release result. On failure it retains the opaque handle and previous owner and marks release fault/block. Frequency HIGH PB3/TIM2 does not clear owner if `labmate_frequency_tim2_lease_pending()` is true.
- `src/labmate_pulse_capture.c`: Pulse EXTI owner/pin is cleared only following successful lease release. Failed returns retain handle/mask and software owner with a sticky fault.
- `src/labmate_button_capture.c`: Button Analyzer PC1 behaves the same way; adds a read-only `labmate_button_lease_pending()`.
- `src/labmate_event_counter.c`: Counter only clears PB3/TIM2 owner if native capture was healthy, no lease remains and no sticky release fault was raised.
- Native PC1/Pulse status helpers expose **read-only** pending-handle booleans. The underlying E11 HAL lease acquire/release APIs and ISR implementations remain unchanged.
- `src/labmate_capture_release_gate.h`: pure-C, fail-closed policy requires Scope STOP confirmation, all five capture engines inactive, **all four native handle groups** (LOW PC1 / TIM2 / Pulse / Button PC1) cleared, and no sticky fault.
- `src/labmate_capture_session.c`: final `labmate_capture_stop_all()` now calls this policy after all five STOP attempts; only on confirmed success does it set `capture_owner=LabMateCaptureNone` and `capture_blocked=false`.

**Limitations:** These are app-side release-result and retained-handle checks, not direct probing of EXTI electrical state or proof every other Momentum firmware owner cooperates with the E11 lease API. Scope uses its existing independently verified `labmate_scope_native_stop_confirmed` gate.

## 2. Exact GitHub source identities

| Reviewed artifact | Git blob SHA |
|---|---|
| `src/labmate_capture_release_gate.h` | `49a35cd13f9b1f82bf11c25b651b403076634ef0` |
| `src/labmate_capture_session.c` | `c4ad822f12998b4d4a787ae89511b0519f10735c` |
| `src/labmate_frequency_capture.c` | `4ad010a3d7b06cc176d736571d399cd149adf080` |
| `src/labmate_pulse_capture.c` | `2a4691914071f5a8e1f8e038fe43438f14a4d8ec` |
| `src/labmate_button_capture.c` | `8adb206d9f137b40a9a64c7e26faba6993a1c9c2` |
| `src/labmate_event_counter.c` | `00455cf9fd3d9a7ef7bdee96f988b1114d3674e2` |
| `tests/test_v20_phase2k_release.c` | `29c99ce4643bdd82d567c686f458a5937cfc5831` |
| `tests/test_v20_phase2k_native_stop.c` | `fd15e10ec84200f136020d0dce5485873211bc23` |
| `tests/test_v20_phase2k_button_counter.c` | `c4b81c3c15be11e1d567ed670fa0190710f4f5a0` |
| `tests/test_v20_phase2k_stop_all.c` | `6a67fd3cbd20fd051e1a36c5ecb15bd396b07235` |
| `scripts/test-v20-phase2k-host.sh` | `014fb45331dc2e1dbeab0f6caa8af38fc19cb2c8` |

The four new pure-C test fixtures and release policy header were checked using local `git hash-object` against the exact GitHub readback. In the native STOP mock suites, the function bodies were copied byte-for-byte from the corresponding current GitHub production source and checked by CRC32:

| Exact production function | Characters | CRC32 |
|---|---:|---|
| Frequency HIGH stop | 903 | `78d05a9b` |
| Frequency LOW stop | 1449 | `cefde2eb` |
| Pulse stop | 1491 | `4f8e2703` |
| Counter stop | 1546 | `2e78cf0f` |
| Button stop | 1274 | `5df63798` |
| All-capture stop | 1789 | `b932be20` |

## 3. Tests ACTUALLY executed locally

Isolated Linux GCC and Clang each built with C11, `-Wall -Wextra -Werror -pedantic -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer`. On **both** compilers the following actual executions exited 0:

```text
Phase2K native-lease release gate PASS: 2048 reports, only 1 fully released
Phase2K extracted native STOP functions PASS: 9 success/failure/empty-handle cases
Phase2K extracted Button/Counter STOP PASS: 6 release scenarios
Phase2K extracted STOP-all integration PASS: 10 scope/capture/lease scenarios
```

The 2,048-state truth table checks every combination of Scope stop, five active capture engines, four native lease groups, and a sticky fault. It accepts exactly one completely released configuration.

The **six extracted production STOP functions** were executed with deliberate firmware release successes/failures, missing handles, suspect TIM2 clock and clean Scope exit to check retained owner and blocked/fault status. In total **2,073** host cases per compiler. Mock HAL functions simulate release outcome and callback removal; they **cannot** attest the real firmware backend.

Earlier exact-source fixtures for Phase 2I PB3/TIM2 (1,038 groups per compiler) and Phase 2J Pulse pairs (1,171 scenarios per compiler) were re-run locally with GCC/Clang and sanitizers, both passing. Those are independently tested source subsets, **not the full current PR checkout**.

## 4. Reproducibility, CI and NO-GO

The committed read-only runner uses `awk` to extract the **current production STOP functions** at execution time, checks call-site ordering, builds the complete local release policy test and the three source-linked mocked native STOP executables:

```sh
sh scripts/test-v20-phase2k-host.sh
```

The read-only `.github/workflows/v20-ui-host-gates.yml` has a new Phase 2K job step and path filters for all involved source and test files. **GitHub Actions reports zero runs** on the development branch: there is no successful remote CI run to certify. The repository's full host scripts also have **not** been executed together from a complete checked-out repo in this environment (outbound github.com DNS inaccessible).

**Pinned E11 SDK, ufbt, firmware ABI, FAP integration, real STOP/BACK and PA7→PC1 hardware tests were not available in the local runtime.** These cannot be marked PASS and the user has not authorized any device/SD writes. Any future E11 build must be read-only on the host and any device installation separately approved.

**Decision:** Phase 2K exact-source host lease-release gate **PASS**. Full CI, E11 integration/physical metrology and v2.0 Stable **NO-GO**.
