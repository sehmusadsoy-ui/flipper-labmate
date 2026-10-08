# LabMate v1.5-dev — Data Logger

Status: **development only**. Do not label as stable until an on-device
Momentum firmware test has passed. v1.4 Stable remains the release baseline.

## Scope

The Data Logger is a sixth main-menu entry. It reuses the existing capture
engines (not separate GPIO interrupts) and stores one processed measurement
snapshot per second in CSV on the microSD card.

- **FREQ / PC1 LOW** — period-based low-frequency meter
- **FREQ / PB3 HIGH** — TIM2 hardware edge-counting meter
- **PULSE / PC1** — pulse HIGH/LOW/period and duty measurements
- **LEFT/RIGHT** — select the source while logging is stopped
- **OK** — start or stop recording
- **BACK** — stop and close the file, release the capture input, return to menu

The Signal Generator retains its existing PA7 hardware PWM behavior. None of
the v1.4 meter or generator key bindings are intentionally changed.

## Files and CSV fields

Directory: `/ext/apps_data/labmate/`

Example filename: `log_0001.csv`, then `log_0002.csv` and so on. Files
are created with `FSOM_CREATE_NEW`; no existing log is overwritten. Up to
9,999 numeric names are supported.

CSV columns:

```csv
elapsed_ms,source,pin,valid,frequency_hz,high_us,low_us,period_us,duty_pct
1000,FREQ,PC1,1,999.820,,,,
2000,PULSE,PC1,1,,500,500,1000,50.0
```

These rows are **illustrative of the format**, not actual measurement results.
`elapsed_ms` is time since record start measured with the firmware tick counter
and is not wall-clock time. A valid flag of `0` indicates the capture has
not produced a valid result (frequency becomes 0; pulse widths become 0).

The logger snapshots at 1-second intervals, **not one row per GPIO edge**.
SD writes happen in the application loop, outside GPIO interrupt handlers and
outside the UI mutex. After every 10 successfully written measurement rows, the
logger also synchronizes the CSV file to microSD; STOP/BACK synchronizes and
closes it. A failed write or sync stops recording and sets an error message.
Unexpected power loss or microSD removal may still cause lost data; periodic
sync is damage mitigation, not a guarantee.

## Build in the existing Momentum checkout

From the repository root (PowerShell):

```powershell
Copy-Item .\labmate.c "$env:USERPROFILE\Momentum-Firmware\applications_user\labmate\labmate.c" -Force
Copy-Item .\application.fam "$env:USERPROFILE\Momentum-Firmware\applications_user\labmate\application.fam" -Force
Copy-Item .\labmate_10px.png "$env:USERPROFILE\Momentum-Firmware\applications_user\labmate\labmate_10px.png" -Force
cd "$env:USERPROFILE\Momentum-Firmware"
.\fbt launch APPSRC=applications_user\labmate
```

## START/STOP responsiveness fix (repeat-cycle device check passed)

- When starting a new recording, check for already-existing filenames and reuse
  a session-local next-number cursor. Only try to open candidate files that
  do not already exist; CREATE_NEW still prevents overwriting existing data.
- Perform START and STOP file operations after releasing the GUI mutex, showing
  an OPENING/SAVING wait indicator. This prevents storage latency from holding
  the UI drawing lock, but slow microSD calls can still briefly delay button
  handling because the storage operations share the application thread.
- Defer storage cleanup after CSV formatting/write failures until outside the
  GUI mutex.
- If the app still hangs on repeat START, capture the exact stage and investigate
  storage blocking, file handles and whether an asynchronous worker is needed.

**Regression test:** start a PC1 1 kHz recording; STOP after 5 seconds; press
OK again to START a second recording without leaving the screen; STOP again.
Verify two different CSV filenames and readable content, then repeat at least
five START/STOP cycles. Test BACK and re-entry, SD error display, and other
v1.4 measurement screens. Do not consider this fix verified by CI alone.

**Device feedback — 2026-10-09:** The user confirmed that three consecutive
START -> approximately 5 seconds -> STOP cycles and BACK/menu re-entry were
performed without the previously reported freeze. This is a successful
repeat-START responsiveness smoke test on the physical Flipper after the fix.
The longer five-cycle and other regression tests above remain open; do not
infer they passed from this report alone.

## On-device acceptance tests (in progress)

- [x] Build against the installed Momentum API; launch without crashes
- [ ] Verify existing v1.4 meter and generator screens still work
- [x] Insert microSD and record at least 5 samples on PC1 with internal PA7
      generator loopback; check format, timestamps and values
- [ ] Switch to PB3 and repeat at 1, 20, and 50 kHz
- [ ] Switch to PULSE/PC1 and repeat at 1 kHz; inspect periods/duty
- [ ] STOP, BACK and exit close files; existing CSVs are not overwritten
- [x] Record at least 12 rows; ensure periodic sync does not freeze the UI
- [ ] Remove/unmount SD before starting; ensure UI reports an error safely
- [ ] Test sudden signal loss: valid flag returns 0 after timeout
- [ ] Test continuous logging for at least 10 minutes and USB navigation

**Electrical safety:** Flipper Zero GPIO is 3.3 V logic only. Never connect
unknown voltage or 5 V / 12 V directly to GPIO. Use a 3.3 V-compatible
loopback with the internal signal generator for the first tests.
