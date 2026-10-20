# LabMate v1.9 Logic Scope — Physical acceptance and release gate
Date: 2026-10-20
Status: **physical core loopback and resource handoff PASS (operator-reported); public release NOT authorized / NOT yet verified.**

## Exact native candidate (do not substitute files)
- Source pin: `72eb58d6c65d31f510acf6f532ee23c543a9149d`
- Installed E11-patched Momentum SDK base: `d3f89dfe2ef6b01839201598e9be1590cba80322`, isolated Windows SDK in previous review.
- Candidate FAP: **101,468 bytes**, SHA-256 `d8bb04cf6de6ebaa466e7487e619d9f68af21dac49df2aa51e91dfae1f9f55c2`.
- Operator's Windows log: native `fbt.cmd fap_labmate`, LINK, APPMETA, FAP, FASTFAP, APPCHK, strict E11 exported API FAP reviewer PASS; unrelated cli_bridge/mtp manifest warnings did not fail LabMate build.
- Operator's install log: new active file and retained backups both fully read twice, including independent reopened read-only session; FAP-only replacement PASS; no firmware flash.
- Previous FAP versions (99,376-byte redesign predecessor, 97,724-byte v1.9 UI), final v1.8 and historical E11 backups and existing LabMate data protected by earlier installation checks. Do not overwrite, wipe or globally reset.

## Physical core test evidence

| Gate | Operator result | Evidence |
|---|---|---|
| Logic Scope waveform on PC1, PA7 100Hz 50% | PASS | User screenshot: framed true square wave with HOLD 100.00Hz, 50.0% |
| 100Hz / 50% Reference | PASS | User screenshot: TARGET 100Hz 50%, FREQ 100.00Hz, DUTY 50.0%, PASS |
| 1kHz / 50% measured B capture | PASS | User screenshots: 1.00kHz 50.0% in compare and B details |
| Sequential A/B capture and compare | PASS | User screenshot: A 100.00Hz 50.0%, B 1.00kHz 50.0%, dF +900.00Hz, dD +0.0% |
| A details | PASS | User screenshot: HIGH 5.00ms, LOW 5.00ms, PERIOD 10.00ms |
| B details | PASS | User screenshot: HIGH 500us, LOW 500us, PERIOD 1.00ms |
| Negative reference gate (1kHz input, 100Hz target) | PASS | User screenshot: FAIL, correctly rejects target mismatch |
| Positive reference gate (1kHz input, 1kHz target) | PASS | User screenshot: PASS after target selection |
| Frequency Meter and Pulse Analyzer after Scope exit | PASS (operator aggregate) | User replied PASS to matrix; individual numeric logs not supplied for this final pass |
| Scope re-entry RUN/STOP and BACK/IRQ resource release | PASS (operator aggregate) | User replied PASS to matrix; no separate serial logs |
| BUSY/ERR during final resource test | No problem reported | Same operator shorthand PASS; not independently logged |
| User's visual acceptance for v1.9 | ACCEPTED FOR NOW | User explicitly postpones major visual redesign until v2.0 |

**Do not conflate operator-reported tests with independent CI/device logs.** Physical results justify completion of the requested v1.9 bench acceptance, not universal compatibility or accuracy guarantees.

## Release gate review, performed after physical PASS

- GitHub PR #15: **DRAFT / OPEN**, head `dev/v1.9-logic-scope`, base `dev/v1.8-completion`, mergeable at inspection. At inspection: **453 commits, 134 changed files, 15,941 additions / 49 deletions**. The changed files include **40 src, 47 tests, 29 scripts, 12 docs, five workflow files, application.fam**. It is not a one-file FAP/UI patch and must be reviewed as a broad firmware-adjacent integration delta.
- Main branch is still **ordinary v1.8 Stable**, with `application.fam` declaring `fap_version="1.8"`. Keep this release unchanged.
- Native API version used by the v1.9 E11 candidate is 87.1; successful SDK-export checks and FAP device launch do **not** attest to the installed device firmware binary hash or universal compatibility.
- Workflow CI was intentionally disabled in this Windows-only project; do **not** represent GH checks as green when no jobs ran. Host five-test gates and native FAP build were run by the operator through the pinned Windows build-only script, not GitHub Actions.
- **Public ordinary Stable v1.9 release is NO-GO** with this E11-specific FAP. It depends on custom E11 resource-lease and nonasserting GPIO callback APIs; it must not be presented as a drop-in replacement for ordinary v1.8, unpatched Momentum or other firmware builds.
- An explicitly labeled **v1.9 Logic Scope E11 custom-compatibility prerelease** is the realistic next publication track if approved; requires bundle provenance, exact firmware compatibility note, independent read-only device firmware binary/ABI attestation where possible, signed/pinned hash manifest, install/rollback documentation, and inspection of PR #15 scope and public distribution conditions.
- **No release, tag, merge, flash or main-branch update has been performed** as part of this evidence note. An aggregate PASS is not permission to do those actions.
- At v2.0 redesign, revisit full 128×64 typography, dense rows and true scope hierarchy; do not quietly backport speculative UI changes into the physically accepted v1.9 binary.

## Remaining next decision

Before publishing, select the release channel: (1) E11-specific v1.9 prerelease clearly restricted to the exact compatible firmware environment; or (2) a separately rebuilt and validated ordinary-Momentum-compatible v1.9 Stable, which is additional engineering work and not represented by this FAP. Keep v1.8 as current Stable until then.
