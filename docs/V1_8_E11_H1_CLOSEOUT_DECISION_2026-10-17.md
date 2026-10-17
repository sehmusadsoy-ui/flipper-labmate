# LabMate v1.8 E11 — H1 closure boundary and next-action decision

**Decision date:** 2026-10-17.
**Scope:** installed paired E11 trial on a Flipper Zero; development branch
`dev/v1.8-completion`, Draft PR #13.
**Decision:** **SUPPORTED/COOPERATIVE SOFTWARE GATE PASS; TRUE ON-DEVICE
SECOND-CLIENT RESOURCE ARBITRATION NOT OBSERVED. DO NOT CLAIM H1 DEVICE PASS.**
This is **not a v1.8 Stable asset update or a v1.9 start authorization**.

## Authoritative paired trial and acceptance evidence

- Exact E11 FULL review candidate / live-matched app:
  `labmate.fap` SHA256
  `2b31ec3fa9050580dc3c3ff80138578ed185d70811aa8124ebd2d00b8d981af0`;
  native JS GPIO module SHA256
  `fff2ab8ad8e5b320b669283fc611216da99e9cda4dc03428fcd8e8a130ecca0a`.
  Both were compared by on-device MD5 to independently SHA256-pinned
  local E11 build inputs. The native `js_event_loop.fal` MD5 was also
  compared with the exact E11 FULL `resources.tar.gz` member.
- Native Momentum firmware reports `mntm-dev` and pinned source base
  `d3f89dfe` on the actual unit, but this label/prefix is NOT a full
  independent firmware image readback/attestation.
- GUI functional rounds A–G: **36/36 operator-reported PASS** on the
  paired device, with only the explicit physical/control scope shown
  in `V1_8_E11_FIRST_LIVE_BOOT_AND_SMOKE_2026-10-17.md`.
- H0: **PASS**, exact on-device CLI JS `gpio.get("PA7")` plus
  `pa7.read()` with PWM STOP, full markers
  `begin/event_loop/gpio/pin/read=YES`, `error=NO`, `done=YES`.
- H1 attempted with LabMate PWM 100 Hz / 50% RUN and BACK to its menu:
  CLI V3 emitted **no JS launch/start/read/BUSY markers**, so it
  **DID NOT EXERCISE a simultaneous GPIO access**. Operator then
  confirmed the PWM still showed RUN, and a deliberate OK STOP
  succeeded. **PWM persistence + STOP passed as UI operations;
  native second-client BUSY did not pass.**
- H2: **PASS** for sequential native JavaScript PA7 free-state read
  after operator-confirmed STOP and full LabMate app exit. As the
  verified H0 V3 checker was reused, its `H0 v3` internal message
  is normal. This does not prove instantaneous hardware release,
  independent waveform characteristics, or simultaneous use.
- Source-level/native host ownership: [H1 combined original-C gate
  #39033260627](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/39033260627)
  **SUCCESS** for source-extracted native patched JS PA7 claim,
  real native PWM HAL and production LabMate generator C compiled
  into one host-tested ownership lifecycle. Checks denial without
  foreign register writes, PWM persistence, owner STOP, JS acquisition,
  reverse-denial with JS owning PA7, clean reentry. This is a host
  stub with shared lease/register counters, not on-device firmware
  or a second native JS runtime executing concurrently.

## Why a CLI H1 test cannot be accepted

At pinned Momentum commit
`d3f89dfe2ef6b01839201598e9be1590cba80322`:

1. `applications/system/js_app/js_app.c` registers
   `js` using `CliCommandFlagDefault` — NOT
   `CliCommandFlagParallelSafe`.
2. `applications/services/cli/cli_main_commands.c` likewise
   declares the built-in `gpio` command with
   `CliCommandFlagDefault`.
3. `lib/toolbox/cli/shell/cli_shell.c` requires
   `loader_lock(loader)` for these commands; when LabMate is
   an open foreground app, the code refuses dispatch with
   `this command cannot be run while an application is open`.
   The literal refusal message was **source-confirmed**, not
   captured verbatim from the actual H1 device response.
4. The built-in `gpio read` handler in
   `applications/services/cli/cli_command_gpio.c` calls
   `LL_GPIO_GetPinMode` then `furi_hal_gpio_read` without a
   cooperative lease claim. Even were it run independently,
   it would not demonstrate a `GPIO pin BUSY` denial. The
   adjacent `gpio mode/set` paths can reconfigure/write
   GPIO and are **not** a safe H1 fallback.

**NEVER**: mark an all-NO CLI response as a firmware BUSY PASS,
change the ordinary `js`/`gpio` commands to `ParallelSafe`
to force overlap, bypass the loader lock, invoke a background
test thread without separate source review, try direct pin
mode/set writes while PWM RUN, or substitute a different
firmware / FAP pair without independently approved rollback.

## Decision matrix — precisely scoped

| Evidence category | Verdict | Meaning |
| --- | --- | --- |
| On-device A–G GUI/functional rounds | **36/36 PASS** | Requested UI and controls, not universal hardware physics |
| On-device H0 free PA7 read | **PASS** | JS/native GPIO read works after source/resource preflight |
| On-device H1 PWM RUN persisted, deliberate STOP | **PASS** | No observed unexpected stop |
| Cooperative H1 native original-C host integration | **PASS** | Paired JS/PWM original implementation C enforces owner contract under host HAL |
| **On-device H1 simultaneous second-client PA7 BUSY** | **NOT OBSERVED / BLOCKED** | CLI cannot dispatch JS while LabMate app holds loader |
| On-device H2 STOP then PA7 read | **PASS** | Sequential reacquisition after STOP and app exit |
| Unsupported third-party/legacy direct-LL firmware-global arbitration | **UNVERIFIED** | No universal scope proof |
| Exact custom firmware rollback/restore rehearsal | **NOT VERIFIED** | Do not assume official MNTM-012 restore recreates patched trial |
| Fixture-dependent timing/peripheral/power-failure validation | **DEFERRED/HARDWARE PENDING** | See `DEFERRED_HARDWARE_TESTS.md` |

### Release and branch boundaries

The existing published v1.8 Stable tag, binary and `main` remain
unchanged. Draft PR #13 remains unmerged, with the supported E11
software implementation and actual smoke separately evidenced.
The pre-existing v1.8 scope restoration/firmware-global aims may
not be declared universally complete based on this partial overlap
test. Updating in-place v1.8 Stable or initiating the v1.9
development milestone requires the separate project decision
and applicable physical/safety sign-off; do not silently waive a
functionality or hardware gate.

## Only acceptable ways forward

**A — Keep supported-software PASS and defer real H1.** Preserve the
working paired device, complete offline code/document reconciliation,
and explicitly leave cross-client real-device testing as **HARDWARE
PENDING**, not PASS. No device commands required.

**B — Independently reviewed real-native contender.** Before any
device action, specify a legitimate supported parallel execution
context with an independently owned GPIO client, a real firmware
ownership refusal path, deterministic read-only behavior,
unambiguous status capture, device identity/preflight/backup,
one-shot abort/STOP control and recovery analysis. This may
require a **new separately approved development build** and a
full matched firmware/FAP/SD risk review. No permission exists
to flash, overwrite, reset, bypass loader or alter private data
merely to pursue H1.

**Present choice:** A for project preservation; B remains
a future review task until a source-verified safe design and
specific owner approval exist. Do not count B as a currently
available device-test command.

## Maintained evidence

See the chronological live transcript/decision log:
`docs/V1_8_E11_FIRST_LIVE_BOOT_AND_SMOKE_2026-10-17.md`;
the historical supported-scope software signoff:
`docs/E11_SUPPORTED_SOFTWARE_SIGNOFF_2026-10-16.md`;
and the exact on-device installed resource manifest and
read-only parity checks in the same development branch.
This memo supersedes only **earlier unqualified H1 status
summaries**; it does not erase original failed/blocked attempts.
