# E11 — Supported-software acceptance and explicit exceptions (2026-10-16)

**Decision class:** supported-scope **SOFTWARE ACCEPTANCE PASS**, **NOT** a
firmware-global or hardware/Stable release sign-off.

**Working branch:** `dev/v1.8-completion` (Draft PR #13; do not merge).
**Exact tested LabMate commit:** `349d717f6cde7d1a117edea0db0058e9f2a5748f`.
**Pinned Momentum source:** `d3f89dfe2ef6b01839201598e9be1590cba80322`.
**Post-build documentation/policy head:** `a36688df1ef819f6ce6917ef4de0d6f25a988baf`.
GitHub compare `349d717...a36688d` shows exactly **two later changes:
the E11 final-gate Markdown and the repository evidence-check Python**;
no native patch, application source, native host-test, or full-build
workflow changes after the tested package.

## Final genuine GitHub Actions evidence

| Gate | Workflow run | Verdict | What it proves |
|---|---|---|---|
| External CC1101 RX original production-C | [38955843600](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38955843600) | **SUCCESS** | Default G0 PB2/TIM17/EXTI2 BUSY/callback/lifecycle host gate including updated RX stage |
| External CC1101 TX original production-C | [38955874130](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38955874130) | **SUCCESS** | V2 DMA2/TIM17 native host gate, including RX/TX setter, alloc/free and retained fault safety after TX patch |
| Full matched **no-flash** Momentum/MNTM-012 migration, **one LabMate FAP**, radio/SD resources/JS module | [38955881504](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38955881504) | **SUCCESS** | Firmware/FAP compilation plus checksum, provenance, original-C regression and updater/radio/option-byte comparison |
| E11 repository evidence/deferred-hardware acceptance | [38955947905](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38955947905) | **SUCCESS** | Final documentation/policy commit acceptance; **not** a second firmware compile |

The checked full build's Actions artifact is
`v18DEV-FULL-MNTM012-REVIEW-DO-NOT-FLASH`, artifact ID
`12069454610`, generated on 2026-10-16 and scheduled for expiration
2026-10-23. This is **test-only and not a release, installer or operator
permission to flash**. Use exact archive `PROVENANCE.txt` and
`SHA256SUMS.txt` plus an independently approved recovery plan before
*any* future hardware experiment. A successful CI build does not
validate on-device installation, boot, radio function or recovery.

## What is now allowed to be considered software-complete

Within the **documented supported/default pin configurations of the
exact pinned firmware**, the E11 atomic V1/V2 lease, TIM1/TIM2/TIM17,
GPIO/EXTI/callback exact owners, native RFID/NFC/Sub-GHz/IR/1-Wire/
Serial/Wiegand/IMU/JS GPIO and SignalReader pathways have matched
original-production-C host regression evidence, source-inventory gates
and full integrated package build evidence. New external CC1101
allocation, free and mirror-pin setter logic safely refuses OOM,
outstanding leases, sticky faults and double allocation rather than
freeing a still-live IRQ/DMA callback context. Denied acquisition is
required to avoid foreign GPIO/timer/DMA mutations; exceptional
recovery is deliberately fail-closed.

No separate app or v1.8.1 was created; one LabMate app remains.

## Known exceptions — never promoted to global PASS

1. **Third-party legacy v1 Sub-GHz radio plugin:** the frozen
   `SubGhzDeviceInterconnect.start_async_rx` ABI returns `void`.
   An unmodified third-party v1 plugin cannot attest a truthful BUSY
   result; its fallback is explicitly **UNVERIFIED**. Only the matched
   official external CC1101 reporter handshake is verified. Do not
   silently change ABI or label other plugins safe.
2. **Nonstandard GPIO/pin configurations:** alternate external CC1101
   G0, optional/debug mirror GPIO, extra amplifier/CS sideband
   configurations and unknown external apps have not been universally
   leased. Known unsupported RX/TX G0/mirror starts **fail closed**;
   this is not the same as comprehensive support for every optional
   peripheral control path.
3. **Unreviewed firmware/third-party direct LL paths:** source guards
   cover enumerated pinned native paths only. Unknown dynamic paths
   are not proved safe merely because the documented source inventory
   and host tests passed.
4. **On-device recovery/coexistence:** HAL and driver sticky-fault
   host regression does not establish field interrupt timing,
   physical peripheral collisions or controlled exception recovery.
   See `docs/DEFERRED_HARDWARE_TESTS.md` HW-01..HW-19, especially
   HW-06..HW-19, and the v1.8 physical acceptance gate.

**Disposition:** Close **E11 supported-scope software implementation
and regression** for this pinned candidate. Maintain exceptions as
explicit **COMPATIBILITY UNSUPPORTED / UNVERIFIED** or
**DEFERRED / HARDWARE PENDING** items; do *not* mark the stronger
firmware-global E11/v1.6 ownership or all hardware as unconditionally
complete. Any new app/plugin/pin path or firmware source revision
reopens the relevant software gate. Do not treat this classification as
approval to overwrite v1.8 Stable or move to v1.9 without a separate
v1.8 decision.

**Preservation:** No firmware flash, USB action, SD mutation, main merge,
tag move, release publication, automatic recovery or v1.9 code change.
Existing user CSV/profile backups and stable rollback assets are untouched.
