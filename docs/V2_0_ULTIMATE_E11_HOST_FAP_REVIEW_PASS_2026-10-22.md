# LabMate Ultimate v2.0DEV — E11 native FAP / host review PASS

**Evidence date:** 2026-10-22, owner-run Ubuntu WSL isolated E11 build.  
**Branch:** `dev/v2.0-signal-doctor`. Stable, `main`, v1.8/v1.9 historical backups and installed device artifacts unchanged.  
**Status:** candidate binary successfully built; real-device functional / visual release approval **NOT YET TESTED**.

## Owner-provided actual terminal result

```text
SDKCHK targets/f7/api_symbols.csv
API version 87.1 is up to date
APPMETA build/f7-firmware-C/.extapps/labmate.fap
FAP build/f7-firmware-C/.extapps/labmate.fap
FASTFAP build/f7-firmware-C/.extapps/labmate.fap
APPCHK build/f7-firmware-C/.extapps/labmate.fap
V20 E11 SDK EXPORTED-API/FAP REVIEW PASS | bytes=123584 | sha256=e9a8098a49df586716423cd66d37dfd6215fedf9006cb913bcef6676d807d1b1
REVIEW ONLY — NO DEVICE WRITES OR FIRMWARE INSTALLATION
V20 CURRENT E11 FAP BUILD AND REVIEW PASS | BUILD ONLY | NO FLASH
V20 ULTIMATE E11 HOST+FAP REVIEW: PASS | NO DEVICE WRITES
```

**Owner-confirmed FAP candidate metadata:**
- Filename: `LabMate-Ultimate-v2.0DEV-E11-REVIEW.fap`.
- Exact file: `/home/adsoy/labmate-v20-ultimate-review-20261022/LabMate-Ultimate-v2.0DEV-E11-REVIEW.fap`.
- Raw E11 compile output: `/home/adsoy/labmate-v20-ultimate-review-20261022/momentum-src/build/f7-firmware-C/.extapps/labmate.fap`.
- Size: **123584 bytes**.
- SHA-256: `e9a8098a49df586716423cd66d37dfd6215fedf9006cb913bcef6676d807d1b1`.
- MD5: `2c84ba22e91a87fcd430fd9ca3a6582c`.
- Local source: `/home/adsoy/labmate-v20-ultimate-source-20261022`.
- E11 SDK exported API: **87.1**.
- Source-side status: source invariant audit, mandatory host suites, E11 FBT build, SDKCHK and APPCHK completed per owner-run script's final PASS.
- Local review command exit `V20 ULTIMATE E11 HOST+FAP REVIEW: PASS`, not independent hardware evidence.
- No firmware flash, app install or device writes.

## GitHub source-provenance cross-check

After the owner supplied the local `ULTIMATE_REVIEW_PROVENANCE.txt`, all **six reported source Git blob SHA-1 IDs matched the current GitHub development branch**:

| Path | WSL owner / GitHub blob SHA |
|---|---|
| `application.fam` | `3fadc5fe7fb51cc285b039498f110e04d6177323` |
| `src/labmate_internal.h` | `0e3580d2a3d955606d1c20060da97484ebd73af3` |
| `src/labmate_dashboard_screen.c` | `b46a49b7ae88ff1676c721d62bcf6e0329ffbada` |
| `src/labmate_doctor_screen.c` | `1e1de8755c089a432ed765ca379832fcb7a5af8c` |
| `src/labmate_doctor_advice.c` | `ccf318533a236c3545a036dc26422442db442bb4` |
| `src/labmate_signal_stats.c` | `121a09e6a2582daa94351d6bf417757ee0346478` |

Six matches prove these specific source-file identities, **not** a full-tree byte-for-byte source attestation; host test-only files received local patching, and a full source-tree hash was not reported.

## Release / user protection decision

- **PASS:** integrated host review, native E11 FAP construction, exported API / APPCHK, owner-reported FAP checksums, six live GitHub source blobs.
- **PENDING:** app launch, About `v2.0DEV` screenshot, 17 guides, old v1.9 FAP preserved, common 128x64 geometry across tools, read-only Dashboard navigation, Signal Doctor diagnostics on measured sealed events, Counter/Logger source provenance after hardware teardown, STOP/BACK, data integrity, long-run tests.
- **NOT CLAIMED:** v2.0 Stable, all roadmap features completed, exact device functional QA pass, ordinary stock Momentum compatibility, independent external instrument calibration.
- Original active `/ext/apps/Tools/labmate.fap` remained previously verified **101468 bytes / MD5 `066f017c695bb5a17158a7b26c8f4838`** with corresponding protected Windows PC copy (SHA-256 `d8bb04cf6de6ebaa466e7487e619d9f68af21dac49df2aa51e91dfae1f9f55c2`).
- Earlier Phase3D sidecar `/ext/apps/Tools/labmate-v20-phase3d-trial.fap` was separately verified **115104 bytes / MD5 `7333aea05d157e915ee5a9c4de0a2296`**. No reason to delete, rename or replace without authorization.
- Both FAP versions declare the same `appid="labmate"`. A separately named sidecar does **NOT** isolate the app's SD data directory or necessarily distinguish launch icons. Fresh specific **device upload authorization** and subsequent **first-launch authorization** are needed for this new artifact. Old permissions for the previous trial upload are not automatically renewed.

**Next non-device stage:** retain the 123584-byte candidate under pinned hashes, take a separate PC-only immutable copy, then after user consent conduct **one consolidated E11 acceptance campaign**, not recurring individual UI tests. A PASS should only be assigned to a test after real-device evidence supports it.

**Release gate: v2.0 Stable NO-GO until final integrated E11 physical acceptance and outstanding roadmap disclosure.**
