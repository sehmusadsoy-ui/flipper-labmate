#!/usr/bin/env python3
"""Fail-closed static guard for the integrated Button STOP/RESUME lifecycle.

This does not claim physical Flipper validation. Portable state behavior
is additionally exercised by tests/test_button_logic.c.inc in CI.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
read = lambda name: (root / name).read_text(encoding="utf-8")
capture = read("src/labmate_button_capture.c")
logic = read("src/labmate_button_logic.c")
header = read("src/labmate_internal.h")
inputs = read("src/labmate_input_measure.c")
ui = read("src/labmate_ui_screens.c")
tests = read("tests/test_button_logic.c.inc")


def section(source: str, start: str, end: str) -> str:
    assert source.count(start) == 1, f"Missing/duplicate {start}"
    rest = source.split(start, 1)[1]
    assert end in rest, f"Missing terminator after {start}"
    return rest.split(end, 1)[0]


def need(condition: bool, message: str) -> None:
    assert condition, message


reset = section(capture, "void labmate_button_capture_reset(", "void labmate_button_capture_change_quiet(")
start = section(capture, "void labmate_button_capture_start(", "void labmate_button_capture_poll(")
stop = section(capture, "void labmate_button_capture_stop(", "\n}")
resume = section(logic, "void labmate_button_state_resume(", "void labmate_button_edge(")
input_button = section(inputs, "void labmate_input_button(", "void labmate_input_counter(")

need("bool button_session_started;" in header, "session flag absent")
need("if(app->button_active) return;" in reset, "reset must not clear live capture")
need("app->button_session_started = false;" in reset, "explicit RESET must drop resumable session")
need("const bool resume = app->button_session_started;" in start, "START/RESUME distinction missing")
need("if(resume)" in start and "labmate_button_state_resume(" in start,
     "restart must preserve state on RESUME")
need("labmate_button_state_init(" in start and "else {" in start,
     "fresh START must begin with empty counters")
need("app->button_session_started = true;" in start and
     "app->button_active = true;" in start, "start must arm session")
need("labmate_button_state_init(" not in stop and
     "labmate_button_capture_reset(" not in stop, "STOP must not erase results")
need("app->button_session_started = false;" not in stop,
     "STOP must keep resumable session")
need("state->pending = false;" in resume and
     "state->press_started = false;" in resume,
     "restart must discard incomplete edge/hold")
for preserved in ("presses", "releases", "rejected_glitches",
                  "last_bounce_cycles", "last_settle_ticks", "last_hold_ticks"):
    need(f"state->{preserved} =" not in resume,
         f"resume is erasing previous {preserved}")
need("if(app->button_active)" in input_button and
     "labmate_button_capture_stop(app);" in input_button and
     "labmate_button_capture_start(app);" in input_button,
     "OK toggle must call STOP/START owner")
need("event.key == InputKeyUp" in input_button and
     "labmate_button_capture_reset(app);" in input_button,
     "UP must remain explicit reset key")
need('app->button_session_started ? "RESUME" : "START"' in ui,
     "STOP/RESUME action not displayed")
need("labmate_button_state_resume(&state" in tests,
     "portable resume regression missing")
print("v1.8.1 Button Analyzer lifecycle guard PASS: STOP holds results, RESUME preserves counters")
