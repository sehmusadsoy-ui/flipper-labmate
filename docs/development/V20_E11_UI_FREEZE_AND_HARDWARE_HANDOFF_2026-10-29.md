# LabMate Ultimate v2.0DEV E11 — UI design freeze and hardware QA handoff

**Recorded:** 2026-10-29  
**Decision:** Product owner approves the overall visual consistency, polished/premium appearance and the currently installed UI. **The visual design phase is CLOSED for design iteration.**  
**Next phase:** Functional/electrical device tests, regressions, fixes only when demonstrated, then an explicit Stable release decision.

> **Scope of approval:** owner-reported visual satisfaction with the installed LabMate interface.
> It is **not** a pixel-by-pixel certification of every screen/state, a successful UART/I2C/DS18B20 electrical stimulus test, a release sign-off, or proof of complete functional behavior.

## Protected installed development baseline

| Field | Recorded value |
|---|---|
| Device | Flipper Zero, custom patched Momentum E11, API 87.1 (operator's previously used matched firmware) |
| App version | `v2.0DEV`, **not Stable** |
| Canonical installed app | `/ext/apps/Tools/labmate.fap` |
| Exact executable-producing source commit | `47fd6958441c5f7d07193fb3519f69a9d6ab195f` |
| FAP review run | [GitHub Actions 40838850973](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/40838850973), SDKCHK / FASTFAP / APPCHK PASS |
| Installed FAP size | **177804 bytes** |
| Installed candidate SHA-256 | `160e1c2c7e5f63418bf641fc7b5ab9a72f5bb45219126d914b94185654d10e7e` |
| USB event | **2026-10-29**, operator-supplied console log |
| USB transfer outcome | Previous FAP read back and saved to PC; new canonical FAP write/readback **PASS** |
| Previous installed FAP SHA-256 | `39261383d4b6ad38a74541fa8934098206e37764aee79321740404ee6dbe0bfc` (174192-byte prior E11 candidate) |
| PC rollback copy | `Documents/LabMate-FAP-PC-Backups/before-v20-e11-20261029T081919Z/labmate.fap` (under user's Windows profile; **never commit this backup**) |
| Post-build code lineage | Branch updates after source commit `47fd6958` are **install tooling / workflow / documents only**; independent compare up to `d03d7fe5` shows **no `src/`, `application.fam` or icon changes** |
| Operator visual verdict | User reports interfaces as visually attractive, cohesive, premium, and declares UI design consistency achieved |
| Full device electrical/functional acceptance | **PENDING**; operator's USB log explicitly states `Physical Button/Scope/UI tests NOT YET PERFORMED` |
| Release decision | **v2.0 Stable NO-GO** until required physical/multi-tool QA and explicit approval |

Do not replace the above digest with a branch HEAD hash. Documentation/test-only commits
are **not new app binaries**. After future genuine production changes, record a new exact
FAP SHA, source commit, and independently observed USB readback.

## Physical checkpoint A — operator report 2026-10-29

**A01–A04: 4/4 PASS, reported after performing the supplied A01–A04
instructions on the already installed 177804-byte v2.0DEV E11.**
The user supplied only outcome labels, not screenshots, measured counter
values, exact status/error strings or independent instrument traces.

| Test | Report | Scope of acceptance |
| --- | --- | --- |
| A01, navigation | **USER-REPORTED PASS** | Five groups, tool navigation, BACK/re-entry smoke; not 17 independently calibrated tools |
| A02, UART RX | **USER-REPORTED PASS** | Start/Stop, idle with no peer, re-entry; not real RX bytes or baud accuracy |
| A03, I2C | **USER-REPORTED PASS** | No-device scan/re-entry; positive ACK, real external peripheral and contention remain OPEN |
| A04, 1-Wire | **USER-REPORTED PASS** | No-sensor read/re-entry; external 3.3V DS18B20, CRC and actual temperature remain OPEN |

No observable failure was reported within this smoke scope; do not infer
that fault/error states or electrical performance have been exhaustively
tested. The separate **read-only Settings/Records smoke and SD data
integrity** line remains PENDING. The installed candidate identity is
the previously USB-confirmed SHA-256 listed above; there was **no new
independent FAP/firmware readout** in this 3A result.

### Next gate B01 — controlled internal PA7 to PC1 loopback (PENDING)

- Before connecting anything, identify the real external pinout in
  [official Flipper Zero GPIO documentation](https://docs.flipper.net/zero/gpio-and-modules).
  **PA7 = external header pin 2; PC1 = external header pin 15.**
  GPIO is 3.3V logic. Do not use +5V pin 1, +3.3V pin 9,
  an external power source or any ambiguous header pin.
- Only when both pin numbers are independently confirmed, ensure LabMate
  has exited and PWM is **STOPPED**. With no power source attached,
  connect **one jumper PA7 (pin 2) → PC1 (pin 15)**. The same device
  shares its own ground; do not add a separate supply for this test.
- Reopen LabMate, set PWM Studio to preset **100 Hz, 50% duty** while
  stopped; start intentionally with short **OK**, check for a visible RUN
  and no BUSY/ERR. BACK leaves the running PA7 output active inside the app
  by existing deliberate behavior.
- Open Frequency Meter and explicitly choose **LOW PC1** (not HIGH PB3)
  if it defaults otherwise. Compare a stabilized observed frequency
  against the selected 100 Hz reference; capture the exact reading and
  HOLD/BACK behavior. Do not claim calibrated output frequency from a
  Flipper measuring its own PWM: this is a loopback functional test only.
- Return to PWM Studio and **OK STOP**. Verify stopped output and
  safe BACK/re-entry. Fully exit LabMate before physically disconnecting
  the jumper. A different test at 1000 Hz or Pulse Duty is a **separate
  gate after B01**, not automatically passed.
- If any BUSY, ERR, restart, wrong pin or unexpected measurement appears,
  STOP and save the observed screen/log; no blind retry or rewiring
  while PWM is running.
- Evidence required for B01 PASS: exact running/stopped states,
  selected 100 Hz / 50%, selected LOW PC1, observed Hz, abnormal messages,
  and STOP/BACK cleanup. Without confirmed jumper/pin identification,
  mark **DEFERRED**, not FAIL.

**B01 has not yet been performed or marked PASS.** UI remains frozen; there
is no new FAP build, SD write, firmware flash or Stable promotion.

## UI freeze policy (effective now)

1. Treat the current visual language—back chevron, measured text, status chips,
   bottom action hints, 3.3 V tag and tool grouping—as the approved design baseline.
2. **Do not perform speculative redesigns, font reworks, animation experiments or
   repeated trial-FAP builds.** Change UI only for a reproducible defect, a safety
   concern, unreadable text, or a separately authorized feature/design change.
3. A pixel-close-up checklist for all exceptional states remains optional quality
   evidence but is **not a reason to silently revoke the user's overall visual approval**.
   Never claim the nine COMM target state captures were individually taken.
4. Preserve the excluded UART TX layout until explicitly requested. Preserve the
   current functional I2C **4-address pages and UP/DOWN paging**; never silently
   change them to mimic an eight-address concept illustration.
5. No application source code, GPIO mappings, key behavior, stored profiles, CSV
   formats, settings or SDK firmware should change merely to update QA statuses.
6. One device FAP name only: **`labmate.fap`** at the canonical Tools path;
   keep the verified previous-version PC backup; avoid accumulating alternate
   `Step`, `Trial`, `Ultimate` FAP copies.
7. Protect prior published Stable tags/releases and unrelated Momentum firmware.

## Acceptance boundary — what is complete

| Gate | Status / evidence |
|---|---|
| Source-linked COMM renderer GCC + Clang | **PASS**, [40838850979](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/40838850979) |
| Integrated current UI/evidence/core GCC + Clang | **PASS**, [40838850948](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/40838850948) |
| Patched Momentum E11 FAP compile/ABI | **PASS**, [40838850973](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/40838850973) |
| Strict CI candidate installer / operator PC-only mock safety | **PASS**, [40840935469](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/40840935469) |
| Full SHA-pinned candidate USB write + MD5/size readback | **PASS**, operator-supplied console output 2026-10-29 |
| Owner's whole-app design cohesion/visual appearance review | **ACCEPTED**, explicit owner feedback 2026-10-29 |
| Real 128×64 screenshot-by-screenshot pixel audit of every unusual state | **NOT PERFORMED** (separate from owner overall visual approval) |
| Real physical functionality of current v2.0 E11 17-tool integration | **NOT YET SIGNED OFF** |
| Independent calibrated electrical accuracy / foreign ownership / fault recovery | **OPEN / EQUIPMENT-DEPENDENT** |
| Stable promotion / release / default-branch merge | **NOT APPROVED** |

## Ordered physical verification after UI freeze

Perform each test **on the installed candidate**, never on an imagined CI binary.
For every performed test, record date, device app SHA, E11 firmware identity,
pins, wiring, expected value/state, actual observed value/state, STOP/BACK
behavior and PASS/FAIL/DEFERRED. A successful read-only screen display does
not certify sensor conversion or signal accuracy.

### Phase A — no external hardware, zero-risk smoke

- Launch `labmate.fap`. Confirm all five menu groups, 17 tools, one back
  chevron per relevant screen, readable labels and BACK exit without a crash.
- Open the three COMM Ready screens, verify actual pin labels and action hints.
  Open UART receive, START, wait without attached signal, STOP and BACK;
  record real state/safe exit. Do not claim UART RX electrical throughput PASS.
- I2C with **no external I2C peripheral**: READY → SCAN → no replies or
  appropriately explained fault; STOP if still scanning; BACK and re-enter.
  Never report an empty bus as proof of positive ACK/address discovery.
- 1-Wire without DS18B20: READY → READ → no sensor / documented error;
  BACK and re-enter. Never mark DONE/temperature/CRC PASS.
- Check output/generator STOP first and read-only Records/Settings navigation.
  **Do not test DELETE, Reset UI, profile overwrite or storage corruption on
  existing user data.**

### Phase B — verified safe internal loopback and mechanical contact

- PWM Studio `PA7` → PC1 **only after verifying official physical header pins**
  and safe 3.3V wiring, stop source before moving jumpers. Frequency/Pulse
  LOW 100 Hz and 1 kHz, measured vs selected source; check STOP/BACK lease
  release and Doctor/Scope valid-sealed vs no-data distinctions.
- Event Counter `PB3` with known 3.3V signal; verify counts and STOP/RESET;
  avoid resource contention with TIM2 owners.
- Button Analyzer momentary dry-contact switch **PC1 ↔ GND** using the
  internal pull-up; real press/release, debounce 5/10/20/50ms, bounce/settle
  and 2-second hold; never connect 5V.
- Verify state transitions, no stale evidence and no misleading PASS if no
  actual capture/edge exists.

### Phase C — real external communication and persistence

- UART USART1 receive/optional transmit with **verified 3.3V peer and common
  ground**, exact 9600/38400/115200 presets; count Received/Dropped/Errors
  against an independently known byte payload, STOP/BACK and safe busy denial.
- I2C positive ACK with known **3.3V** addressed peripheral on **PC0 SCL /
  PC1 SDA**, appropriate pull-ups and bus owner clearance; verify actual
  7-bit ACK address, four-address page contract, cancel/re-entry.
- DS18B20 externally VDD-powered at **3.3V**, DQ **PA4**, proper data pull-up
  and verified wiring. Record resolution, CRC-valid reading against known
  ambient reference; repeat measurement, STOP, no-sensor and error recovery.
- CSV Logger, History, Profiles, preference persistence using **sacrificial
  test data only**, with prior independent SD backup; no destructive fault
  injections on real user media.
- Finish resource conflict and recovery/rollback scenarios from
  `docs/DEFERRED_HARDWARE_TESTS.md` and
  `docs/V2_0_PHASE3E_E11_DEVICE_ACCEPTANCE_MATRIX_DRAFT.md`.

## Stop / release conditions

**STOP AND COLLECT EVIDENCE** upon any crash/reboot, unexpected BUSY/ERR,
stale values presented as valid, loss of unrelated GPIO ownership, wrong pin
identity or altered storage. Do not retry blindly or flash firmware.

**Stable remains blocked** pending sufficient device-level tool QA, error
paths, persistence, resource release, rollback and explicit operator approval.
A designer's visual acceptance cannot substitute for these gates.

Supporting COMM-specific nine-state checklist:
[`V20_E11_COMM_PIXEL_VISUAL_ACCEPTANCE_2026-10-29.md`](V20_E11_COMM_PIXEL_VISUAL_ACCEPTANCE_2026-10-29.md).
