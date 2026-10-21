#!/usr/bin/env python3
"""LabMate Ultimate v2.0: fail-closed source-contract check, NO device access.
Not a replacement for GCC/Clang, SDK/APPCHK or real-device acceptance.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent

def get(path):
    p = ROOT / path
    if not p.is_file():
        raise ValueError(f"missing required source: {path}")
    return p.read_text(encoding="utf-8")

def require(condition, message):
    if not condition:
        raise ValueError(message)

def contains(path, snippets):
    s = get(path)
    for snippet in snippets:
        require(snippet in s, f"{path}: required contract not found: {snippet!r}")
    return s

def main():
    manifest = get("application.fam")
    internal = get("src/labmate_internal.h")
    nav_h = get("src/labmate_navigation.h")
    nav_c = get("src/labmate_navigation.c")
    render = get("src/labmate_view.c")
    input_code = get("src/labmate_input.c")
    menu_code = get("src/labmate_input_menu.c")
    ui = get("src/labmate_ui_screens.c")
    require('appid="labmate"' in manifest, "appid changed, SD/data compatibility review needed")
    require('name="LabMate Ultimate"' in manifest, "Ultimate launcher not identifiable")
    require('fap_version="2.0"' in manifest, "v2.0 manifest missing")
    require('#define LABMATE_VERSION_TEXT "v2.0DEV"' in internal,
            "displayed version differs from manifest")
    require('"v1.9DEV"' not in internal and "v1.9DEV" not in ui,
            "legacy version still rendered")
    ids = re.findall(r"^\s*(LabMateTool\w+)(?:\s*=\s*[^,\n]+)?[,]\s*(?:/\*.*\*/|//.*)?$",
                     nav_h[nav_h.index("typedef enum {"):nav_h.index("} LabMateTool;")],
                     re.MULTILINE)
    expected = ["Gpio","Frequency","Pulse","Generator","Logger","History",
                "About","Profiles","Counter","Button","Alerts","Uart",
                "OneWire","I2c","Scope","Doctor","Dashboard","Count"]
    require(ids[:len(expected)] == ["LabMateTool" + item for item in expected],
            "historical tool IDs/order changed")
    require("LabMateToolInvalid" in nav_h, "invalid sentinel changed")
    for expected_line in ['"MEASURE", "OUTPUT", "RECORDS", "COMM", "INFO"',
                          '{7U, 2U, 4U, 3U, 1U}',
                          '{LabMateToolLogger, LabMateToolHistory, LabMateToolProfiles, LabMateToolDashboard',
                          '"Signal Doctor"', '"Dashboard"']:
        require(expected_line in nav_c, f"navigation contract: {expected_line}")
    require('"17 tool guides"' in ui, "About guide count out of sync with tool enum")
    for expected_text in ['LabMateScreenDashboard', 'LabMateScreenDoctor']:
        require(expected_text in internal, f"screen enum missing {expected_text}")
        require(f"case {expected_text}:" in input_code, f"input dispatch missing {expected_text}")
        require(f"case {expected_text}:" in render, f"view dispatch missing {expected_text}")
    for tool in ["Doctor", "Dashboard"]:
        require(f"case LabMateTool{tool}:" in menu_code,
                f"menu handler missing {tool}")
        require(f"[LabMateTool{tool}]" in ui, f"help guide missing {tool}")
    contains("src/labmate_doctor_screen.c", [
        "LABMATE_DOCTOR_STATUS_Y", "labmate_doctor_advice", "ADVISORY ONLY"
    ])
    layout = contains("src/labmate_doctor_layout.h", [
        "LABMATE_DOCTOR_STATUS_Y = 50"
    ])
    require("LABMATE_UI_FOOTER_RULE_Y = 52" in get("src/labmate_ui_layout.h"),
            "footer geometry changed without layout re-evaluation")
    contains("src/labmate_dashboard_screen.c", [
        "labmate_dashboard_store_read_measurement",
        "labmate_signal_stats_read", "SEALED / NOT LIVE",
        "FREQ", "PULSE", "SCOPE", "COUNT", "LOGGER",
        "a->dashboard_evidence",
    ])
    contains("src/labmate_doctor_advice.c", [
        "NO SEALED DATA", "CAPTURE + STOP", "NO EDGES SEEN"
    ])
    contains("src/labmate_signal_stats.c", [
        "labmate_snapshot_v1_can_display_measurement",
        "LABMATE_SIGNAL_STATS_MAX_SESSIONS"
    ])
    contains("src/labmate_scope_period_stats.c", [
        "LabMateScopeMetricsReady", "m->completed_cycles < 2U",
        "m->truncated", "spread_permille"
    ])
    for path in ["src/labmate_doctor_frequency_bridge.c",
                 "src/labmate_doctor_pulse_bridge.c"]:
        contains(path, ["labmate_evidence_session_finish",
                        "labmate_dashboard_store_ingest",
                        "labmate_signal_stats_record"])
    contains("src/labmate_scope_bridge.c", [
        "labmate_scope_native_reinit_safe",
        "labmate_dashboard_store_ingest",
    ])
    contains("src/labmate_event_counter.c", [
        "labmate_frequency_tim2_lease_pending",
        "labmate_dashboard_store_ingest",
        "counter_run_start_total",
    ])
    contains("src/labmate_logger_storage.c", [
        "app->logger_session_pin = app->capture_pin_index",
        "app->logger_session_source = app->logger_source",
        "labmate_logger_dashboard_finalize",
        "labmate_dashboard_store_ingest",
    ])
    for path in ["src/labmate_dashboard_screen.c",
                 "src/labmate_doctor_screen.c",
                 "src/labmate_doctor_advice.c",
                 "src/labmate_signal_stats.c"]:
        s = get(path)
        for bad in ["furi_hal_gpio_", "furi_hal_bus_", "storage_file_write(",
                    "storage_file_open(", "furi_hal_resource_lease_try_acquire("]:
            require(bad not in s, f"read-only presenter {path} contains {bad}")
    for name in ["scripts/test-v20-dashboard-host.sh",
                 "scripts/test-v20-signal-stats-host.sh",
                 "scripts/test-v20-doctor-advice-host.sh",
                 "scripts/test-v20-scope-period-stats-host.sh",
                 "scripts/test-v20-phase3b-doctor-panel-host.sh"]:
        require((ROOT / name).is_file(), f"mandatory test runner missing {name}")
    return True

if __name__ == "__main__":
    try:
        main()
        print("V20 ULTIMATE SOURCE CONTRACT AUDIT: PASS | SOURCE ONLY")
    except (ValueError, OSError) as err:
        print(f"V20 ULTIMATE SOURCE CONTRACT NO-GO: {err}", file=sys.stderr)
        raise SystemExit(1)
