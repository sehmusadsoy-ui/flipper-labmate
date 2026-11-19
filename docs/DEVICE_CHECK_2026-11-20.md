# Flipper Zero USB device check · 2026-11-20

One LabMate launch on the connected Flipper Zero showed an out-of-memory dialog. After one restart, the same installed app opened and its menus were accessible. The screenshots show the installed CI review build.

## Device and installed build

| Field | Observed value |
| --- | --- |
| Device | Flipper Zero, hardware revision `12`, target `7` |
| Connection | USB serial on Windows |
| Running firmware | Momentum `mntm-dev`, commit `d3f89dfe-dirty`, build date 2026-10-16 |
| Firmware API | `87.1` |
| Installed app | LabMate Ultimate v2.0 E11 review build at `/ext/apps/Tools/labmate.fap` |
| Installed FAP size | 180,200 bytes |
| Installed FAP SHA-256 | `da85b8ff1cfa726cbb794723f5bccc03f75a209c61ea8b0cad2607b0ea662a8d` |

The SHA-256 was calculated from the FAP read back over USB. It matches the E11 native CI artifact built at [`156c0b670d9b996eff34668d0fc144c5d2c24e2d`](https://github.com/sehmusadsoy-ui/flipper-labmate/tree/156c0b670d9b996eff34668d0fc144c5d2c24e2d). The public `v2.0-rc.1` release ships a separate 179,380-byte FAP. [Native CI job and build attestation](https://github.com/sehmusadsoy-ui/flipper-labmate/actions/runs/43245154786/job/131275720319) · [Public RC1 release](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v2.0-rc.1)

## Startup and menu check

1. Before the restart, the USB CLI reported `Preload failed ... Not enough memory`. Opening LabMate from the on-device Tools list also displayed `Error: Out of Memory`.
2. After one restart, the USB CLI opened the same FAP and reported `Application "LabMate Ultimate" is running`. The [main menu](../screenshots/2026-11-20/main-menu.png), [Measure menu](../screenshots/2026-11-20/measure-menu.png), [Signal Doctor reference setup](../screenshots/2026-11-20/signal-doctor.png), [empty Dashboard](../screenshots/2026-11-20/dashboard.png) and [Settings](../screenshots/2026-11-20/settings.png) were visible. The app then exited through its Back controls.

| USB CLI `free` snapshot | Free heap | Largest free block |
| --- | ---: | ---: |
| After the failed launch, before the restart | 92,552 bytes | 73,760 bytes |
| After the restart, before the successful launch | 139,440 bytes | 139,440 bytes |

These are USB-connected snapshots taken outside the failing allocation. The observed error and recovery are relevant to [issue #31](https://github.com/sehmusadsoy-ui/flipper-labmate/issues/31). The failure's root cause and long-idle startup stability still need verification. Electrical measurements and loopback validation are pending. The five interface captures came from the device's 128 × 64 display and are shown at 3× pixel scale.
