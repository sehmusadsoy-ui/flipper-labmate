# v1.8 E11 — Firmware-Global Resource Lease Contract (DESIGN ONLY)

**Branch:** `dev/v1.8-completion` / Draft PR #13.
**Pinned, already installed firmware source:** Momentum
`d3f89dfe2ef6b01839201598e9be1590cba80322`.
**Installed LabMate EXITFIX FAP SHA256:**
`7a76f626f34a65059d9536fa2cd52b2639f4d1038a9b5c69291fa28d5e4f63be`.
**Approval state:** NO new firmware/FAP/USB install; NO v1.8 Stable approval.

## Why application-local ownership is insufficient

`LabMateCaptureOwner` and `LabMateCommOwner` reject overlaps **inside
LabMate**. A separate Momentum app/service can still use a timer, GPIO,
EXTI callback or PWM without consulting these variables.

Read-only review of the actual pinned firmware identified:
- `furi_hal_bus_enable(TIM1/TIM2)` checks (and asserts) that the
  peripheral is disabled, rather than returning a recoverable owner
  claim. A momentary `furi_hal_bus_is_enabled` check would introduce
  a time-of-check/time-of-use race; it is NOT a global lease.
- `furi_hal_gpio_add_int_callback` asserts that the chosen EXTI
  callback slot is empty. This is NOT a nonfatal try-add API.
- `furi_hal_pwm_start` and LabMate's direct TIM2 setup configure
  peripheral registers. `furi_hal_gpio_init_simple` reconfigures
  pins. Each can affect an unrelated prior owner if ownership is not
  jointly enforced.

This is a **source-level identified risk**, not a reproduced crash.
The completed EXITFIX E1–E9 physical tests show safe behavior under
the observed ordinary, noncompeting conditions, not general concurrency.

## Proposed firmware contract (NOT YET IMPLEMENTED)

A correct cross-firmware solution must be installed **inside the exact
firmware**, before any component configures a shared resource. Merely
adding a second LabMate-local mask, or checking a clock/callback state
before a call, is not sufficient.

1. Expose a versioned, firmware-owned and atomically enforced
   `try_claim(owner_handle, resource_mask)` with a stable FAP ABI.
   Lock the shared state in a short RTOS critical section, **not**
   across device operations or a long wait. Fail without any register,
   pin mode or callback mutation on conflict. Unsupported SDKs must
   fail closed; do not fall back to unsafe direct HAL access.
2. Alias each physical resource to the SAME underlying lease:
   TIM1+PA7 (PWM), TIM2+PB3 (counter/HIGH frequency),
   EXTI line+physical pin (PC0/PC1/PB2/PA4), I2C3+PC0+PC1,
   and PA4 for 1-Wire. Shared EXTI lines must respect MCU
   line-number sharing across GPIO ports. Claims that touch
   multiple resources are ALL-OR-NOTHING.
3. Only the matching **unique, versioned owner handle** may release
   its exact acquisition. A wrong owner, double release, partial
   release, stale handle or failed acquisition must not disable a
   peripheral, reset a pin, or remove a callback owned by someone
   else. Establish a defined lifecycle for abnormal app termination.
4. Integrate the contract into **all relevant firmware HAL entry
   paths and other firmware services**, not only LabMate; audit
   timer/GPIO/EXTI/I2C/PWM owners and any direct LL register writes.
   A bypassing legacy service is an outstanding blocker, not a
   protected service. Coordinate with existing external-I2C firmware
   mutex; do not introduce an independent competing I2C lock.
5. Design hardening and ABI checks must preserve the exact patched
   Momentum build's radio/option-byte semantics and original tools.
   No firmware patch may be deployed without a new pinned
   firmware+FAP CI build, complete recovery strategy, separate
   explicit operator consent and real-device acceptance.

## Executable contract prototype — HOST ONLY

`tests/v18_firmware_lease_proto.c` models a shared lease table.
It uses a `pthread_mutex_t` **only as a host stand-in** for a
kernel-protected atomic critical section. It is **not linked into
the production FAP or firmware**.

`check-v18-firmware-lease-proto.yml` independently checks the
exact pinned firmware HAL source expectations and compiles and
executes this host prototype with strict C11 warnings.

Expected HOST tests:
- Non-LabMate owner reserves TIM2/PB3: LabMate refused, then succeeds
  only after the real owner releases.
- EXTI/PC1 vs another PC1 consumer, I2C3 vs PC0/PC1, PWM TIM1/PA7
  vs unrelated TIM2/PB3: alias conflicts fail and disjoint ownership
  can coexist.
- Invalid/empty masks, owner-token reuse, mismatched/partial/foreign
  release and double release never silently clear ownership.
- **24 simultaneous acquisition threads ×25 rounds** race for
  one TIM2/PB3 lease: exactly one owner wins each round.
- Model never reconfigures hardware; no expected PIN/GPIO
  or firmware-side effects are inferred from a successful host run.

This model does not yet solve stable unique token generation,
resource-manager recovery after process crashes, supported firmware
ABI packaging, or protecting legacy drivers that bypass the lease.
All these require real firmware integration, proper driver tests,
CI builds and separately approved device tests.

## Evidence/status gates

| Gate | Scope | Status |
| --- | --- | --- |
| E11.0 | Source contract audit + contested host lease prototype | **HOST CI PASS**, [run 38747593373](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38747593373), source SHA `bdbcc5676072bfc6b0a455de191f17fc10a43c51` |
| E11.1 | Actual patched firmware atomically enforces leases across all relevant HAL/service paths | **NOT IMPLEMENTED** |
| E11.2 | Matched firmware+FAP builds/APPCHK, API/ABI, failure-path and no-register-mutation tests | **NOT TESTED** |
| E11.3 | Operator-approved on-device competing-service safety tests, rollback verified | **NOT TESTED** |
| E10 | Existing-file preservation; nine historical logs absent with unknown reason | **OPEN**, do not restore automatically |

**Release decision:** E11 is a v1.8 gate, not a v1.9 replacement.
Do not mark v1.8 complete based solely on host lease simulations.
The canonical `ROADMAP.md` and
`docs/MASTER_ROADMAP_V2_ADDENDUM.md` remain authoritative.

## E11.0 observed CI evidence (2026-10-15)

At the exact source commit `bdbcc5676072bfc6b0a455de191f17fc10a43c51`,
GitHub Actions [run 38747593373](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38747593373)
completed **SUCCESS**. Its one job passed all steps, including:

- `E11 PINNED-SOURCE AUDIT PASS: source hazard assumptions confirmed.`
- `HOST LEASE MODEL PASS: all-or-nothing, owner-safe, alias-safe, contested 24-thread test x25`
- `FIRMWARE-GLOBAL OWNERSHIP: NOT IMPLEMENTED / NOT HARDWARE VERIFIED`

This is **E11.0 host-model/source-audit PASS**, NOT E11.1 firmware-side
implementation, NOT a new FAP, and NOT a device PASS. The host
prototype currently takes numeric tokens from callers; firmware-safe
unique versioned owner handles and stale-token invalidation remain
mandatory design work before HAL integration.
