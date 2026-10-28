#!/usr/bin/env python3
"""E11 final UI source contract audit, NOT a real framebuffer/device test.

The nine pre-pixel renderer fixtures are historical and not admissible as
release proof. This checks the production bodies against *current* semantics
for COMM/RECORDS/LOGGER/BUTTON/ALERTS/FREQ/PULSE/PWM/MENU, without editing them.
"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent.parent
def read(p): return (ROOT/p).read_text(encoding="utf-8")
def fail(msg): raise AssertionError(msg)
def require(ok,msg):
    if not ok: fail(msg)
def body(path,name):
    s=read(path)
    m=re.search(r'(?m)^(?:static\s+)?void\s+'+re.escape(name)+r'\s*\(',s)
    require(m is not None, f"{path}: missing {name}")
    op=s.index("{",m.end()); depth=0
    for i in range(op,len(s)):
        if s[i]=="{": depth+=1
        if s[i]=="}":
            depth-=1
            if depth==0: return s[m.start():i+1]
    fail(f"{name}: unbalanced")
def contains(text,terms,group):
    for t in terms: require(t in text,f"{group}: missing {t}")
def excludes(text,terms,group):
    for t in terms: require(t not in text,f"{group}: unexpected {t}")

# Every renderer remains passive. The existing monitor display has a
# specifically approved presentation-trace update; it is not in this set.
names={
 "src/labmate_uart_ui.c":("draw_uart",),
 "src/labmate_i2c_ui.c":("draw_i2c",),
 "src/labmate_onewire_ui.c":("draw_onewire",),
 "src/labmate_ui_screens.c":(
   "draw_profiles","draw_history","draw_history_detail",
   "draw_logger","draw_button","draw_alerts",
   "draw_frequency","draw_pulse","draw_generator","draw_menu"),
}
draws={}
for path,items in names.items():
    for name in items:
        b=body(path,name);draws[name]=b
        excludes(b,("furi_hal_gpio_", "storage_file_write(",
                    "furi_hal_resource_lease_", "labmate_capture_start(",
                    "labmate_capture_stop_all(", "frequency_tim2_enable(",
                    "labmate_event_counter_start(", "furi_delay_ms("),name)

uart=draws["draw_uart"]
contains(uart,(
 "uart->blocked ? \"BUSY\"","uart->invalid_baud ? \"BAUD\"",
 "uart->dropped ? \"DROP\"","uart->rx_errors ? \"ERR\"",
 "uart->active ? \"RUN\" : \"STOP\"",
 "labmate_comm_ui_header(","ui_kit_stat_row(",
 "uart->tx_editing","uart->rx_total == 0U",
 "UiKitKeyOk, \"Send\"","UiKitKeyOk, \"Stop\"",
 "UiKitKeyOk, \"Start\"","UiKitKeyLeftRight, \"Baud\"",
 ),"UART")
i2c=draws["draw_i2c"]
contains(i2c,(
 "labmate_i2c_runtime_snapshot(","LabMateI2cRuntimeApiMissing",
 "LabMateI2cRuntimeBusy","LabMateI2cRuntimeScanning",
 "LabMateI2cRuntimeResults","LabMateI2cRuntimeNoDevices",
 "LabMateI2cRuntimeCancelled","LabMateI2cRuntimeFailed",
 "\"FW API\"","\"BUSY\"","\"RUN\"","\"DONE\"","\"NONE\"",
 "\"STOP\"","\"ERR\"","\"REAL ACK RESULTS\"",
 "\"NO ACKS / CHECK BUS\"","\"NO UNSAFE BUS LOCK\"",
 "i < result.row_count && i < 4U","UiKitKeyOk, scanning ? \"Stop\" : \"Scan\"",
 ),"I2C")
wire=draws["draw_onewire"]
contains(wire,(
 "s->has_temperature","s->temperature_tenths >= -550",
 "s->temperature_tenths <= 1250","s->resolution_bits >= 9U",
 "s->resolution_bits <= 12U","LabMateOneWireHwMeasured",
 "valid_temperature ? \"DONE\" : \"ERR\"",
 "LabMateOneWireHwNoSensor","LabMateOneWireHwBusy",
 "LabMateOneWireHwDataError","LabMateOneWireHwPowerCheck",
 "LabMateOneWireHwStopped","\"EXTERNAL VDD ONLY\"",
 "UiKitKeyOk, active ? \"Stop\" : \"Read\"",
 ),"1-Wire")

records=["draw_profiles","draw_history","draw_history_detail"]
for name in records:
    contains(draws[name],("labmate_pixel_header(",),name)
contains(draws["draw_profiles"],(
 "ui_kit_confirmation(", "app->profile_", "\"CRC\"",
 "\"SD ERR\"","\"PWM ON\"","labmate_pixel_keys(",
 ),"Profiles")
contains(draws["draw_history"],(
 "ui_kit_confirmation(","app->history_busy",
 "app->history_error", "app->history_delete_mode",
 "labmate_pixel_keys(", "\"Delete\"",
 ),"History")
contains(draws["draw_history_detail"],(
 "\"READ ONLY\"","\"SD READ ERROR\"","UiKitKeyBack",
 ),"Log View")

logger=draws["draw_logger"]
contains(logger,(
 "labmate_pixel_header(","app->logger_recording",
 "\"NO VALID PULSE\"","\"NO VALID FREQ\"",
 "\"SD BUSY - WAIT\"","UiKitKeyOk, \"Stop\"",
 "UiKitKeyOk, \"Record\"",
 ),"Logger")
button=draws["draw_button"]
contains(button,(
 "labmate_pixel_header(","app->capture_release_fault",
 "app->capture_blocked","\"PC1 / PULLUP\"",
 "\"SETTLING\"","\"OPEN\"","\"CLOSED\"",
 "labmate_pixel_keys(",
 ),"Button")
alerts=draws["draw_alerts"]
contains(alerts,(
 "labmate_pixel_header(","ui_kit_panel(",
 "\"DISARMED\"","\"ALERT LATCHED\"",
 "\"WAITING FOR INPUT\"","\"BELOW LIMIT\"",
 "UiKitKeyDown, \"Ack\"","UiKitKeyOk, \"Off\"",
 ),"Alerts")
frequency=draws["draw_frequency"]
contains(frequency,(
 "ui_kit_back_title(","ui_kit_sparkline(",
 "\"Busy\"","\"Held\"","\"No signal\"","\"PB3\"","\"PC1\"",
 ),"Frequency")
pulse=draws["draw_pulse"]
contains(pulse,(
 "ui_kit_back_title(","\"Busy\"","\"Held\"",
 "\"Live\"","\"No signal\"",
 ),"Pulse")
pwm=draws["draw_generator"]
contains(pwm,(
 "ui_kit_back_title(","\"PA7\"",
 "\"Busy\"","\"Editing\"","\"Running\"",
 ),"PWM")
menu=draws["draw_menu"]
contains(menu,(
 "ui_kit_brand(","ui_kit_carousel_card(",
 "ui_kit_list_row(","labmate_nav_group_size(",
 "labmate_nav_first_visible(","ui_kit_pill(",
 "ui_kit_center_text(",
 ),"Menu")
excludes(menu,("labmate_menu_tile_","ui_draw_header(","ui_footer_triple("),"Menu")

# Look for key footer geometry and title/chip collision checks in the actual
# shared UI header, but do not pretend this is the device's font raster.
chrome=read("src/labmate_pixel_ui.h")
contains(chrome,(
 "canvas_string_width(canvas, title)",
 "canvas_string_width(canvas, status)",
 "canvas_draw_rbox(","canvas_draw_rframe(",
 "ui_kit_key_hint(canvas, 4U,",
 "ui_kit_key_hint(canvas, 66U,",
 ),"Shared pixel chrome")

print("E11 CURRENT UI SOURCE CONTRACT PASS: 13 production renderer bodies")
print("COVERAGE: COMM (UART/I2C/1W), records, logger, button/alerts,")
print("frequency/pulse/PWM, root menu, shared measured pixel header")
print("NOT A PIXEL RASTER, TIMER/GPIO, OLD-NINE-SUITE OR DEVICE PASS")
