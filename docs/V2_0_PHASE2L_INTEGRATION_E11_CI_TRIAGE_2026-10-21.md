# LabMate Ultimate v2.0 — Phase 2L integrated host + pinned E11 compile-readiness

**Date:** 2026-10-21  
**Scope:** `dev/v2.0-signal-doctor` → Draft PR #21 into `dev/v1.9-logic-scope`  
**Decision:** Orchestrator/source readback **PASS**; limited source-identical component regression **PASS**; **22-suite actual full-repo run PENDING**; **pinned E11 SDK build PENDING**; **GitHub Actions 0 total runs**; physical Flipper **PENDING**. No Stable or device writes.

## CI investigation: verified facts, not guesses

- `mcp__GitHub__get_repo` identifies the normal `main` default branch. The dev branch contains `.github/workflows/v20-ui-host-gates.yml`, but `main` does not. This alone does **not** prevent `on.push` from running on the dev branch.
- The dev UI workflow has the correct `push` branch `dev/v2.0-signal-doctor` and PR target `dev/v1.9-logic-scope`. All **22 directly invoked `scripts/test-v20-...-host.sh` files** have been independently fetched at the current dev ref; none is missing.
- `GET /repos/sehmusadsoy-ui/flipper-labmate/actions/runs?per_page=5` returns **`total_count: 0` globally**, not merely an empty dev-branch filter. The latest commit also has **zero legacy combined-status contexts**. Absence of these contexts is not, by itself, proof that no modern Checks API checks exist; the Actions runs query is the relevant fact.
- The connected GitHub fetch endpoint **does not expose `actions/permissions` or `actions/workflows` for this repo**, so whether repository-level Actions are disabled, restricted, or awaiting user approval is **UNVERIFIED**.
- No release, merge, workflow dispatch or main-branch modification has been made. Do not mark CI green on the strength of a YAML file.

**Account administrator follow-up:** Open the repository's **Settings → Actions → General** and inspect whether Actions are allowed. Also inspect **Actions** for any disabled/approval-required workflows. These are user-interface checks; no setting was changed via the connector. If enabling Actions resolves the issue, a subsequent authorized change on the dev branch should generate a workflow run; only the recorded run outcome counts as CI proof.

## New all-host orchestrator

Added `scripts/test-v20-phase2l-integration-host.sh` (Git blob **`257e13ed12365c565dda9b249bce86703216c157`**). It requires `gcc`, `clang`, `awk`, `mktemp`, `application.fam` and the expected complete repo source. Then it runs, in order, all **22** source-linked suites that the existing UI and Snapshot CI workflow references:

```text
UI: ui01 ui02 ui03 ui04 ui05 ui05b ui05c ui05d ui05e ui06 ui06c
Evidence: snapshot phase2b phase2c phase2d phase2e phase2f
          phase2g phase2h phase2i phase2j phase2k
```

It stops immediately on a missing runner or failing child script. From a complete checkout:

```sh
sh scripts/test-v20-phase2l-integration-host.sh
```

**Actually executed locally:** Exact script bytes were matched to the connected GitHub Git blob using `git hash-object`; `sh -n` passed. The orchestration was run against 22 deliberately tiny **mock success runners** and printed its 22-suite success line. Deliberately failing `phase2j` yielded exit status **1** and correctly identified `PHASE2L FAIL: phase2j` after correcting a format-string bug found in the first dry run. **These were mock harnesses; they do not mean 22 production suites passed.**

## New pinned E11 SDK compile-only workflow

Added `.github/workflows/build-v20-e11-source-compile-only.yml` (Git blob **`47b5244e5cdc4d098bd5b0180b8035c96d0e70a2`**). This builds on the **existing reviewed v1.9 E11 patch-chain workflow** without altering its native patch sequence or pinned upstream base `d3f89dfe2ef6b01839201598e9be1590cba80322`.

Safety/order:

1. On a dev-branch push or review PR targeting `dev/v1.9-logic-scope`, checkout the reviewed v2.0 working tree with no persistent credentials.
2. Run existing E11 SDK/FAP verifier's host unit tests.
3. Run the **all-22 host suites**; if any fails, skip the E11 SDK build.
4. Checkout the exact pinned Momentum base; reapply the already audited E11 patch chain only inside the ephemeral CI workspace and test its resource contracts.
5. Stage the v2.0 working source, compile `./fbt fap_labmate` and execute `scripts/verify_v19_e11_sdk_fap.py` against the pinned SDK exports/ELF. The current `application.fam` intentionally retains the provisional `fap_version="1.9"`/`v1.9DEV` internal development metadata; this is **NOT** a v2.0 release-label claim.
6. Upload **only build diagnostics** (not a review FAP, not a GitHub Release). Do not use any device, USB, installer, updater or firmware flashing action.

The dev workflow itself and this compile-only workflow **have zero recorded Actions runs** at time of review. This is configuration/readback proof, not compile PASS.

## Existing component regression freshly rerun

In isolated previously retained host fixtures, compiled **fresh** under GCC and Clang with C11, `-Wall -Wextra -Werror -pedantic`, `-O1 -g`, AddressSanitizer and UndefinedBehaviorSanitizer; both compilers returned 0:

```text
Phase2I PB3/TIM2 accepted-gate audit PASS: 1038 test groups
Phase2J Pulse paired HIGH/LOW evidence PASS: 1171 scenarios
Phase2K native-lease release gate PASS: 2048 reports, only 1 fully released
Phase2K extracted native STOP functions PASS: 9 success/failure/empty-handle cases
Phase2K extracted Button/Counter STOP PASS: 6 release scenarios
Phase2K extracted STOP-all integration PASS: 10 scope/capture/lease scenarios
```

The Phase 2K fixture source/header SHA values match the current GitHub blobs as read back; Phase 2I/J fixtures were previously matched in their independent evidence reports. This **does not** prove the entire current PR tree links or is E11 SDK ABI compatible.

## Why acceptance remains NO-GO

The local runtime has **no complete repository checkout** and cannot resolve `github.com` to clone. The pinned E11 SDK `fbt` source and `arm-none-eabi-gcc` are not installed in this runtime. Hence we did **not** execute the 22-suite wrapper against the live whole source tree, did **not** execute the new compile workflow, did **not** produce a validated v2.0 FAP and did **not** test the Flipper.

Next acceptance gates: enable/authorize GitHub Actions if they are disabled; inspect **real UI-host and pinned SDK compile workflow runs**; resolve all compiler diagnostics in the development branch; verify real E11 STOP/BACK and GPIO resource lease fault behavior on-device after a separately authorized FAP deployment; then validate Dashboard's first actual capture bridge. Preserve immutable normal v1.8/E11 v1.9 Stable, FAP, Profiles and microSD CSV. Stock Momentum remains a separate workstream.

**Phase 2L: integration runners + E11 build gate authored and source-verified; CI/SDK/hardware acceptance PENDING. Stable NO-GO.**
