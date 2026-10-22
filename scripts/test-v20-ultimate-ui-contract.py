#!/usr/bin/env python3
"""Static cross-screen 128x64 visual contract audit. SOURCE ONLY.
No Flipper/SDK access, no rendering/pixel-perfect or hardware PASS claim.
"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent.parent
def src(path):
    return (ROOT/path).read_text(encoding="utf-8")
def body(text,name,return_type="void"):
    m=re.search(r"^(?:static\s+)?"+return_type+r"\s+"+re.escape(name)+r"\s*\(",text,re.M)
    if not m: raise AssertionError("renderer missing: "+name)
    end=re.search(r"^}\s*$",text[m.end():],re.M)
    if not end: raise AssertionError("renderer lacks close: "+name)
    return text[m.start():m.end()+end.end()]
def check(condition,message):
    if not condition: raise AssertionError(message)

def main():
    canvas=src("src/labmate_ui_screens.c")
    files={
        "src/labmate_ui_screens.c":(
            "draw_menu","draw_gpio","draw_frequency","draw_pulse",
            "draw_generator","draw_logger","draw_counter","draw_button",
            "draw_alerts","draw_history","draw_history_detail",
            "draw_profiles","draw_about"),
        "src/labmate_uart_ui.c":("draw_uart",),
        "src/labmate_i2c_ui.c":("draw_i2c",),
        "src/labmate_onewire_ui.c":("draw_onewire",),
    }
    count=0
    for path,names in files.items():
        text=src(path)
        for name in names:
            b=body(text,name)
            count+=1
            check("ui_draw_header(" in b,name+": shared header missing")
            check("ui_footer_pair(" in b or "ui_footer_triple(" in b or
                  "ui_footer_info(" in b,
                  name+": shared physical-key/footer contract missing")
            if name=="draw_history_detail":
                check('ui_footer_info(canvas, "BACK", "LIST", "READ ONLY")' in b,
                      name+": passive read-only footer contract changed")
            for forbidden in ("furi_hal_gpio_", "storage_file_write(",
                              "furi_hal_resource_lease_try_acquire("):
                check(forbidden not in b,name+": renderer acquired native resources")
    check(body(canvas,"draw_menu").count("labmate_menu_tile_x")>=1,
          "Ultimate root grid bypassed")
    check('ui_footer_triple(canvas, "<>COL", "^vROW", "OK GO")' in
          body(canvas,"draw_menu"),
          "Root navigation must show LEFT/RIGHT, UP/DOWN and OK")
    check('ui_badge(canvas, 95, 1, 31, position, false)' in
          body(canvas,"draw_menu"),
          "Submenu must show focused tool index")
    check("canvas_draw_str(canvas,117U,y,\">\")" in body(canvas,"draw_menu"),
          "submenu disclosure position changed")
    check("draw_pulse_stats(canvas, app);" in body(canvas,"draw_pulse"),
          "Pulse STATS display lost")
    check('ui_footer_triple(canvas, "vRST"' in
          body(canvas,"draw_pulse_stats") and
          'ui_footer_pair(canvas, "UP", "MAIN", "OK", "LIVE")' in
          body(canvas,"draw_pulse_stats"),
          "Pulse STATS live/hold inverse footer contract missing")
    check('canvas_draw_str(canvas, 3, 49, "DUTY")' in
          body(canvas,"draw_pulse_stats"),
          "Pulse STATS must clear the footer rule")
    for title,name in (("FREQ","draw_frequency"),("PWM","draw_generator"),
                       ("PULSE","draw_pulse")):
        check(f'ui_draw_header(canvas, "{title}")' in body(canvas,name),
              name+": shared heading regression")
    for path,signature in (
        ("src/labmate_dashboard_screen.c","labmate_dashboard_screen_draw"),
        ("src/labmate_doctor_screen.c","labmate_doctor_screen_draw"),
    ):
        t=src(path)
        for component in ("ui_draw_header(", "ui_footer_pair("):
            if signature=="labmate_doctor_screen_draw" and component=="ui_footer_pair(":
                continue
            check(component in t,path+" missing "+component)
        if signature=="labmate_doctor_screen_draw":
            check("ui_footer_triple(" in t,path+" missing controls")
    scope=src("src/labmate_scope_display.c")
    check("labmate_scope_ui_header(" in scope and
          "labmate_scope_ui_footer(" in scope,
          "Scope's dedicated plot geometry requires independent title/footer")
    nav=src("src/labmate_navigation.c")
    check('"MEASURE", "OUTPUT", "RECORDS", "COMM", "INFO"' in nav,
          "historical five-group order changed")
    check("LabMateToolDashboard" in nav and "LabMateToolDoctor" in nav,
          "Ultimate tools missing")
    print(f"V20 APP-WIDE UI SOURCE CONTRACT PASS: {count} legacy renderers + "
          "Doctor, Dashboard and dedicated Scope chrome; "
          "both prior special footers migrated into shared inverse chrome. "
          "PIXEL TEST AND DEVICE STILL PENDING")

if __name__=="__main__":
    main()
