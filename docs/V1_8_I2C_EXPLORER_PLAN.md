# LabMate v1.8 — I²C Explorer: Compatibility and Safety Gate

**Status (2026-10-13): DESIGN/SDK GATE ONLY. No I²C tool code, FAP, external bus scan or physical I²C PASS exists.**  
**Development isolation:** `dev/v1.8-i2c-explorer` branched from `main` after [UART PR #7](https://github.com/sehmusadsoy-ui/flipper-labmate/pull/7) merged. The published v1.7 Stable release is excluded from this work.

## Goal and initial testable scope

An explicit, **read-only device-address explorer** for a user-owned, known-safe **3.3 V I²C peripheral**. Do not advertise generic device identification or arbitrary write/register access. The first milestone is **bounded manual scan → results → STOP/BACK → resource cleanup**, not a simulated list of detected devices.

### Source/compatibility facts checked

- Upstream Flipper firmware `dev` uses `furi_hal_i2c_handle_external`, acquires/releases it via `furi_hal_i2c_acquire/release`, and exposes `furi_hal_i2c_is_device_ready(handle, encoded_addr, timeout_ms)`: [upstream I²C HAL header](https://github.com/flipperdevices/flipperzero-firmware/blob/dev/targets/furi_hal_include/furi_hal_i2c.h) and [implementation](https://github.com/flipperdevices/flipperzero-firmware/blob/dev/targets/f7/furi_hal/furi_hal_i2c.c).
- External I²C peripheral is configured on **I2C3**, pins **PC0 (SCL)** and **PC1 (SDA)**, GPIO alternate-function open-drain, nominal **100 kHz** by upstream firmware [bus config](https://github.com/flipperdevices/flipperzero-firmware/blob/dev/targets/f7/furi_hal/furi_hal_i2c_config.c). External header mapping is **pin 16 / C0 = SCL; pin 15 / C1 = SDA** ([official Flipper Wi-Fi Devboard header schematic](https://cdn.flipperzero.one/Flipper_Zero_WI-FI_Module_V1_Schematic.PDF), connector pins 15=PC1 and 16=PC0; [Flipper app wiring corroboration](https://catalog.flipperzero.one/application/6a78beb42c28780510a289df/page)).
- **Important:** the above is upstream reference source, **not proof of exact Momentum SDK API 87.1 ABI**. Check the actual Momentum development headers/external symbol export and compile a dedicated isolated candidate before producing scanner hardware calls.
- In upstream `furi_hal_i2c_acquire`, the bus uses a mutex with **FuriWaitForever**. The `is_device_ready` timeout applies to transaction waiting **after** acquisition; it is **not** an ownership-lock timeout. Never promise an immediate BUSY refusal or implement the scanner on the GUI thread with this blocking acquire until a verified bounded ownership strategy exists.

## Hardware/resource rules

1. **Only known-safe 3.3 V open-drain I²C**. No 5 V pull-ups or unknown voltage on PC0/PC1. Common ground when using a supported independently powered 3.3 V peripheral. The first tests must not energize unverified accessories.
2. A valid I²C bus requires suitable 3.3 V SDA/SCL pull-ups, but their presence, value and module voltage must be **verified for the exact peripheral**. No invented wiring or claim that Flipper automatically supplies safe pull-ups.
3. PC0/PC1 are also legacy LabMate GPIO/pulse/frequency capture pins, particularly PC1. **Never run a capture owner on either pin concurrently with external I²C**, and never silently seize a pin or interrupt in use. Ensure capture STOP/release before any I²C acquisition, and restore normal GPIO availability on exit.
4. If independent PWM is still RUN, enforce a conservative explicit **SCAN DISABLED / STOP PWM FIRST** policy for the initial version; never silently stop the user's generator. Do not change TIM1 PA7, TIM2 PB3, previous UART USART 13/14 or stored Profiles/CSV.
5. ESP32 Wi-Fi Devboard and other expansion modules should be **detached** before initial I²C tests, with the Flipper/board powered off before physical removal. The previously flashed UART stress firmware does not constitute an I²C slave/test fixture.
6. Do not write to I²C device registers, flash peripherals, change firmware, or touch microSD as part of an address scan.

## Proposed scan behavior (subject to SDK and ownership gate)

- UI opens in **STOP / NOT SCANNED**; an explicit OK starts only if bus/pin ownership policy is satisfied. Back/STOP must remain responsive; no scanning or acquiring in the render/ISR callback or while holding the UI mutex.
- Only normal **7-bit addresses 0x08–0x77** in the initial scan. The upstream HAL uses the encoded address byte; verify `addr7 << 1` against actual Momentum symbols/tests **before** touching a real peripheral. Ignore reserved address space.
- Finite per-address timeout (e.g., **2 ms**, to confirm after SDK review) and bounded total scan work. No claims of precise scan latency until actual measurement. Display **NO DEVICES** rather than a fabricated PASS if no address responds. Keep maximum results bounded and page the 128×64 UI.
- Distinguish **SCAN NOT RUN**, **SCAN PASS / N found**, **NO DEVICES**, **BUSY / CANNOT ACQUIRE**, and **TIMEOUT/ERROR**. Avoid writing to peripheral memory.
- **Blocking-acquire hazard is an explicit architecture blocker:** a background worker alone does not solve cancellation if `furi_hal_i2c_acquire` waits forever. Find a safe SDK-supported limited-wait path or a documented safe restriction with no competing bus owners before building the hardware scanner. Never edit HAL internals or forcibly unlock a foreign owner.

## Ordered implementation gates

- **G0 (now):** source, header, connector and collision review; dedicated branch and Draft PR; no physical scan claim.
- **G1:** validate exact Momentum SDK `furi_hal_i2c` API/export, address encoding and bounded acquire strategy. Report unsupported patterns as blockers, not workarounds.
- **G2:** independent host tests for pure 7-bit scan progression, result bounds, stop/cancel handling, duplicate filtering and UI state.
- **G3:** isolated SDK FAP build plus static ownership checks; all existing UART/PWM/Counter/Profile/CSV regression tests stay green.
- **G4:** physical Flipper **no-peripheral** control run; no fabricated device detected. STOP/BACK, UART reentry, old tool regression PASS only when operator reports them.
- **G5:** one verified 3.3 V read-only I²C peripheral; correct address detected, result display and repeated clean STOP/exit. This requires real hardware evidence; none exists yet.
- **G6:** complete final regression and reviewed risk acceptance before I²C merge. v1.8 Stable release is separate.

**Last UART checkpoint:** [device log](V1_8_UART_ESP32_TEST.md); [accepted limits](V1_8_UART_ACCEPTANCE.md). These remain valid; do not re-run UART stress tests merely to begin I²C development.
