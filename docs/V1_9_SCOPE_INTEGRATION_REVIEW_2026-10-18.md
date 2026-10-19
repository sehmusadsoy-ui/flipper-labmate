# LabMate v1.9 — PC1 Logic Scope integration review (2026-10-18)

Status: **SOURCE REVIEW / NOT PHYSICAL ACCEPTANCE**. This is a scoped review of the current `dev/v1.9-logic-scope` branch; it is neither a firmware flash authorization nor a v1.9 release.

## Verified in source on this branch

- `application.fam` declares experimental v1.9; `src/labmate.c` allocates/initializes a Scope state and polls the Scope screen.
- `src/labmate_scope_bridge.c` routes START/STOP/BACK, drives UI display state, and records A/B metrics only after native capture teardown. 
- `src/labmate_scope_native.c` gates native capture behind `FURI_HAL_RESOURCE_LEASE_API_V1` and `FURI_HAL_GPIO_HAS_TRY_ADD_INT_CALLBACK`. On absent matching APIs, START returns unsupported instead of falling back to asserting stock callbacks.
- PC1 EXTI1 native driver uses a resource lease plus try-add callback before GPIO/EXTI reconfiguration; interrupt callback reads DWT cycles and GPIO state, with no storage/UI work.
- A bounded 256-edge in-app capture buffer and a time guard are present. The target remains *single-channel digital*, not an analog scope.

These are **code observations only**. Neither CI status nor real native coexistence/measurement accuracy was independently established by this review.

## Integration gate before any install or v1.9 release

| ID | Required validation | Status |
| --- | --- | --- |
| LS-01 | Exact E11 patched native ABI symbols, SDK pin and reproducible FAP build | NOT VERIFIED IN THIS REVIEW |
| LS-02 | Host tests: 0/1/2 edges, repeated levels, wraparound, buffer-full, dropped-edge flags | INITIAL HOST CASES ADDED; CI RESULT UNVERIFIED; full matrix remains open |
| LS-03 | Trigger/quiet/wall-duration and delayed (>100ms) polling watchdog, including tick-to-ms conversion | TRIGGER/QUIET/POLL-GAP/WRAP CASES ADDED; wall-duration/native conversion still open; CI result unverified |
| LS-04 | START refusal under existing PC1 native callback/lease **without changing foreign registers**, and lease-release failure stickiness | PURE C PC1/OWNER TESTS ADDED; real HAL register and callback isolation not yet verified |
| LS-05 | STOP/BACK/restart during ARMED, RUNNING, FULL, error and clock-unsafe states; verify no own IRQ/lease remains | NOT VERIFIED IN THIS REVIEW |
| LS-06 | A/B pair metrics: require complete distinct captures; invalid/no signal/overflow must never report an idealized PASS | TRUNCATION FAIL-CLOSED FIX + HOST REGRESSION ADDED; exact CI/FAP/physical acceptance still open |
| LS-07 | Peak IRQ load, RAM/stack usage and 128×64 rendering responsiveness under high edge rate | NOT VERIFIED IN THIS REVIEW |
| LS-08 | 3.3V independent signal generator and independent analyzer/scope, plus native foreign-service contention | DEFERRED PHYSICAL TEST |
| LS-09 | Existing UART/PWM/Counter/Button/Logger/Profile navigation and legacy data regression | NOT VERIFIED FOR V1.9 |
| LS-10 | Exact FAP SHA256, backed-up SD/firmware, tested FAP-only recovery and separately classified full-firmware recovery | NOT VERIFIED FOR V1.9 |

## Source-level review observations

1. The header comment in `src/labmate_scope_native.h` still says the driver is not connected to the menu, whereas `src/labmate.c` already shows Scope integration. Treat such historical comments as stale, not evidence of disabled code.
2. `src/labmate_scope_bridge_refresh` reads a bounded live sample snapshot; full metrics are latched only when no native IRQ or lease is active. Validate this distinction with host tests before changing UI semantics.
3. The code checks the kernel tick frequency before millisecond conversion, and rejects certain late/unsafe clock states. Verify timer wrap, long UI stalls and watchdog behavior against actual patched firmware.
4. Do not merge E11 Draft PR #13 wholesale into `main`, modify historical tags or update installed devices as part of this review.

## Next controlled implementation step

Run and inspect the newly added host regression CI; extend the uncovered metrics/owner/native ABI tests and then inspect build logs before any FAP change. Record exact test commands and commit SHA. Only after that, assess an explicitly approved, backup-protected physical test on the matched E11 device.

Canonical scope stays: v1.9 **Logic Scope + Signal Compare**, then v2.0 **Signal Doctor + unified dashboard**. Existing Stable v1.8 and compatibility-limited E11 prerelease are preserved.

## Implementation update — 2026-10-18

- Explicit PC1-only input validation strengthened at the pure resource gate. The underlying capture policy already restricts the Scope owner to PC1; this is a second fail-closed check, **not** proof that a different pin previously reconfigured hardware.
- Added `tests/test_scope_pc1_pin_gate.c` for allowed/denied GPIO, unavailable ABI, conflicting local owner, fault status and sticky lease-release retry.
- Added `tests/test_scope_buffer_timeguard.c` for trigger filtering, short 32-bit wrap, invalid interval, 256-edge capacity/drop, no-trigger/quiet timeout, late poll and millisecond wrap.
- Added `.github/workflows/v19-scope-host.yml` on the dev branch to compile and execute both tests on branch pushes with strict compiler warnings. This workflow is **host only**: no Flipper firmware flashing, FAP publishing, personal data or GPIO access.
- Commits: `eae6bbd` gate, `f171d80` initial PC1 regression, `7a9e27b` buffer/timeguard suite, `7e12fef` workflow, `9954701` ownership retry test.
- **Execution status:** workflow source and tests exist, but no authenticated run/job PASS log was retrieved in this session. Treat outcomes as **UNVERIFIED**, never as CI PASS.

## Signal Compare follow-up — 2026-10-18

**Source defect fixed:** `scope_bridge_latch` marked an overflow/dropped-edge capture as `truncated` while still allowing `scope_last_valid`. The pure A/B pair validator and comparison engine also accepted such metrics. A sample containing unobserved transitions must not be used as a trustworthy full-capture comparison.

- `src/labmate_scope_bridge.c`: latches `last_valid` only for READY **and not truncated**.
- `src/labmate_scope_pair.c`: refuses saving A/B from truncated measurements.
- `src/labmate_scope_compare.c`: independent comparison API refuses truncated A or B.
- `tests/test_scope_compare_pair.c`: covers two genuinely observed 1kHz waves with different duty (50.0% vs 45.0%), insufficient/invalid input, A/B generation monotonicity, and overflow-marked A/B rejection.
- `.github/workflows/v19-scope-host.yml`: added the third host test executable.
- Relevant commits: `15de604`, `3035467`, `4ec7796`, `a2439f2`, `09b788f`.

**Evidence correction:** No reproducible local GCC execution log for the exact repository sources is available in the reviewed evidence. An earlier note describing a reconstructed implementation as local PASS is **not acceptable as verified evidence** and is superseded here. Host test code is committed, but exact checkout/CI execution and native FAP/device acceptance remain UNVERIFIED until genuine logs are inspected.

## Measured tolerance reference module — 2026-10-18

A new **pure C, UI-independent** starting point toward the required v1.9 named reference and tolerance feature is on the development branch:

- `src/labmate_scope_tolerance.h/.c`: sample presets `100Hz 50%` and `1kHz 50%`, illustrative ±1% frequency and ±2 percentage-point duty tolerances; custom caller-supplied numeric limits are supported by the reference struct. These are reference specifications, **not measured signal truth or accuracy claims**.
- Verdicts are `PASS`, `OUT_OF_TOLERANCE`, `NO_SIGNAL`, `INVALID` and `BUSY`. Only capture-complete READY metrics without dropped edges, with observed cycles, valid timebase and plausible fields can become PASS/OUT_OF_TOLERANCE.
- `NO_SIGNAL` requires the caller to explicitly classify a confirmed no-signal timeout. Zero edges alone, while still waiting for a signal, remain `INVALID`. A BUSY condition is not evaluated as a pass.
- `tests/test_scope_tolerance.c` exercises authentic synthetic H-L-H timestamp-derived 1kHz metrics, exact and exceeded numeric limits, null/stale references, truncated captures, unverified clock/zero-cycle metrics, BUSY and NO_SIGNAL differentiation.
- `.github/workflows/v19-scope-host.yml` builds and runs the tolerance module as a **fourth host test**. Commits `eff400b`, `48c6174`, `15ff321`, `9e4bee9`.
- **Acceptance scope:** source files and CI configuration committed; exact GitHub runner logs/green result were not available through the readback tools. No v1.9 FAP, UI integration, ABI compatibility or physical device results are claimed.

**Next gate:** inspect real CI job output and fix any compiler/runtime regressions, then connect this verified evaluator to the Flipper display via an explicitly reviewable change. Do not invent measured PASS screens or integrate demo-only output.

## Reference verdict page integration — 2026-10-18

The pure-C reference comparator is now **connected in development source** to an additional read-only Scope LCD page. This is NOT a device acceptance or a published v1.9 FAP.

- `src/labmate_scope_reference_view.[ch]` renders the selected named preset, `PASS / OUT OF TOLERANCE / NO SIGNAL / INVALID / BUSY`, and measured Hz/duty only for complete, non-truncated, validated captures. The verdict uses full mHz precision; LCD display rounds/truncates for readability.
- Existing app view and input coordinator now offer `DOWN` cycling `PLOT -> A/B -> REFERENCE -> PLOT` when stopped, and `UP` to toggle `100Hz 50%` / `1kHz 50%` on the reference page. `BACK` retains existing safe STOP + return logic. Starting new capture resets the page to PLOT without changing the selected reference.
- The reference view cannot independently acquire GPIO/IRQ, and app UI computes a comparison only after a matching completed capture generation, no active native owner/lease and no clock fault. `NO SIGNAL` is shown only after the native no-trigger timeout with zero captured edges. `BUSY` is not shown as a measurement.
- Existing A/B and waveform screens remain available; neither SD Profile nor Logger CSV format was modified.
- Added `tests/host_stubs/gui/gui.h` and `tests/test_scope_reference_view.c` for a fake Canvas test of read-only PASS/INVALID/NO SIGNAL/BUSY rendering and denial of a PASS without validated metrics. Included as fifth host test in `.github/workflows/v19-scope-host.yml`.
- The new reference presets are initial fixed examples. An on-device editor for custom tolerances is **NOT implemented**; the pure comparator accepts caller-provided reference values, but UI currently offers only the two named presets. Do not claim full user-configurable v1.9 controls are shipped.

**GitHub evidence:** committed branch files were read back. Native Flipper SDK compilation, CI green logs, on-device UI pixels/controls, independent waveform truth, real firmware-wide BUSY and STOP/RESTART are **NOT VERIFIED**. The connected GitHub Actions tool used here did not expose push-run logs; empty commit-status or PR-run lists do not establish CI PASS/FAIL. Work must remain in `dev/v1.9-logic-scope` until these gates are separately checked.

### Next manual physical acceptance (only after confirmed matched E11 FAP build and backup)

1. Without starting capture, go to reference page: it must say INVALID/WAIT, **not** PASS or NO SIGNAL.
2. With known-safe 3.3 V signal, capture 100 Hz / 50% using the already validated PA7->PC1 loopback. STOP, choose the 100 Hz preset on the reference page; this is a **functional loopback check**, not independent calibration.
3. Compare against the wrong 1 kHz preset; verdict must be OUT OF TOLERANCE (given a completed valid capture), never false PASS.
4. With PC1 disconnected and safe input state, start and allow no-trigger timeout; expect NO SIGNAL only on confirmed no-edge timeout, not before START.
5. Check 1-2 observed edge cases, full/overflow and resource-denied BUSY; they must never be marked PASS.
6. Check DOWN/UP/BACK and STOP/RESTART, UART/PWM/Logger/Profile regressions and all owned IRQ/lease cleanup. Inspect result on actual 128x64 LCD.
7. Do not install the FAP or flash firmware before exact SDK/ABI, backup and explicitly approved installation scope are verified. External scope measurements remain with the instructor at the university.

## Final-exit IRQ lifetime hardening — 2026-10-18

**Source safety finding:** The original app coordinator always called `free(app)` on final exit even if `labmate_capture_stop_all` reported unresolved Scope native callback/lease ownership. The Scope IRQ callback receives a pointer into the heap-owned `LabMateApp.scope_native`; unconditional reclamation can risk a dangling IRQ context if native teardown is incomplete.

**Development-only remediation:**

- `src/labmate_scope_exit_guard.[ch]` defines a pure-C fail-closed predicate. Reclaiming the Scope heap requires an initialized session with inactive capture/IRQ, zero native lease handle, idle owner phase and fault-cleanup phase, cleared teardown bookkeeping flags, and no sticky native fault.
- `src/labmate.c` applies this gate after ordinary cleanup but **before** `free(app)`. For uncertain teardown it disables only LabMate's own IRQ-processing flag within a critical section, logs the fault, and invokes `furi_crash("LabMate Scope IRQ cleanup fault")` to force the firmware's controlled crash/reboot path **without returning from the FAP entry point**. Merely retaining the heap and returning was unsafe because the native IRQ callback could then point at unloaded executable FAP code. This emergency path has NOT been physically fault-injected, and the crash/reboot is not a normal STOP/BACK recovery mechanism.
- `tests/test_scope_exit_guard.c` covers fresh and initialized sessions, active ISR, running capture, outstanding lease, interrupted release, sticky fault, stale callback/pin flags, and only-confirmed-clean exit. The sixth standalone host executable is wired into `.github/workflows/v19-scope-host.yml`.
- A **separate isolated Linux GCC/C11 smoke** reproduced the new predicate and assertions with a minimal structural native-header stub and passed using `-Wall -Wextra -Werror -pedantic`. This is **not an exact GitHub source checkout, full firmware SDK compile, GitHub Actions PASS or Flipper fault-injection result**. Connector readback confirmed the committed repository files exist.
- Physical/native fault injection must verify lease-release failure, retained-callback state, actual final-exit behavior, reboot path, and that no foreign GPIO/callback is modified. No deliberate fault injection should run on the user's only working firmware or production microSD.

The gate does **not** close LS-05/LS-08/LS-10 without an exact native build and measured firmware-level behavior. v1.8 Stable and the v1.8 E11 prerelease remain unchanged.

## Traceable host compilation evidence (2026-10-18)

See [host GCC evidence](V1_9_HOST_GCC_EVIDENCE_2026-10-18.md) for individual Git blob hashes and actual strict GCC/UBSan outputs for the **exact** Scope exit guard, tolerance engine, compare module, and reference-Canvas regression sources with explicitly substituted host device headers. An additional stale-verdict guard now prevents a previous PASS from being drawn after the reference preset or measurement changes; GCC also exposed and resolved a `-Werror=format-truncation` renderer issue.

This improves source-level verification only. **LS-01 (exact E11 FAP build), LS-04/05 (real hardware resource isolation/teardown), LS-07 (ISR/LCD performance), LS-08 (independent physical truth), LS-09 (legacy device regression), LS-10 (install/recovery) remain open.** The remaining complete GitHub Actions workflow status is still not authenticated by a real run log.

## Emergency exit code lifetime correction — 2026-10-18

Source defect: the previous final-exit guard used `return -2` after retaining the heap allocation. If firmware still owned a Scope callback, **unloading the FAP would invalidate the callback's executable address**, regardless of whether heap storage remained allocated. The unusual teardown failure therefore now ends with Furi's documented `furi_crash` (after quiescing only our own IRQ-handler flag) rather than returning. Flipper's documented crash handler logs diagnostic state and reboots on ordinary production firmware; debug builds may halt. This is a last-resort fail-closed policy, not a feature or permission to inject faults on a production device.

- Changed file `src/labmate.c`; fix commit `31430fd`. The native HAL ABI / complete FAP link and physical reboot behavior remain **unverified**.
- The purely logical `labmate_scope_exit_storage_safe` gate was recompiled from exact Git blob sources in local C11 GCC `-Wall -Wextra -Werror -pedantic` and UBSan on 2026-10-18. Both **PASS**. This does **not** exercise the `furi_crash` call in a live firmware image.
- The host-test workflow initially gained a `pull_request` event for `main` in `f9e0fea`. An actual GitHub PR metadata check established that Draft PR #15 targets `dev/v1.8-completion`, not `main`; commit `5287fe4` corrected the filter to include the real PR base, retaining `main` for future review. The PR remains Draft and unmerged; enabling the event does not establish a successful CI run.
- **Go/no-go:** Do not flash, install a new v1.9 FAP, or label native cleanup accepted until exact SDK compile and a controlled hardware test with backup/recovery proof. The current v1.8 stable and E11 prerelease are unchanged.

## Host CI observability and watchdog matrix update — 2026-10-18

- `tests/test_scope_buffer_timeguard.c`: added strict, deterministic tests for exact wall-duration timeout, invalid guard configuration, sticky invalid terminal states, FULL buffer result, capture/timebase ERROR, impossible snapshot count/capacity, decreasing edge counts and saturating UINT32_MAX dropped-edge bookkeeping. **These newly added cases have not been confirmed in an exact GitHub checkout/CI execution.**
- `.github/workflows/v19-scope-host.yml`: retains compiler version, exact `GITHUB_SHA`, executable names, output and pass/failure context in a review-only 7-day artifact; corrected shell `printf` newline escaping before check-in. The workflow keeps `pipefail` and does not convert failing tests into green jobs. Artifacts are never a GitHub release and never installed on Flipper.
- Draft PR #15 current acceptance status has been placed at the **top** of its description to supersede earlier historical remarks that could incorrectly imply overflowed/truncated prefix samples may be accepted as A/B PASS. The user-device policies and no-flash restriction remain unchanged.
- Provenance: regression commit `9650c14`, log improvements `9aab450` and `fedb19f`. No CI run was returned by the available authenticated PR-run/status tools as of this check, and no native SDK/FAP build, merge, flash or physical test was performed.

**NEXT NO-GO GATES:** (1) obtain actual GitHub Actions host/build run and strict log; (2) inspect the precise v1.9 Momentum FAP compiler/link result; (3) resolve PR mergeability conflicts if real, without merging the E11 firmware history into main; (4) device acceptance against matched firmware with backup and instructor-assisted independent timing truth.

## Pinned E11 FAP build observability and operator handoff — 2026-10-18

The GitHub review-only FAP workflow runs on pushes to `dev/v1.9-logic-scope` and compatible Draft PR events; see [first Flipper trial protocol](V1_9_FIRST_FLIPPER_TRIAL_NO_FLASH.md). No device data is written. The manual-dispatch setting was inoperative because the workflow does not exist on the default `main` branch, so it was removed. Keep `main` untouched.

- Its only executable FBT target is `./fbt fap_labmate`. The pinned Momentum source remains `d3f89dfe2ef6b01839201598e9be1590cba80322`; the scripted E11 patch chain and SDK/FAP provenance gates are not bypassed.
- **New diagnostic evidence:** `./fbt fap_labmate 2>&1 | tee ../v19-fap-build-output.log` with Bash `pipefail` retains compiler/linker errors **without treating a failed compiler as PASS**. If any earlier E11 source patch command fails, an ERR trap records the failing Bash line and exit status. An `if: always()` diagnostics step creates `v19-E11-COMPILE-LOG-REVIEW-ONLY` with run SHA, run ID, pinned firmware base, and up to 2000 lines of the FBT output. It does **not** include a failed binary or trigger any flash/install.
- The original `v19-E11-FAP-REVIEW-ONLY-DO-NOT-INSTALL` upload remains separate, downstream of a **fully successful compiler, linked ELF verification, provenance and SHA256 gate**. It is retained only for review, and is not an authorization to install it.
- Source changes: `52b001b` (compiler logging), `eacba91` (nonblocking success artifact ordering), `03ffe5d` and `94cf021` (patch failure diagnostics). Trial protocol source: `13e0ad6`.
- **Workflow structure was inspected via the connected GitHub repository API**, including the pinned base, manual dispatch, failure diagnostics, success-only artifact, SHA gate and executable FBT commands. This static review is **NOT** an actual successful GitHub run or FAP SDK build. Current GitHub connector only exposes PR-triggered run subsets; repeated current-head lookups yielded no independently verifiable run/job success. The local container cannot resolve github.com.
- **Next exact step (supersedes the earlier automatic-only instructions below):** open the Actions workflow, choose **Run workflow**, explicitly select `dev/v1.9-logic-scope` rather than `main`, and share the resulting `/actions/runs/NUMBER` URL. A safe `main` visibility stub now makes the manual dropdown discoverable; only the dev branch performs the review-only FAP build. Do not install anything until an authentic green run, installed E11 ABI, verified original LabMate FAP+CSV+S1 backup and controlled FAP-only acceptance approval are all present.

## Default-branch-only manual Actions correction — 2026-10-18

GitHub's documented `workflow_dispatch` behavior requires the workflow file to exist on the repository's **default branch** for a manual UI run. Exact connected-repo reads returned `NOT_FOUND` for both `.github/workflows/build-v19-e11-fap-review-only.yml` and `.github/workflows/v19-scope-host.yml` on `main`, while they exist on `dev/v1.9-logic-scope`. Therefore the previously documented **Run workflow** direction was misleading. The inoperative dispatch trigger was removed from both dev-only workflow files (commits `e0b3745`, `1887675`) without modifying Stable or `main`, and the user-facing [trial instructions](V1_9_FIRST_FLIPPER_TRIAL_NO_FLASH.md) were corrected in `7cc66ad`.

**Current authorized CI evidence path:** automatic push and PR runs, selected from GitHub Actions / Draft PR #15 Checks. Their authoritative individual run URL is necessary because the connected repository tool exposes only pull-request-triggered workflow run subsets and the legacy commit-status endpoint shows no entries. Do not infer a green or failed CI job from either empty list.

## Actions visibility correction and safe development build launcher — 2026-10-18

**Root cause confirmed with authenticated GitHub file reads:** The E11 v1.9 Actions workflow was present on `dev/v1.9-logic-scope` but **absent on the default branch `main`**. GitHub's UI requires a `workflow_dispatch` workflow to exist on the default branch before showing the manual **Run workflow** entry. The prior advice to find a manual button was therefore unusable.

**Minimal CI-only solution (no Stable application modification, no PR merge):**

- A new, 836-byte *guard-only* `.github/workflows/build-v19-e11-fap-review-only.yml` was added to `main` (commit `f71459d`). This is **the sole change made to `main`** for discovery. It has no repo checkout, no FBT command, no artifacts, no FAP, no device actions; the only job intentionally fails with a select-dev-branch message if someone runs the default-branch version.
- The complete 17-KB workflow still lives on `dev/v1.9-logic-scope`, with `workflow_dispatch` restored and a job-level manual ref gate allowing only `refs/heads/dev/v1.9-logic-scope` (commit `40980a8`). The existing `push` and `pull_request` paths still work. No source code or binary from v1.9 was merged into `main`.
- Connected repo readbacks verified the small `main` guard file (SHA `3c3980e204e64aea7bc1180a9faf190226bcb547`) has a manual trigger and **no FBT call**, whereas the real dev workflow (SHA `3437d3dfe7d78b2bd778632e7662888a3f627e16`) has manual + pinned-E11 compile with the explicit dev branch condition.
- Updated [operator procedure](V1_9_FIRST_FLIPPER_TRIAL_NO_FLASH.md) to select `dev/v1.9-logic-scope` from the **Run workflow** branch dropdown, never leave it on `main`. GitHub's rendering of that dropdown / an actual successful workflow run still has **not been observed independently**, so do not claim CI green, valid FAP or Flipper authorization.

This entry supersedes the preceding historical **“Default-branch-only manual Actions correction”** section which had removed the unavailable trigger and described an automatic-only path. Only **CI metadata** on `main` changed; existing v1.8 Stable source, E11 firmware, tags and installed apps were not modified.


## 2026-10-19 — physical 100 Hz Logic Scope screenshot: cramped 64-edge plot, UI focus fix (candidate)

Operator's **real Flipper Zero** screenshot of the v1.9 first PA7→PC1 100 Hz / 50% test shows many narrow HIGH/LOW bars across the full 128×64 LCD and `E:.. HOLD` visually running into the waveform. Unlike earlier app-only load observations, this screenshot is direct evidence of **actual PC1 edge capture and a waveform**. It is **not** independent quantitative frequency/duty calibration.

Source-level root cause: `labmate_scope_bridge_refresh` projected **up to 64 copied consecutive transitions onto only x=5..122 (117 px)**, yielding ~1.8 px per half-cycle and dozens of compressed periods at 100 Hz. `LABMATE_SCOPE_PLOT_Y_LOW=43` overlaps the FontSecondary glyph band of the status row drawn at baseline y=50. Combined with the long `E:... HOLD LAST64` status and footer text, the screen was difficult to read. This is a **visualization problem, not proof of a waveform-acquisition failure**.

**v1.9 DEV branch repair — source only, NOT YET INSTALLED:**
- `labmate_scope_plot_focus`: a pure read-only window over at most the latest **13 real observed transitions** from the already IRQ-excluded copied 64-edge snapshot. These produce up to six measured square-wave periods across 117 px, in this known 100 Hz/50% case ~9–10 px per half-cycle. The existing full 256-edge capture buffer, timebase validation and metric-latching logic are not modified; no fabricated first or last state, interpolation, IRQ or new HAL calls. `cropped_old_edges` marks the zoomed recent viewport.
- `LABMATE_SCOPE_PLOT_Y_HIGH=20`, `LOW=35`, giving a clear gap from the status text y≈42..50; status suffix is compact `ZOOM`, footer shortened to `OK RUN vPAGE BK EXIT` within 128 px.
- Updated existing pure waveform coordinate unit test and strengthened mock Canvas assertions to reject trace/status collisions; new `tests/test_labmate_scope_focus.c` uses a deterministic true-edge 100 Hz / 50% fixture with 64 stored transitions, expects last 13 shown, six actual cycles, 24 plot lines, >=9-pixel horizontal portions, zero invented edges, invalid timebase fail-closed. Existing project/metrics safety behavior remains.
- Dedicated GitHub Actions host regression `check-v19-scope-buffer-host.yml` updated to run new focus test in strict C11 and ASAN/UBSan, along with prior plot/display tests; source contract updated to require `labmate_scope_plot_focus`.
- **One-command local PC/WSL build-only helper:** `scripts/build-v19-scope-ui-wsl.sh`. Checks pinned dev branch + existing E11 SDK base, runs strict host plot/focus/Canvas tests, copies exactly the repo's FAP source into the existing E11 SDK `applications_user/labmate`, runs `./fbt fap_labmate`, and independently verifies the linked FAP against required exports. Never opens COM or uploads/installs FAP; the output path and SHA256 must be read before a separately controlled FAP-only replacement of the working v1.9.

**Still pending:** actual revised source GCC/SDK build result from the operator or authenticated green CI run, a newly compiled updated FAP hash, on-device installation and fresh screenshot/STOP/BACK. Do not claim the current Flipper screenshot has changed yet. DO NOT run the old version-pinned `run-v19-e11-activation-review.ps1` (it expects the original 97,540-byte FAP and pre-v1.9 staged state). Stable v1.8, firmware and the verified on-device v1.8 backup remain preserved. PR #15 stays Draft.
