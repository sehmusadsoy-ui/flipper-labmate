#!/usr/bin/env python3
"""Current E11 source contract, with explicit historical retirement boundaries.

Preserved old checks and replacements are listed in
docs/development/V20_E11_CURRENT_ACCEPTANCE_COVERAGE.md. Source inspection is
not hardware/raster evidence, nor proof that every historical feature exists.
"""
from pathlib import Path
import re
import runpy

ROOT=Path(__file__).resolve().parent.parent
def read(path): return (ROOT/path).read_text(encoding='utf-8')
def require(ok,message):
    if not ok: raise AssertionError(message)
def function(text,name):
    m=re.search(r'(?m)^(?:static\s+)?void\s+'+re.escape(name)+r'\s*\(',text)
    require(m is not None,'missing renderer '+name)
    start=text.index('{',m.end()); depth=0
    for end in range(start,len(text)):
        if text[end]=='{':depth+=1
        elif text[end]=='}':
            depth-=1
            if depth==0:return text[m.start():end+1]
    raise AssertionError('unterminated '+name)

manifest=read('application.fam')
for token in ('appid="labmate"','name="LabMate Ultimate"','fap_version="2.0"','sources=["src/*.c"]'):
    require(token in manifest,'manifest '+token)
require('#define LABMATE_VERSION_TEXT "v2.0"' in read('src/labmate_internal.h').splitlines(),
        'expected v2.0 display version')
require('v1.9DEV' not in read('src/labmate_internal.h')+read('src/labmate_ui_screens.c'),'legacy display version')
nav=read('src/labmate_navigation.c')
require('"MEASURE", "OUTPUT", "RECORDS", "COMM", "SETTINGS"' in nav,'current category labels')
header=read('src/labmate_navigation.h')
expected=['Gpio','Frequency','Pulse','Generator','Logger','History','About','Profiles',
          'Counter','Button','Alerts','Uart','OneWire','I2c','Scope','Doctor','Dashboard','Count']
enum=header[header.index('typedef enum {'):header.index('} LabMateTool;')]
ids=re.findall(r'^\s*(LabMateTool\w+)(?:\s*=\s*[^,\n]+)?[,]\s*(?:/\*.*\*/|//.*)?$',enum,re.M)
require(ids[:len(expected)]==['LabMateTool'+x for x in expected],'stable persisted tool IDs')
require('LabMateToolInvalid' in header,'invalid sentinel')
require('#define LABMATE_INFO_GUIDE_COUNT 17U' in read('src/labmate_info_guides.h'),'17 current tool guides')
require('index < LABMATE_INFO_GUIDE_COUNT ? &guides[index] : NULL' in read('src/labmate_info_guides.c'),
        'guide lookup count/bounds')
for screen in ('LabMateScreenDashboard','LabMateScreenDoctor'):
    require(screen in read('src/labmate_internal.h'),'screen enum '+screen)
    for path in ('src/labmate_input.c','src/labmate_view.c'):
        require('case '+screen+':' in read(path),path+' screen dispatch '+screen)
for tool in ('Doctor','Dashboard'):
    require('case LabMateTool'+tool+':' in read('src/labmate_input_menu.c'),'menu route '+tool)
    require('[LabMateTool'+tool+']' in read('src/labmate_ui_screens.c'),'preserved help table '+tool)

# Current per-screen expectations and passive-I/O constraints are independent
# of historical tile coordinates or header function names.
runpy.run_path(str(ROOT/'scripts/audit-v20-e11-current-ui-contracts.py'),run_name='__main__')
files={
 'src/labmate_ui_screens.c':['draw_menu','draw_gpio','draw_frequency','draw_pulse',
  'draw_generator','draw_logger','draw_counter','draw_button','draw_alerts',
  'draw_history','draw_history_detail','draw_profiles','draw_about'],
 'src/labmate_uart_ui.c':['draw_uart'],
 'src/labmate_i2c_ui.c':['draw_i2c'],
 'src/labmate_onewire_ui.c':['draw_onewire'],
}
for path,names in files.items():
    source=read(path)
    for name in names:
        body=function(source,name)
        for token in ('furi_hal_gpio_','storage_file_write(','furi_hal_resource_lease_try_acquire('):
            require(token not in body,name+' passive I/O contract '+token)
detail=function(read('src/labmate_ui_screens.c'),'draw_history_detail')
for token in ('READ ONLY','UiKitKeyBack','SD READ ERROR'):
    require(token in detail,'read-only log detail '+token)
scope=read('src/labmate_scope_display.c')
for token in ('scope_complete(','LabMateScopeMetricsReady','!m->truncated','ui_kit_pixel_header(',
              'ui_kit_key_hint(', 'UiKitKeyOk'):
    require(token in scope,'dedicated current Scope geometry/validity '+token)
for path in ('src/labmate_dashboard_screen.c','src/labmate_doctor_screen.c',
             'src/labmate_doctor_advice.c','src/labmate_signal_stats.c'):
    source=read(path)
    for token in ('furi_hal_gpio_','furi_hal_bus_','storage_file_write(',
                  'storage_file_open(','furi_hal_resource_lease_try_acquire('):
        require(token not in source,path+' read-only presenter '+token)
for path in ('src/labmate_doctor_frequency_bridge.c','src/labmate_doctor_pulse_bridge.c'):
    source=read(path)
    for token in ('labmate_evidence_session_finish','labmate_dashboard_store_ingest','labmate_signal_stats_record'):
        require(token in source,path+' sealed data flow '+token)
for path in ('src/labmate_scope_bridge.c','src/labmate_event_counter.c','src/labmate_logger_storage.c'):
    require('labmate_dashboard_store_ingest' in read(path),path+' dashboard provenance')
require('labmate_snapshot_v1_can_display_measurement' in read('src/labmate_signal_stats.c'),'quality gate')
require('LABMATE_SIGNAL_STATS_MAX_SESSIONS' in read('src/labmate_signal_stats.c'),'bounded statistics')
for path in ('src/labmate_doctor_frequency_bridge.c','src/labmate_doctor_pulse_bridge.c',
             'src/labmate_scope_bridge.c','src/labmate_event_counter.c','src/labmate_logger_storage.c'):
    require('labmate_dashboard_store_clear_source' in read(path),path+' source isolation')
dashboard=read('src/labmate_dashboard_screen.c')
for token in ('labmate_dashboard_store_read_measurement','labmate_signal_stats_read',
              'FREQ','PULSE','SCOPE','COUNT','LOGGER','a->dashboard_evidence','HISTORICAL ONLY'):
    require(token in dashboard,'dashboard sealed source/label '+token)
for token in ('NO SEALED DATA','CAPTURE + STOP','NO EDGES SEEN'):
    require(token in read('src/labmate_doctor_advice.c'),'advisory evidence '+token)
require('labmate_doctor_result_draw' in read('src/labmate_doctor_screen.c'),'current Doctor result UI')
for path,tokens in {
 'src/labmate_scope_bridge.c':('labmate_scope_native_reinit_safe',),
 'src/labmate_event_counter.c':('labmate_frequency_tim2_lease_pending','counter_run_start_total'),
 'src/labmate_logger_storage.c':('app->logger_session_pin = app->capture_pin_index',
   'app->logger_session_source = app->logger_source','labmate_logger_dashboard_finalize'),
}.items():
    for token in tokens:require(token in read(path),path+' session identity '+token)

# Removal is an explicit supported-scope boundary, never an emulated PASS.
for name in ('labmate_level_witness.c','labmate_level_witness.h','labmate_scope_diagnostics.c',
             'labmate_scope_diagnostics.h','labmate_menu_grid.h'):
    require(not (ROOT/'src'/name).exists(),'historical feature reintroduced without coverage review '+name)
for p in (ROOT/'src').iterdir():
    if p.suffix in ('.c','.h'):
        require(not re.search(r'\b(?:LabMateLevelWitness|labmate_level_(?:begin|observe|finish|assess|invalidate))\b',p.read_text()),
                'retired level witness referenced '+p.name)
print('CURRENT E11 SOFTWARE SOURCE CONTRACT PASS: 16 passive renderers, stable IDs, sealed data flow')
print('RETIRED / UNPROVEN: GPIO LevelWitness polling certification; old Scope MAD output; old tile-grid raster')
print('NO DEVICE, SD DURABILITY, OOM RUNTIME, CALIBRATION OR PHYSICAL-ONLY COMPLETION CLAIM')
