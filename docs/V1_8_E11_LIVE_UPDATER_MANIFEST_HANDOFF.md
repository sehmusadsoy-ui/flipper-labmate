# LabMate v1.8 E11 — Installed old-resource Manifest cleanup gate

**2026-10-17 FINAL STATUS: Static tests PASS; LIVE COM7 READ-ONLY AUDIT PASS, SPLIT TRIAL REJECTED.**

Momentum's updater source pinned at
d3f89dfe2ef6b01839201598e9be1590cba80322 has been checked:
its post-update worker restores internal state, then reads the
**CURRENT OLD /ext/Manifest**, removes the resource file paths
listed there, and only then extracts the NEW firmware resources
into /ext. The old manifest resource cleanup does not compare the
present file MD5 before attempting removal. It also attempts to
remove old resource directories in reverse order.

**Implication:** removing the new LabMate FAP from the experimental
FAP-separated update archive does not necessarily protect the
currently installed EXITFIX FAP. If the OLD on-device resource
manifest lists apps/Tools/labmate.fap, it is scheduled for
cleanup before unpacking. The mere fact that a file is manually
installed or that the new archive excludes it is insufficient
to claim persistence. This is a hardware-identity-independent
software risk and MUST be checked separately.

The on-device Manifest cannot be inferred from downloaded official
MNTM-012 resources: the user currently has customized mntm-dev
firmware (dirty=true), not necessarily the official release.

## Safe, minimal COM7 read-only audit

The program scripts/audit_v18_e11_installed_resource_manifest.py
reads ONLY /ext/Manifest, using a pinned Momentum FlipperStorage
transport. Allowed Flipper CLI actions are device_info for startup,
storage md5 and storage read_chunks on /ext/Manifest, and a
read-transfer y handshake. No SD writes, format, upload, updater,
recovery, app close, output backup files or FAP installation.
The entire Manifest stays in PC memory. Its device MD5 is checked
before and after the transfer; binary receive is bounded.
Files/paths are NOT printed: only aggregate risk flags.

- old_cleanup_lists_installed_labmate_fap: YES/NO — indicates
  whether installed EXITFIX path is listed among old files for
  cleanup; **NO does not guarantee update survival**.
- old_cleanup_labmate_data_files — count of resource-manifest
  entries targeting the LabMate persistent-data subtree.
- old_cleanup_non_labmate_apps_data_files — count of other
  app-data resource file entries in the old cleanup list.
- split_updater_guarantees_exitfix_survival: NO — hard-blocked.
- trial_write_authorized: NO — hard-blocked.

A missing/malformed Manifest, changed MD5 or unsupported syntax
returns nonzero, WITHOUT changing any device file or declaring
the firmware trial safe.

### Windows operator command — no Flipper write

Close qFlipper and any other COM7 client. On the previously
reported COM7 device, use this SINGLE PowerShell block:

~~~powershell
& {
    $ErrorActionPreference = 'Stop'
    $source = 'a67f0238948bb6b71535cd401dccd1e83b6ff698'
    $momentum = 'd3f89dfe2ef6b01839201598e9be1590cba80322'

    $work = Join-Path $env:TEMP (
        'LabMate-E11-OldManifest-READONLY-' + [guid]::NewGuid().ToString('N')
    )
    $transport = Join-Path $work 'flipper'
    New-Item -ItemType Directory -Path $work | Out-Null
    New-Item -ItemType Directory -Path $transport | Out-Null
    Set-Content -LiteralPath (Join-Path $transport '__init__.py') -Value '' -Encoding ASCII

    foreach ($name in @(
        'audit_v18_e11_live_labmate_sd.py',
        'survey_v18_e11_external_sd_ro.py',
        'backup_v18_e11_usb_sd_to_pc.py',
        'audit_v18_e11_installed_resource_manifest.py'
    )) {
        $url = "https://raw.githubusercontent.com/sehmusadsoy-ui/flipper-labmate/$source/scripts/$name"
        Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile (Join-Path $work $name)
    }

    $url = "https://raw.githubusercontent.com/Next-Flip/Momentum-Firmware/$momentum/scripts/flipper/storage.py"
    Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile (Join-Path $transport 'storage.py')

    py -3 (Join-Path $work 'audit_v18_e11_installed_resource_manifest.py') --port COM7 --momentum-scripts $work

    if ($LASTEXITCODE -ne 0) {
        throw 'E11 LIVE OLD MANIFEST AUDIT REFUSED - NO FLASH'
    }

    Write-Host 'E11 OLD RESOURCE MANIFEST CHECK COMPLETE - NO FLASH' -ForegroundColor Green
}
~~~

**Historical procedure note:** This command has now been executed on the owner's real device. Share the
summary fields only; do not upload whole Manifest or other
application paths. Do not run any updater after a PASS.

Final complete test replay after the multi-chunk binary-receive
fixture was corrected: [pinned upstream source gate
#38982699788](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38982699788)
**SUCCESS**, [native Windows fake-COM
#38982699841](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38982699841)
**SUCCESS** (12 old-Manifest tests; 1 unrelated NTFS
collision fixture skipped in the earlier generic suite), and
[full host regressions
#38982699802](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38982699802)
**SUCCESS**. Earlier run #38982669322 failed from our test
fixture writing literal backslash+n instead of actual newline;
repaired without weakening production parser.

## Verified sources / simulations

- [Pinned actual Momentum update worker #38982495403](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38982495403):
  SUCCESS, 10 source semantics tests + 12 manifest risk/USB
  transfer tests, including multi-chunk readback; confirmed old cleanup before new unpack.
- [Windows simulated serial/Manifest #38982495374](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38982495374):
  SUCCESS; all 12 manifest protocol tests passed at the
  final simulated-version/large-stream test commit.
- [Full native/host v1.8 regression #38982495377](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/38982495377):
  SUCCESS.

**Release decision remains NO-GO.** The original updater embeds
the new E11 LabMate FAP; the review-only FAP-excluded derivative
does not yet guarantee the installed EXITFIX survives cleanup.
Regardless of the old manifest outcome, exact dirty firmware
recovery and E11 physical GPIO/TIM1/TIM2/EXTI tests remain OPEN.
Both updater packages are DO NOT FLASH, Stable and EXITFIX intact.


## 2026-10-17 — REAL COM7 manifest verdict: EXITFIX is explicitly scheduled for old-resource removal

**The operator has NOW executed the exact source-pinned COM7 read-only audit
described above.** This supersedes earlier "not executed"/"unknown" language.

```text
old_manifest_resource_files: 2114
old_manifest_directories: 165
old_manifest_metadata_lines: 2
old_cleanup_lists_installed_labmate_fap: YES
old_cleanup_labmate_data_files: 0
old_cleanup_non_labmate_apps_data_files: 156
old_cleanup_app_fap_files: 268
old_cleanup_lists_apps_tools_parent: YES
manifest_total_records: 2281
current_installed_manifest_provenance: READ_FROM_DEVICE_NOT_AUTHENTICATED
old_resource_cleanup_behavior: REMOVES_OLD_MANIFEST_FILE_ENTRIES
split_new_bundle_excludes_labmate_fap: YES_REVIEW_ONLY
split_updater_guarantees_exitfix_survival: NO
exact_prior_firmware_restore_tested: NO
trial_write_authorized: NO
live_manifest_readback_md5_screen: MATCH
E11 OLD RESOURCE CLEANUP SCOPE AUDIT PASS - FIRMWARE TRIAL NO-GO
E11 RESOURCE MANIFEST CHECK PASS - NO FLASH
```

**Authoritative decision:** Under the verified Momentum native updater's
post-update resource cleanup, the **current installed LabMate app at
`/ext/apps/Tools/labmate.fap` IS in the old manifest's FILE removal
list**. Hence a trial that enables this resource-cleanup phase is
expected to remove that file. Our experimental FAP-SPLIT updater also
omits LabMate from the new bundle and therefore does NOT reintroduce
a LabMate FAP during that unpack. It must **NOT** be used as the
proposed way to preserve installed EXITFIX or as a device trial package.

The original full updater DOES include the new uninstalled E11
LabMate FAP and, if resources are updated, may replace EXITFIX
with E11's matching but untested application. It is also
**DO NOT FLASH**; containing the replacement is not authorization
or proof of its proper operation. The manifested zero entries
under `apps_data/labmate` indicate the old **resource-manifest
cleanup does not directly enumerate those persistent-data file
paths**, not that all possible updater or runtime writes are absent.

The 156 other `apps_data` resource files and 268 app FAPs are
*manifest entries*, not proof of damaged or deleted files. The
Manifest was read only, MD5 matched and no files were removed.
No full installed firmware image has been hashed; its exact
rollback remains unproven.

**Safety gate:** `SPLIT_UPDATER_AS_EXITFIX_PRESERVATION=REJECTED`.
`ORIGINAL_FULL_E11_TRIAL=NO_GO`.
`DEVICE_WRITE_AUTHORIZED=NO`. Only offline planning is permitted.
Historical 14-file LabMate PC backup and current 10-file/1791-byte
PC copy remain independently preserved. The working installed EXITFIX
must not be overwritten or removed.
