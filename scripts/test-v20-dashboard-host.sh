#!/bin/sh
# Read-only GCC+Clang projection test; no Flipper, USB or CSV writes.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
     -fsanitize=address,undefined -fno-omit-frame-pointer -I"$root/src" \
     "$root/tests/test_v20_dashboard_sealed.c" \
     "$root/src/labmate_dashboard_store.c" "$root/src/labmate_snapshot.c" \
     -o "$tmp/dashboard-$cc"
  "$tmp/dashboard-$cc"
done
python3 - "$root" <<'PY'
import sys
from pathlib import Path
r=Path(sys.argv[1])
code=(r/'src/labmate_dashboard_screen.c').read_text()
for text in ['FREQ','PULSE','SCOPE','COUNT','LOGGER',
             'labmate_dashboard_store_read_measurement',
             'SEALED / NOT LIVE', 'labmate_signal_stats_read']:
    assert text in code, text
for path,expr in [
    ('src/labmate_scope_bridge.c','labmate_dashboard_store_ingest'),
    ('src/labmate_event_counter.c','labmate_dashboard_store_ingest'),
    ('src/labmate_logger_storage.c','labmate_dashboard_store_ingest'),
    ('src/labmate_doctor_frequency_bridge.c','labmate_signal_stats_record'),
    ('src/labmate_doctor_pulse_bridge.c','labmate_signal_stats_record')]:
    assert expr in (r/path).read_text(),path
app=(r/'src/labmate_internal.h').read_text()
assert '#define LABMATE_VERSION_TEXT "v2.0DEV"' in app
fam=(r/'application.fam').read_text()
assert 'fap_version="2.0"' in fam
assert 'LabMateToolDashboard' in (r/'src/labmate_navigation.c').read_text()
print('V20 DASHBOARD SOURCE WIRING AUDIT PASS | STATIC; NOT RUNTIME')
PY
echo "V20 DASHBOARD HOST PASS GCC+Clang (NO E11/DEVICE CLAIM)"
