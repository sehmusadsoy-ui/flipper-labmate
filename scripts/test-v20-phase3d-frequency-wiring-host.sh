#!/bin/sh
# Phase 3D-B: nonhardware SOURCE-LINKED ordering and ownership contract.
# The E11 FAP compile remains mandatory for C/HAL ABI validation.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python3 - "$root" <<'PY'
import sys
from pathlib import Path
r=Path(sys.argv[1])
read=lambda p:(r/p).read_text()
inp=read("src/labmate_input_measure.c")
native=read("src/labmate_frequency_capture.c")
measure=read("src/labmate_measurements.c")
bridge=read("src/labmate_doctor_frequency_bridge.c")
app=read("src/labmate.c")
internal=read("src/labmate_internal.h")
assert 'labmate_doctor_frequency_started(app);' in native
assert native.count('labmate_doctor_frequency_started(app);')==2
assert 'labmate_doctor_frequency_note_low(' in measure
assert 'labmate_doctor_frequency_note_high(app);' in measure
assert 'observed_edges = app->frequency_irq_edges;' in measure
assert 'last_edge_tick = app->frequency_irq_last_tick;' in measure
a=measure.index('    FURI_CRITICAL_ENTER();')
b=measure.index('    FURI_CRITICAL_EXIT();',a)
assert a < measure.index('observed_edges = app->frequency_irq_edges;',a) < b
assert a < measure.index('last_edge_tick = app->frequency_irq_last_tick;',a) < b
assert 'labmate_doctor_frequency_prepare_stop(app);' in inp
assert 'labmate_doctor_frequency_finish_stop(app);' in inp
back=inp.rsplit('event.key == InputKeyBack',1)[1]
p=back.index('labmate_doctor_frequency_prepare_stop(app);')
s=back.index('labmate_capture_stop_all(app);')
f=back.index('labmate_doctor_frequency_finish_stop(app);')
assert p<s<f, "native STOP must occur between prepare and finish"
assert 'labmate_doctor_frequency_abandon(app);' in inp
assert 'app->hold = !app->hold' in inp
assert 'labmate_evidence_session_finish(' in bridge
assert 'labmate_frequency_low_lease_pending()' in bridge
assert 'labmate_frequency_tim2_lease_pending()' in bridge
assert '!a->capture_release_fault && !a->capture_blocked' in bridge
assert 'labmate_doctor_frequency_policy_accept(&c)' in bridge
assert 'a->doctor_frequency_session.sample_fault = true;' in bridge
assert 'a->doctor_frequency_seen_count = o->publications;' in bridge
assert 'a->doctor_frequency_seen_count = audit->publications;' in bridge
assert 'labmate_doctor_frequency_abandon(app)' not in native
assert 'labmate_doctor_frequency_bridge.h' in internal or (
    'labmate_doctor_frequency_policy.h' in internal)
assert 'labmate_evidence_session_init(&app->doctor_frequency_session)' in app
print("PHASE3D FREQUENCY SOURCE-LINKED ORDER/OWNERSHIP AUDIT: PASS")
PY
echo 'HOST ONLY | E11 SDK/FAP/REAL DEVICE NOT TESTED BY THIS AUDIT'
