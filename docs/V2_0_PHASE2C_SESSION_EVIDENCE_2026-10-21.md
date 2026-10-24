# LabMate Ultimate v2.0 — Phase 2C capture evidence hardening

**Date:** 2026-10-21  
**Branch:** `dev/v2.0-signal-doctor` → `dev/v1.9-logic-scope`, PR #21 **Draft/Open**  
**Gate:** **Source-matched isolated host PASS** on GCC and Clang with ASan/UBSan. **Real firmware producer integration and E11 SDK/device PENDING**. No stable release or device writes.

## 1. Confirmed source bug and reproducible RED

Production `src/labmate_capture_session.c` (Git blob `c90a27a6a2449fdab7f57ba009958ba56c5a3c91`) explicitly limits interrupt-backed Pulse Analyzer to GPIO indices **0=PC0, 1=PC1, 3=PB2, 5=PA4**. Other GPIO Monitor polling pins are **not** safe Pulse IRQ inputs. The old `labmate_snapshot_bridge_from_capture()` accepted Pulse indices 0..7, mistakenly permitting PC3/PB3/PA6/PA7 as published Pulse evidence.

The **unmodified old bridge**, locally reconstructed with exactly matching original Git blob `8a97b7f28e2079cbf1a816740ecd8c679fd59d9f`, was compiled alongside the existing source-identical snapshot implementation (Git blob `1cd46551f2d65ef33fe71ee51310a64acf5de44f`). The new rejection fixture failed exactly on a forbidden Pulse pin, **before changing the implementation**:

```text
RED_EXIT=134
Assertion '!labmate_snapshot_bridge_from_capture(&e,&s)' failed.
```

This is a host-code bug, not a report of a firmware GPIO fault.

## 2. Surgical source correction

Added a publicly reusable **pure C** allowlist function `labmate_snapshot_capture_pin_supported(source,pin)` in `src/labmate_snapshot_bridge.h/.c`, used as an early fail-closed structural gate before any output write:

| Source | Allowed pin indices | Physical labels |
|---|---|---|
| Frequency | 1,4 | PC1 low / PB3 TIM2 high |
| Pulse | 0,1,3,5 | PC0, PC1, PB2, PA4 |
| Any other source | none | Separate adapter pending |

Unsupported IDs/pins return **false without modifying the output snapshot**. This does not change the native firmware pin allowlist or any IRQ setup.

**Exact edited GitHub readback and local Git hashes:** `labmate_snapshot_bridge.h` = `93c2eb56f8fc3d591ef9ac5ac2ce006c5f860e69`; `labmate_snapshot_bridge.c` = `4c944e25babdf35d20322bbe9a28553dfc8db1d1`.

## 3. Phase 2C pure evidence session helper

Added `src/labmate_evidence_session.h/.c`, a **host-only-proven app-thread contract** for accepting producer-supplied facts. It does NOT start, stop, inspect or write any HAL/IRQ resource:

- `begin` accepts **only an explicitly confirmed successful native acquisition**, source/pin allowlisted, nonzero real timebase and a non-exhausted monotonically increasing capture generation.
- `record` accepts app-thread submissions of **genuinely completed** observations with strictly increasing sample count and nondecreasing edge/drop counters. A rejected/mismatched report **poisons the session**, preventing replay of a previous good sample as VALID.
- `finish` may run **only after a real teardown attempt**; it requires the caller's actual release result. Successful release can produce VALID only through the existing Phase 2B Snapshot bridge. Failed teardown outputs **BUSY** and enters a sticky **ReleaseFault** state: later `begin` calls are rejected.
- Out-of-order/same instant end timestamps publish **CLOCK ERR** with zero validated samples; no made-up later clock value is used.
- All produced measurements remain gated by the existing Snapshot and Dashboard eligibility functions; after a new INVALID/BUSY event, the previous valid numeric reading becomes unavailable in the Dashboard store.

**Crucial trust boundary:** the helper cannot independently establish whether a caller's sample count/ownership flag is truthful. It is a safe lifecycle **consumer** of verified facts, NOT a native producer implementation. The app must get these facts from the actual session and coherent IRQ snapshots before the helper may be wired into live rendering. In particular, **HOLD is not proof of a released lease** and `frequency_valid` by itself is not proof of a newly completed capture.

## 4. Source-verified executable host evidence

All following files were independently built in a separate local Linux fixture directory; their exact Git blob hashes were matched to GitHub files:

| Source/test | Git blob |
|---|---|
| `src/labmate_evidence_session.h` | `9678901b5e0973d9404df883cc53d9b422a32f0d` |
| `src/labmate_evidence_session.c` | `a403c6897ee091e8feddeb2ceb578332e518a102` |
| `tests/test_v20_phase2c_pins.c` | `f57b2994ef6bf985c442e3b2d08e2565afab4fdb` |
| `tests/test_v20_evidence_session.c` | `77766495d63d3cd0348cc3e24b116e46781ede1b` |
| `scripts/test-v20-phase2c-host.sh` | `04603094d8c2685133192f861af1ee2b964568e8` |

Run from a full repository checkout:

```sh
sh scripts/test-v20-phase2c-host.sh
```

**Locally executed with GCC and Clang**, C11 `-Wall -Wextra -Werror -pedantic -O1 -g` and `-fsanitize=address,undefined -fno-omit-frame-pointer`. Both compilers returned **exit code 0** on two separate binaries, using **production-identical snapshot/bridge/dashboard-store and new session sources**.

Observed outputs under **each** compiler:

```text
UI-Phase2C strict E11 capture pin matrix PASS (8 Pulse, 8 Frequency, 2 unsupported sources)
Phase2C evidence lifecycle PASS: 43 cases
```

The lifecycle cases cover failed starts, denied reentrance, monotonically increasing generations, STOP duplicate denial, trusted sample submission, invalid or rolled-back sample counters, frequency and pulse readout, BUSY after failed lease release, sticky failure, clock-order faults, per-pin admission, UINT32_MAX generation exhaustion and suppression of old numeric Dashboard values.

These test counts are host input scenarios, not independent physical measurements. The full checked-out-repository CI runner was **added** but has not yet been seen executing via GitHub Actions.

## 5. Acceptance debts and safety

- **Still PENDING:** actual firmware instrumented START/STOP ownership facts, verified completed-period counters distinct from IRQ edge counts, atomic pulse snapshot handoff, capture epoch/wrap handling, actual on-device Dashboard and Signal Doctor.
- **Still PENDING:** full UI-06 repo regression; E11 SDK/FAP integration/ABI build and physical Flipper tests; stock Momentum separate workstream.
- CI configuration `.github/workflows/v20-ui-host-gates.yml` invokes the new `scripts/test-v20-phase2c-host.sh` in the read-only snapshot job. No deployed application or firmware was changed. A YAML entry is **not** a CI PASS.
- Existing v1.8 normal Stable and v1.9 E11 Stable, FAP, CSV, Profiles S1–S3 CRC, hardware lease/IRQ modules, menu IDs, firmware, and SD data are untouched.

**Phase 2C safe-source host gate: PASS. Live integration: NO-GO until physical-source evidence can be proved.**
