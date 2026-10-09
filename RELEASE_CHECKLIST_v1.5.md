# LabMate v1.5 — Release-candidate gate (2026-10-09)

**Status:** Candidate built and checksummed; **not published Stable**.
Keep the existing v1.4 release/tag unchanged.

## Accepted development-build device tests

- [x] GPIO Monitor, Frequency Meter, Pulse Analyzer and Signal Generator
  regressions — confirmed by user.
- [x] FREQ/PC1, FREQ/PB3 and PULSE/PC1 CSV recording; repeated START/STOP,
  Log History, signal interruption/recovery — confirmed by prior user
  device results and analyzed CSVs.
- [x] PC1 600-sample/approximately ten-minute logging.
- [x] User confirmed final v1.5-dev display labels, USB-connected
  STOP/save, BACK-to-save and opening both files in Log History.
- [x] CSV imported successfully in LibreOffice Calc (Microsoft Excel
  itself was not tested).

## Release candidate

- [x] Created isolated `v1.5-rc` from tested `v1.5-dev`.
- [x] Source comparison: the complete `labmate.c` differs from
  development only by `LABMATE_VERSION_TEXT` (`v1.5d` to `v1.5`).
  `application.fam` is identical and declares `fap_version="1.5"`.
- [x] GitHub Actions run
  [37867046096](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/37867046096)
  built `labmate-v1.5.fap` successfully, with Momentum SDK **dev,
  API 87.1**, and verified `sha256sum -c SHA256SUMS.txt`.
- [x] Build upload includes `labmate-v1.5.fap`, `SHA256SUMS.txt`
  and `BUILD_INFO.txt`.
- [x] SHA-256 of the **FAP file** (not the artifact ZIP):
  `b5c6a374f9ae70bada33797bef91788626ace81a33580a61e3cb3b5510e530d5`.
- [x] Build source commit: `67110124582550abd520a749183a34db754199a7`.
  Later documentation-only commits do not change the binary.

## Still required before publishing

- [ ] Install the **release-candidate FAP**, make sure only one LabMate
  entry exists and confirm the menu and About show `v1.5`. Since the
  measurement implementation is otherwise identical to the tested
  development build, no full repeat of the completed logger stress
  tests is requested.
- [ ] Confirm Flipper launches the candidate against the installed
  Momentum firmware, with compatible API.
- [ ] Obtain explicit user go-ahead to create the `v1.5` tag and GitHub
  Stable Release. No GitHub Release or tag has yet been created.
- [ ] Publish the **same verified FAP bytes** and matching
  `SHA256SUMS.txt`, not a fresh unchecked build.
- [ ] Update the public `README.md`, `CHANGELOG.md` and roadmap
  release status as part of Stable publication.

## Disclosed limitations

- Real microSD fault recovery, a full/corrupt card and unbounded I/O
  latency have not been certified on a Flipper; never remove the card
  while LabMate runs.
- Simultaneous PC-side writes to a CSV being logged were not tested.
- External frequency calibration and Microsoft Excel import were not
  independently verified.
- Digital GPIO uses only compatible **3.3 V** signals.
- See [release notes](RELEASE_NOTES_v1.5.md).

**Current published Stable remains [v1.4](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.4).**
