# LabMate Ultimate v2.0DEV — one-pass E11 candidate gate

**Source of truth:** GitHub `dev/v2.0-signal-doctor`. User's unrelated uploaded ZIP is NOT the source baseline. Never use old `123584`-byte FAP SHA256 `e9a8098a49df586716423cd66d37dfd6215fedf9006cb913bcef6676d807d1b1` to claim that newer UI or E11 safety changes were built.

## No-device candidate production

From a **fresh new** local clone of that GitHub branch, with its pinned patched E11 SDK at `$HOME/labmate-build/momentum-src`:

```bash
bash scripts/prepare-v20-ultimate-github-e11-review.sh
```

This wrapper fails rather than overwriting any existing workspace/log, verifies current Git branch and clean tracked sources, records the exact Git commit/tree, runs the canonical full source, Phase2L, Phase3A–D and all new Ultimate GCC/Clang host gates, then copies an isolated original pinned E11 SDK and compiles with FBT / SDKCHK / APPCHK. It prints the **new actual size/SHA256/MD5** only when its complete native review is successful. It never writes, flashes, renames, deletes or installs anything on a Flipper. If a required host suite or native build fails, use the last 80 lines from the log and keep device QA NO-GO; do NOT bypass tests.

A manually downloaded *GitHub branch export* can also be reviewed, but lacks a full Git commit/tree attestation. The wrapper labels this limitation; source-file blob hashes appear in the provenance. Prefer a clean actual Git checkout.

Defaults (override `LABMATE_E11_WORK` for a new unused path):

- Workspace `$HOME/labmate-v20-ultimate-github-e11-review`
- Immutable log `$HOME/labmate-v20-ultimate-github-e11-review.log`
- Candidate `<workspace>/LabMate-Ultimate-v2.0DEV-E11-REVIEW.fap`
- Provenance `<workspace>/ULTIMATE_REVIEW_PROVENANCE.txt`

## Subsequent upload — only after owner review / consent

Current installed file previously verified:

- `/ext/apps/Tools/labmate.fap` — 101468 bytes, MD5 `066f017c695bb5a17158a7b26c8f4838`, protected original v1.9DEV
- `/ext/apps/Tools/labmate-v20-phase3d-trial.fap` — 115104 bytes, MD5 `7333aea05d157e915ee5a9c4de0a2296`
- `/ext/apps/Tools/labmate-ultimate-v20dev-e11.fap` — **older** 123584-byte v2.0DEV candidate, MD5 `2c84ba22e91a87fcd430fd9ca3a6582c`

**Do NOT overwrite any of these paths.** When native compile + hash + PC backup succeeds and owner explicitly authorizes exact upload, use a **new unique sidecar filename** and verify file size+MD5 on Flipper CLI, then perform one consolidated user-device acceptance. Same appid `labmate` means a unique filename does NOT isolate shared app data. Do not touch Profiles/Logger/SD data in initial UI-only inspection.

### Single-session device acceptance matrix (operator evidence required)

1. Identity/About: Ultimate launcher, v2.0DEV, 17 guides; old v1.9 MD5 and old trial paths unchanged.
2. All five root cards: correct focus, left/right columns, up/down rows, OK enters, BACK returns; all 17 tools accessible with no name clipping.
3. Doctor: 4 passive evidence sources (Frequency, Pulse, PC1 Scope, sampled GPIO); advisory page; invalid / no-data / unsafe samples show no fabricated diagnosis. Read-only UI navigation.
4. Dashboard: all five independent sealed sources; no historical data shown as LIVE; evidence generation/pin/quality and stale/release failures fail closed.
5. All legacy tool screens including PWM, UART, I2C, 1-Wire, Profiles, Logger/History, Pulse STATS, History Detail: title/footer contrast, 128×64 collisions, status badge, physical keys.
6. Safe frequency & pulse restart denial and wrong/competing resource ownership: no false LIVE; STOP/BACK returns all leases. Do not intentionally inject risky conflicting HAL operations unless covered by a separate approved hardware plan.
7. PA7→PC1 loopback 100 Hz and 1 kHz with 50% duty, Frequency/Pulse/Scope results; PWM STOP confirmed; no BUSY/ERR in successful configurations.
8. CSV/Profile compatibility and SD integrity tests *only after separate explicit approval*, compared to the protected 12-file/2128-byte PC backup. External calibrated device-fixture tests may remain DEFERRED with reason.

**Release state:** Development changes committed; **new FAP and physical acceptance unverified**, v2.0 Stable/merge/firmware flash NO-GO.
