#!/usr/bin/env python3
"""v1.8 coordinator structural and safety regression guard (no Flipper hardware).

Verify ownership boundaries and preserve v1.7 behavior while migrating
input handling, GPIO session transitions, redraw and deferred SD work.
Hardware/timing parity must still be tested on a physical Flipper.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
read = lambda name: (SRC / name).read_text(encoding="utf-8")
main = read("labmate.c")
router = read("labmate_input.c")
session = read("labmate_capture_session.c")
view = read("labmate_view.c")
deferred = read("labmate_deferred.c")
work_header = read("labmate_deferred.h")
screens = {
    "Menu": "labmate_input_menu.c",
    "Profiles": "labmate_input_profiles.c",
    "History": "labmate_input_history.c",
    "HistoryDetail": "labmate_input_history.c",
    "About": "labmate_input_menu.c",
    "Alerts": "labmate_input_output.c",
    "Button": "labmate_input_measure.c",
    "Counter": "labmate_input_measure.c",
    "Logger": "labmate_input_history.c",
    "Gpio": "labmate_input_measure.c",
    "Frequency": "labmate_input_measure.c",
    "Pulse": "labmate_input_measure.c",
    "Generator": "labmate_input_output.c",
}
handlers = [read(p) for p in sorted(set(screens.values()))]
assert len(main.splitlines()) < 250, "labmate.c must be a thin coordinator"
assert len(router.splitlines()) < 90, "input router should not regrow"
assert all(len(s.splitlines()) < 220 for s in handlers), "input handler too large"
assert 'sources=["src/*.c"]' in (ROOT / "application.fam").read_text()
assert 'app->capture_owner = LabMateCaptureNone;' in main
assert 'labmate_capture_stop_all(app);' in main
assert 'labmate_generator_stop(app);' in main
assert 'labmate_logger_storage_stop(app);' in main
assert 'labmate_history_close(app);' in main

# One and only one physical tool entry mapping per original enum value.
for name in screens:
    needle = f"case LabMateScreen{name}:"
    assert router.count(needle) == 1, f"Unrouted screen {name}"
for name in ("Gpio", "Frequency", "Pulse", "Counter", "Button", "Alerts",
             "Generator", "Logger", "History", "About", "Profiles"):
    assert sum(x.count(f"case LabMateTool{name}:") for x in handlers) == 1, (
        f"Missing or duplicate tool launch: {name}"
    )
assert 'event.type != InputTypeShort && event.type != InputTypeLong' in router
assert 'event.type != InputTypePress' in router
assert 'app->generator_skip_entry_ok = true;' in read("labmate_input_menu.c")
assert 'if(app->generator_skip_entry_ok && event.key == InputKeyOk)' in read("labmate_input_output.c")
assert 'labmate_generator_begin_custom_edit(app)' in read("labmate_input_output.c")
assert 'labmate_generator_stop(app);' in read("labmate_input_output.c")

# All STOP paths go through a single capture teardown; PA7 PWM lives elsewhere.
assert len(re.findall(r"(?m)^void labmate_capture_stop_all\\(", session)) == 1
assert "labmate_event_counter_stop(app);" in session
assert "labmate_button_capture_stop(app);" in session
assert "labmate_capture_all_stopped(" in session
assert "labmate_capture_stop_all(app);" in read("labmate_input_measure.c")
assert "labmate_capture_stop_all(app);" in main
assert "furi_hal_pwm_" not in session
assert "furi_hal_pwm_" not in router
assert all("furi_hal_pwm_" not in s for s in handlers)

# Drawing renders state and throttles repaint; it does not mutate peripherals/SD.
assert "void labmate_view_render_callback(" in view
assert "void labmate_redraw_maybe(" in view
for forbidden in ("storage_file_", "storage_common_", "labmate_generator_start(",
                  "labmate_generator_stop(", "furi_hal_gpio_"):
    assert forbidden not in view, f"GUI may not perform {forbidden}"

# Profiles/History/Logger queue requests while mutex is held, and the worker
# commits outside the UI lock. Guard the important ordering invariant.
assert "labmate_input_dispatch(app, status, event, &work);" in main
assert "labmate_deferred_prepare(app, &work);" in main
assert re.search(r"furi_mutex_release\\(app->mutex\\);\\s*"
                 r"labmate_deferred_execute\\(app, &work, viewport\\);", main)
assert "storage_file_write(app->logger_file, work->pending_log_row, bytes)" in deferred
assert "storage_file_sync(app->logger_file)" in deferred
assert "labmate_profile_sd_save(" in deferred
assert "labmate_profile_sd_load(" in deferred
assert "labmate_history_delete_file(work->history_delete_id)" in deferred
assert "app->profile_confirm = true;" in read("labmate_input_profiles.c")
assert "work->history_delete_requested = true;" in read("labmate_input_history.c")
assert "labmate_history_read_step(app);" in deferred
assert "app->generator_running ||" in read("labmate_input_profiles.c")
assert "app->capture_owner != LabMateCaptureNone ||" in read("labmate_input_profiles.c")
assert "app->logger_recording" in read("labmate_input_profiles.c")
for name in ("pending_log_row", "proposed_profiles", "proposed_copy",
             "history_delete_id", "history_delete_selected",
             "logger_start_requested", "profiles_save_requested"):
    assert name in work_header, f"Missing request snapshot {name}"
for forbidden in ("storage_file_write(", "storage_file_open(", "storage_file_close(",
                  "labmate_profile_sd_save(", "labmate_profile_sd_load("):
    assert forbidden not in main and forbidden not in router
    assert all(forbidden not in s for s in handlers), (
        f"SD operation leaked into mutex-protected input handling: {forbidden}"
    )

print("LabMate v1.8 coordinator PASS: 13 screen routes, 11 tools, ownership, "
      "PWM safeguards, deferred I/O, bounded coordinator")
