# LabMate v2.0 E11 WSL pinned-source preflight — 2026-10-21

**Scope:** `dev/v2.0-signal-doctor`, Draft PR #21.  
**Evidence:** Owner-supplied Ubuntu WSL terminal output; not an automated Github CI run.

## Read-only preflight PASS

SDK candidate: `/home/adsoy/labmate-build/momentum-src`; expected Momentum base SHA `d3f89dfe2ef6b01839201598e9be1590cba80322`.

Owner ran the explicit source guard and reported:

```text
PASS: Pinned Momentum commit
PASS: E11 exported native APIs
PASS: LabMate v2.0 source files
PASS: Expected provisional development version
E11 SOURCE PREFLIGHT: PASS
=== PATCH FORMATTING ===
=== SDK DISK SIZE ===
2.1G    /home/adsoy/labmate-build/momentum-src
=== AVAILABLE DISK ===
Filesystem      Size  Used Avail Use% Mounted on
/dev/sdd       1007G  4.1G  952G   1% /
```

The commands `git diff --check` and `git diff --cached --check` produced no diagnostics. Earlier owner inventory showed 57 tracked modifications in this E11-patched SDK, with resource-lease macro and API export present. These modifications have **not** been individually audited against the full E11 patch chain in the current WSL run. A different clean base clone lacked the E11 API export and must not be used as a substitute.

## Decision

- **PASS:** source identity, ABI export presence, development manifest and disk preflight.
- **PENDING:** independent copy staging, FBT compilation and ARM FAP verifier.
- **NO-GO:** Stable release or device installation/flash.
- **Next:** Preserve `/home/adsoy/labmate-build/momentum-src` untouched; copy the complete SDK into a uniquely named `$HOME` workspace, stage LabMate ZIP snapshot there (replace app subtree in copy only), then `./fbt fap_labmate` against the isolated copy. Never treat a FAP selftest as a binary build result.

**Source snapshot:** Owner's local ZIP is from `dev/v2.0-signal-doctor` plus the Phase 2K local test runner correction; not yet full-tree cryptographically attested to the latest branch documentation-only commits.
