#!/usr/bin/env python3
"""Guard v1.8 STOP/RESUME without regressing reset/capture ownership."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
source = (SRC / "labmate_event_counter.c").read_text()
input_menu = (SRC / "labmate_input_menu.c").read_text()
input_measure = (SRC / "labmate_input_measure.c").read_text()
ui = (SRC / "labmate_ui_screens.c").read_text()
header = (SRC / "labmate_internal.h").read_text()
math = (SRC / "labmate_counter_math.c").read_text()

start = source.split("void labmate_event_counter_start(", 1)[1].split(
    "void labmate_event_counter_poll(", 1)[0]
stop = source.split("void labmate_event_counter_stop(", 1)[1].split(
    "void labmate_event_counter_reset(", 1)[0]
reset = source.split("void labmate_event_counter_reset(", 1)[1]
assert "app->counter_total = 0U" not in start
assert "app->counter_elapsed_seconds = 0U" not in start
assert "app->counter_last_hw = 0U;" in start
assert "labmate_capture_can_start(app, LabMateCaptureCounter)" in start
assert "labmate_frequency_tim2_disable();" in stop
assert "labmate_event_counter_poll(app);" in stop
assert "labmate_frequency_tim2_shutdown();" in stop
assert "app->counter_elapsed_ticks = labmate_counter_add_ticks(" in stop
assert "app->counter_total = 0U;" in reset
assert "app->counter_elapsed_ticks = 0U;" in reset
assert "if(app->counter_active) return;" in reset
assert "labmate_event_counter_reset(app);" in input_menu
assert "labmate_event_counter_start(app);" in input_measure
assert "labmate_event_counter_stop(app);" in input_measure
assert "labmate_event_counter_reset(app);" in input_measure
assert 'paused ? "RESUME" : "START"' in ui
assert "uint64_t counter_elapsed_ticks;" in header
assert "labmate_counter_add_ticks(" in math
assert "labmate_counter_elapsed_seconds(" in math
assert "LL_TIM_" not in math and "furi_hal_" not in math and "storage_" not in math
poll = source.split("void labmate_event_counter_poll(", 1)[1].split(
    "void labmate_event_counter_stop(", 1)[0]
assert "labmate_counter_add_ticks(app->counter_elapsed_ticks, active_ticks)" in poll
assert "labmate_counter_elapsed_seconds(total_ticks, tick_frequency)" in poll
print("v1.8 Counter STOP/RESUME static guard PASS")
