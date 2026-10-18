# LabMate v1.9 — First Flipper Zero functional trial (DRAFT / NOT YET AUTHORIZED)

**Status 2026-10-18: HOLD FOR VERIFIED FAP BUILD.** This protocol is a checklist, not a claim that a compiled v1.9 FAP exists or has been installed. No firmware flashing, Momentum updater, microSD reformat, SD cleanup manifest or automatic install is permitted. Stable v1.8 and E11 existing builds stay unchanged.

## Next operator action: inspect automatic branch/PR build

**Do not look for a manual Run workflow button.** GitHub requires a workflow to be present on the repository's default branch to offer `workflow_dispatch`; the experimental v1.9 workflows are deliberately absent from `main`. Manual dispatch was removed as inoperative; `push` to `dev/v1.9-logic-scope` and the existing Draft PR #15 `pull_request` event are the intended triggers.

1. Open the repository's [Actions page](https://github.com/sehmusadsoy-ui/flipper-labmate/actions) or the [Draft PR #15 Checks tab](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/15/checks).
2. Look for **LabMate v1.9 exact E11 Momentum FAP REVIEW BUILD (NO FLASH)** and **v1.9 Logic Scope host regressions** on branch `dev/v1.9-logic-scope`. If needed, filter runs by branch and select the newest run associated with the current commit. These `push`/PR jobs, not a manual dispatch, generate the build evidence.
3. Share the **full GitHub Actions run URL** (normally ending in `/actions/runs/NUMBER`). A PR URL is not the same as an individual run URL. If **no matching run** exists, capture the Actions page and the message/status shown instead of attempting a flash, branch merge or unrelated updater.
4. On failure, inspect the workflow step and `v19-E11-COMPILE-LOG-REVIEW-ONLY` artifact. It includes the exact source SHA and failing E11 patch-shell line or up to 2,000 lines of FBT output if those stages ran. Do not retry by flashing the Flipper.
5. Only a fully successful review build can produce `v19-E11-FAP-REVIEW-ONLY-DO-NOT-INSTALL`. We must independently verify its SHA256, installed E11 ABI, and backup before approving the controlled FAP-only trial.

**Status at this revision:** no authenticated v1.9 successful Actions job log available to this project session. The connected GitHub interface exposes only a restricted set of run records, so an empty connector result does NOT mean no push-run exists.

## Gate A — Before touching the device

1. Inspect the actual **successful** GitHub Actions run of `.github/workflows/build-v19-e11-fap-review-only.yml`. The run must checkout exactly pinned Momentum `d3f89dfe2ef6b01839201598e9be1590cba80322`, apply the audited E11 resource lease / nonasserting GPIO callback patches, and finish the `./fbt fap_labmate` and SDK-export/ELF verifier steps. Do **not** infer a success from a workflow file alone.
2. Download the **review-only** artifact produced by that exact successful build, containing `labmate-v1.9DEV-E11-review.fap`, `SHA256SUMS.txt`, `PROVENANCE.txt`, and `READ_ME_FIRST.txt`. Never use a guessed or unrelated FAP.
3. Run the **read-only** package checker with the **full 40-character build commit SHA** displayed in the matching workflow run (not whatever the PR head became later). On Windows PowerShell with Python installed:
   ```powershell
   py -3 scripts/check_v19_review_bundle.py "C:\path\to\v19-E11-FAP-REVIEW-ONLY-DO-NOT-INSTALL.zip" --source-sha "<EXACT_40_CHAR_BUILD_SHA>"
   ```
   Expected `V19 FAP BUNDLE REVIEW PASS`. Any NO-GO, wrong base/SHA, strange extra files, or mismatched firmware = **STOP**. The file's self-contained checksum is not an independent publisher signature.
4. Establish that the **Flipper's installed firmware** provides the precise tested E11-Momentum lease/API ABI expected by this build; a FAP built against patched sources does **not** automatically add APIs to the firmware already running on the device. If not confirmed, **STOP and do NOT flash a new firmware** as a workaround.
5. Before any FAP-only replacement, copy the existing installed LabMate FAP plus its user `apps_data`, Profiles/S1 and CSV logs to an independently readable **computer backup**. Keep the working v1.8 original/sha record. Verify the backup is readable. If any backup, firmware, or install path is uncertain: **STOP** and ask for review.
6. Only after the above gates have been separately verified and FAP-only installation expressly authorized, copy the reviewed candidate **only to the exact existing LabMate FAP path**. Do not copy a firmware updater, manifest or old resource-cleanup bundle. Keep the verified old FAP for immediate restore.

## Gate B — Non-destructive functional test (FAP-only, compatible firmware)

All GPIO stimulus must be **3.3 V maximum**, within Flipper specifications; **never apply 5 V to PC1**. No external scope is required for *functional* loopback, but independent accuracy calibration remains for the university/instructor test. Stop PWM before rewiring.

| Step | Action | Expected observable result |
| --- | --- | --- |
| B1 | Launch v1.9; verify `INFO` remains the lowest menu entry and `COMM` immediately above it | No crash, previous Profiles/S1/CSV unchanged |
| B2 | Open Logic Scope PC1, enter reference screen before START (DOWN twice) | `INVALID / WAIT`, **not** fake PASS/NO SIGNAL |
| B3 | With PC1 held at a safe steady 0/1 through a suitable digital source or pull resistor, START and allow 1 s no-trigger timeout | `NO TRIGGER` / reference `NO SIGNAL` only after actual timeout; floating pin alone is **not** a reliable no-signal fixture |
| B4 | STOP generators before wiring. Connect **PA7 PWM output to PC1 input** using the tested 3.3 V loopback. Start PWM Studio **100 Hz / 50%** and navigate to Scope, then OK START | Auto-stops after >=32 **actual recorded** edges (roughly >=160 ms at 100 Hz; scheduling may add delay). No FULL/BUSY/ERR |
| B5 | DOWN twice to Reference; select 100 Hz/50% preset with UP if necessary | Real metrics shown; `PASS` only if measured within example ±1% frequency and ±2 %-point duty bounds |
| B6 | On the same completed 100 Hz recording, select **1 kHz/50%** reference | `OUT OF TOLERANCE`, never stale PASS |
| B7 | Return to PWM Studio; change output to **1 kHz / 50%** (stop PWM before settings changes as required), then capture again on PC1 | Auto-stops after >=32 observed edges (roughly >=16 ms at 1 kHz), without 256-edge overflow. Reference 1 kHz/50% should PASS only on valid measured data |
| B8 | A/B sequential workflow: save a complete 100 Hz capture as A; start a new 1 kHz capture and save as B | Separate generations; B-A frequency delta about +900 Hz, duty delta near 0; never same-run B |
| B9 | Repeated STOP / BACK / RESTART, then stop PWM Studio | No stuck input callback, GPIO fault, BUSY, crash or legacy-tool regressions |
| B10 | Inspect Logger CSV, Log History, Profiles/S1, UART, Frequency/Pulse/Button and INFO ordering without destructive edits | Existing records remain intact; any new error means no release |

**Notes:** AUTO STOP does not guarantee all signals will succeed: at high edge rates the buffer may saturate before the app thread polls, yielding a truthful FULL/INVALID instead of PASS. `LabMateScopeMetrics` must independently pass exact full-cycle, clock, no-overflow and fresh-generation validations. A passed PA7->PC1 loopback is **functional**, not independent metrological calibration.

## Result format

```text
v1.9 FIRST FLIPPER FAP-ONLY TRIAL
FAP_SHA256:
BUILD_RUN_URL:
BUILD_SOURCE_SHA:
FIRMWARE_PATCHED_E11_ABI_CONFIRMED: yes/no
OLD_FAP_S1_CSV_BACKUP: yes/no
APP_START/INFO_LAST:
EMPTY_REFERENCE_BEFORE_START:
NO_TRIGGER_TIMEOUT:
100HZ_AUTO_STOP/REF_PASS:
100HZ_WRONG_REFERENCE_OUT_OF_TOLERANCE:
1KHZ_AUTO_STOP/REF_PASS:
A_TO_B_TWO_CAPTURE_GENERATIONS:
STOP_BACK_RESTART:
LEGACY_CSV_S1_UART_PWM:
ERROR/BUSY/CRASH:
```

## NO-GO / STOP conditions

Missing actual successful GitHub build run; unknown installed firmware ABI; checksum mismatch; unavailable verified backup; new boot/IRQ fault; FULL at 1 kHz; unexpected PASS for bad/reference-less data; missing STOP/BACK cleanup; profile/CSV loss; FAP version or path mismatch; or any need to flash or update the firmware during this FAP-only trial.

**No actual user-device trial has been performed at the time of writing.**
