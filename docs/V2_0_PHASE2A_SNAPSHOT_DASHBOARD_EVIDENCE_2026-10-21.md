# LabMate Ultimate v2.0 — Phase 2A measurement evidence and Dashboard store

**Date:** 2026-10-21  
**Branch:** `dev/v2.0-signal-doctor`, Draft PR #21 into `dev/v1.9-logic-scope`.  
**Result:** **pure C host tests PASS** for the isolated versioned data contract and a five-source dashboard data projection. **NOT YET:** an on-device Dashboard screen, wiring to real acquisitions, Signal Doctor rules, E11 SDK/FAP build or GitHub Actions success.

## 1. Newly implemented (only passive source)

- `src/labmate_snapshot.h/.c`: version-1 internal `LabMateSnapshotV1` contract with source, original GPIO-pin index, acquisition generation, same-epoch monotonic start/end, timebase, sample/edge/drop counts, frequency, duty and pulse ticks, explicit availability quality, and resource-ownership release flag.
- `labmate_snapshot_v1_well_formed`: rejects unknown versions/sources/pins/statuses, missing generation, invalid duty, reversed/zero-duration sampled intervals; explicit `NO SIG` demands a positive observation interval and zero recorded edges.
- `labmate_snapshot_v1_can_display_measurement`: accepts **only explicitly VALID complete data** with samples, nonzero timebase, zero dropped edges, and released ownership. Frequency/Pulse additionally require at least two observed edges and nonzero frequency; Pulse requires nonzero period; Scope requires an observed edge. Empty/no-data or busy captures do **not** produce a numeric reading.
- `labmate_snapshot_v1_quality_text`: bounded ASCII status labels. Unknown quality maps conservatively to `INVALID`.
- `src/labmate_dashboard_store.h/.c`: a fixed-capacity **five-source**, no-heap in-memory projection. Each source is keyed by its own increasing capture generation. Same or older generations are ignored, newer BUSY/STALE/NO SIG supersede old readings, invalid `VALID` claims are downgraded to `INVALID`, and numeric values are accessible **only** through `labmate_dashboard_store_read_measurement` when fully eligible. The host fixture asserts the entire store occupies at most **512 bytes**.
- Neither type is currently included by `labmate.c` or used in `application.fam`. They are **deliberately not yet bound** to live ISR acquisition, Scope buffers, logger files, existing Profiles, or the screen menu.

## 2. Verified exact Git blob identities

| File | Git blob SHA |
|---|---|
| `src/labmate_snapshot.h` | `5e9b57212cb7110b215202bef352a80d21bd50b2` |
| `src/labmate_snapshot.c` | `1cd46551f2d65ef33fe71ee51310a64acf5de44f` |
| `src/labmate_dashboard_store.h` | `7972e553a4bb01593da8de32329fde7e5953b84e` |
| `src/labmate_dashboard_store.c` | `5abc7e37a0e66c9d89dbc02224d86e0f1e9c32e4` |
| `tests/test_v20_snapshot.c` | `ef5cb54ba8d1e53af08376d1c16f5b8996ed0fb1` |
| `tests/test_v20_dashboard_store.c` | `0d32b9c0bd598cf16017e1ad4ddf2680863762e6` |
| `scripts/test-v20-snapshot-host.sh` | `7203406458482eac8df6438fe7276a6e24a79b40` |

Every tested file was created locally and its `git hash-object` compared against the exact GitHub file readback. New tests execute **the original full new translation units** together, not hand-duplicated function fragments.

## 3. Local execution

Execute from the exact v2.0 branch checkout:

```sh
sh scripts/test-v20-snapshot-host.sh
```

Actual local Linux/host executions: GCC 14.2 and Clang 17.0, both compiled with `-std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer`; **both processes exit 0** for both binaries, with output:

```text
v2.0 snapshot host PASS: 290 source/quality/invalid-input assertions
v2.0 dashboard read-only store PASS: fixed 5 sources, monotonic generations, no invalid numerical reads
Dashboard host scenarios: 637
```

The same three lines occur under each compiler. The suite checks malformed data, unsafe ownership, bad clocks, zero samples, false Frequency/Pulse edges, empty Scope, quality mapping across all 256 raw codes, five distinct sources, monotonically increasing generation 10..50 for each source, replay/reordering rejection and no numerical read after BUSY/STALE/NO SIG.

These are **host input scenarios**, not genuine Flipper measurements. No real device clock, waveform capture, SD/CSV readback or E11 ABI is attested by this result.

## 4. Explicit safety limitations / next steps

1. `capture_generation` is only comparable **within one source and a single acquisition epoch**. The Dashboard store deliberately rejects wraparound or replay; a full producer integration must define session resets before it can ingest a new epoch.
2. Observation millisecond timestamps are compared only as provided. Cross-reboot comparisons, wraparound or independent timer sources are **not** resolved; producers must mark incompatible timebases `CLOCK ERR`, not `VALID`.
3. `NO SIG` is **not automatically inferred** from zero edges by this code. Real acquisition producers must independently prove their minimum observation window; the schema sanity check alone does not establish electrical silence.
4. The store exposes its fixed internal struct for simple host testing, but production UI must obtain measurement values only via its eligibility-checked read accessor. Non-VALID evidence may remain stored for provenance; it must never be formatted as a valid reading.
5. The read-only workflow `.github/workflows/v20-ui-host-gates.yml` has a **separate snapshot-host-only job** and paths for both new modules, without firmware/USB/SD operations. A job definition is not CI PASS; the connected GitHub Actions list has shown **0 runs**.
6. Full UI-06 integrated tests and E11 exact SDK/FAP build still require independent execution. The previously validated v1.8 ordinary Momentum and v1.9 E11 Stable tags, FAP, resources, Profile CRC and CSV formats are untouched.

**Gate:** Phase 2A pure-model host PASS. End-to-end Dashboard, on-device UI, data producers and Signal Doctor remain **PENDING / v2.0 Stable NO-GO**.
