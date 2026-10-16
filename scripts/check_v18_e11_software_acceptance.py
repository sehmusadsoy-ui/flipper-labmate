#!/usr/bin/env python3
"""E11 software evidence gate; never promotes CI/build PASS to physical PASS.

This is a repository-level regression guard for the pinned native source
workflow. It complements (does not replace) compiled production-C and full
no-flash MNTM-012/FAP gates. Offline, read-only, deterministic.
"""
from pathlib import Path
import argparse

PIN="d3f89dfe2ef6b01839201598e9be1590cba80322"
FULL=".github/workflows/check-v18-full-012-upgrade-package.yml"
RADIO="scripts/patch_momentum_subghz_ext_rx_status_bridge.py"
LL="scripts/check_v18_e11_direct_ll_boundary.py"
DOC="docs/E11_FINAL_RX_COMPAT_AND_LL_GATE.md"
EVIDENCE={
    "tests/test_v18_subghz_ext_rx_status_bridge.py":
        ("pthread", "subghz_devices_try_start_async_rx"),
    "scripts/check_v18_e11_native_irq_callback_inventory.py":
        ("system", "furi_hal_gpio"),
    "scripts/check_v18_e11_direct_ll_boundary.py":
        ("LL_EXTI", "DIRECT_TIMERS", "DMA2"),
    # Genuine original-C tests must also exercise mirror pin setter while
    # an RX/TX lease or sticky fault is held; unsupported pins fail closed.
    "tests/test_v18_native_ext_cc1101_rx_lease.py":
        ("subghz_device_cc1101_ext_set_async_mirror_pin", "e11_ext_rx_fault"),
    "tests/test_v18_native_ext_cc1101_tx_lease.py":
        ("subghz_device_cc1101_ext_set_async_mirror_pin", "e11_ext_tx_fault"),
    "tests/test_v18_native_ext_cc1101_free_lease.py":
        ("subghz_device_cc1101_ext_alloc", "subghz_device_cc1101_ext_free",
         "e11_ext_rx_fault", "e11_ext_tx_fault", "fail_alloc"),
}
WORKFLOW_REQUIRED=(
    "patch_momentum_subghz_ext_rx_status_bridge.py",
    "test_v18_subghz_ext_rx_status_bridge.py",
    "check_v18_e11_direct_ll_boundary.py",
    "check_v18_e11_native_irq_callback_inventory.py",
    "test_v18_native_js_gpio_callback_cleanup.py",
    "test_v18_native_imu_fifo_exti_lease.py",
    "test_v18_native_signal_reader_e11_lease.py",
    "test_v18_native_ext_cc1101_rx_lease.py",
    "test_v18_native_ext_cc1101_tx_lease.py",
    "test_v18_native_ext_cc1101_free_lease.py",
)

def require(cond, reason):
    if not cond:
        raise ValueError(reason)

def check(root:Path):
    flow=(root/FULL).read_text()
    doc=(root/DOC).read_text()
    radio=(root/RADIO).read_text()
    ll=(root/LL).read_text()
    require(PIN in radio and PIN in ll and PIN in doc,
            "Pinned Momentum baseline changed without owner review")
    for item in WORKFLOW_REQUIRED:
        require(item in flow, "Missing E11 full-build step: "+item)
    require(flow.count("python3 labmate/tests/test_v18_native_ext_cc1101_free_lease.py momentum-src") >= 2,
            "Original CC1101 alloc/free gate must run after both RX and TX patch stages")
    require("DO NOT FLASH" in flow and "not a release" in flow.lower(),
            "No-flash review-only package contract changed")
    require("SubGhzDeviceInterconnect" in doc and
            "SUBGHZ_RADIO_DEVICE_PLUGIN_API_VERSION 1" in doc,
            "External plugin v1 ABI exception missing")
    require("status UNVERIFIED" in doc and
            "third-party" in doc.lower(),
            "Legacy third-party void callback risk must be disclosed")
    require("sticky fault" in doc and
            "operator-approved controlled restart" in doc,
            "Non-destructive abnormal resource recovery contract missing")
    require("DEFERRED / HARDWARE PENDING" in doc,
            "Physical fixture acceptance cannot silently become PASS")
    require("Do NOT retrofit" in doc or "Do not" in doc,
            "Missing explicit no-unsafe-ABI-upgrade warning")
    for path, tokens in EVIDENCE.items():
        text=(root/path).read_text()
        for token in tokens:
            require(token in text, path+" missing negative-regression evidence "+token)
    require("source" in ll and "RTC" in ll,
            "Direct LL audit must retain reserved infrastructure checks")
    print("E11 SOURCE-REVIEW ACCEPTANCE GUARD PASS")
    print("Pinned full native build and original-C host gates remain mandatory.")
    print("External CC1101 RX/TX setter tests required; default-pin scope only.")
    print("External v1 third-party RX, optional pins, recovery and physical tests remain OPEN.")
    return 0

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("repository_root",type=Path,nargs="?",default=Path(__file__).resolve().parents[1])
    args=ap.parse_args()
    try:
        return check(args.repository_root.resolve())
    except (OSError,ValueError) as exc:
        print("E11 SOURCE-REVIEW ACCEPTANCE REFUSED: "+str(exc))
        return 1

if __name__=="__main__":
    raise SystemExit(main())
