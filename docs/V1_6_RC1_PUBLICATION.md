# LabMate v1.6 RC1 — Pre-release publication plan

**Reviewed:** 2026-10-10. **Result:** READY FOR MARKED PRE-RELEASE,
subject to an explicit publish instruction. **No GitHub release/tag
created yet.**

## Identity and immutable provenance

- Repository: `sehmusadsoy-ui/flipper-labmate`
- RC branch (keep fixed): `v1.6-rc1`
- Exact tested RC1 commit:
  `62e708fc7c556fe89ef2a1bc99a6ced259434cdf`
- Successful workflow: [38005381142](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38005381142)
- Workflow artifact: `labmate`, containing `labmate.fap`
  and `SHA256SUMS.txt` (SHA256 verified in CI and at device install)
- Proposed new prerelease tag: `v1.6.0-rc1`
- Release title: `LabMate v1.6 RC1 (Pre-release)`
- GitHub Release: **prerelease=true, latest=false** (v1.5
  remains the visible stable release)
- Keep `main`, v1.5 tag and release, and `v1.6-dev` code unchanged.
  New RC1 Git branch commits would fail the RC1 installer's
  head-commit to successful-workflow check, so **do not commit
  documentation updates to RC1 branch merely to record results**.

## Publish steps for future operator-approved action

1. Verify `v1.6-rc1` still resolves to the exact tested RC1 commit,
   and GitHub Actions 38005381142 still reports success.
2. Download the **named** `labmate` artifact of that run through
   authenticated GitHub CLI, validate `labmate.fap` SHA256 using
   its paired `SHA256SUMS.txt`; do not use a floating "latest"
   development-build artifact.
3. Create new immutable release tag `v1.6.0-rc1` at the exact
   above commit. If tag already exists at a different SHA, abort:
   do not move/rewrite old tags.
4. Publish release with `prerelease` and `latest=false`,
   attach **both** `labmate.fap` and `SHA256SUMS.txt`, and
   include disclosure notes below.
5. Verify the new release assets download with matching hashes,
   and verify `main` and v1.5 release unchanged after publishing.
   Do not move the stable latest-release pointer.

## Release description ready for review

**LabMate v1.6 RC1 — Pre-release for Flipper Zero / Momentum Firmware**

This release candidate bundles a digital GPIO monitor, low/high
frequency meter, pulse analyzer, 50% duty signal generator, microSD
CSV logger/history and three nonvolatile profiles with
SAVE / LOAD / DELETE.

Highlights:
- HIGH PB3 frequency-counter regression fix for low rates, and
  tested internal-generator points at 1, 5, 10, 20, 50 kHz.
- Pulse Analyzer HIGH/LOW/PERIOD/DUTY and MIN/MAX, tested
  on PC1 at 100 Hz and 1 kHz; HOLD/LIVE controls checked.
- Generator PA7 ownership, STOP and clean-exit safety checks.
- Three CRC-protected redundant microSD profile slots, safe
  LOAD refusal while PWM is RUN, explicit DELETE and cancel.
- Logger PC1 LOW / PB3 HIGH / PULSE PC1, CSV Log History
  and persistence between sessions.

**Tests:** Host C regressions, source boundary checks, Momentum
FAP build, SHA256 packaging and mock Windows installer **PASS**.
The **RC1 FAP itself** was installed on a physical Flipper via
COM7 and passed user-reported startup label, screen entry,
Profiles S1, Log History and Generator default STOP checks.
Detailed measurement/stats/resource tests were conducted
on the preceding development build with unchanged logic.

**Known limits:** No independent externally calibrated frequency
reference; Flipper generator and meter share the timing source.
Corrupt/full/unavailable microSD and sudden power loss were
not fault-injected on the device. Alternate Pulse Analyzer
input pins and continuous-band accuracy have not all been
characterized. The device must receive only known compatible
3.3 V GPIO signals.

This is a **pre-release**, not v1.6 Stable. v1.5 remains
the official stable version. Existing profile/CSV storage
paths are preserved; always keep a backup before upgrading
third-party tools.

**Install:** An authenticated GitHub CLI + PowerShell
RC1-branch installer fetches the verified RC1 CI artifact,
and replaces only the LabMate external app FAP on the
device. It is not a firmware flash. The prerelease assets
are provided for direct download if preferred.

## Ready / pending

- PASS: RC1 source/CI, package/checksum, Windows installer
  mock, user actual-device installation and six-item smoke.
- PENDING: explicit permission to publish the public
  prerelease/tag and upload assets.
- NOT CLAIMED: stable release; independent metrology;
  deliberate error-injection microSD resilience.
