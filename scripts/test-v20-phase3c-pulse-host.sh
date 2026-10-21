#!/bin/sh
# Phase3C: pure conservative real-Pulse candidate gate + source callsite checks.
# NO firmware/USB/Flipper/SD writes. Full native bridge needs E11 FAP compile.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-phase3c.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
grep -Fq 'labmate_doctor_pulse_started(app);' "$root/src/labmate_pulse_capture.c"
grep -Fq 'labmate_doctor_pulse_prepare_stop(app);' "$root/src/labmate_input_measure.c"
grep -Fq 'labmate_doctor_pulse_finish_stop(app);' "$root/src/labmate_input_measure.c"
grep -Fq 'labmate_doctor_pulse_abandon(app);' "$root/src/labmate_input_measure.c"
grep -Fq 'labmate_evidence_session_finish(' "$root/src/labmate_doctor_pulse_bridge.c"
grep -Fq 'labmate_pulse_lease_pending()' "$root/src/labmate_doctor_pulse_bridge.c"
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" "$root/tests/test_v20_phase3c_pulse_policy.c" \
    "$root/src/labmate_doctor_pulse_policy.c" -o "$tmp/pulse-$cc"
  "$tmp/pulse-$cc"
done
echo 'PHASE3C PULSE POLICY HOST PASS: GCC+Clang; REAL E11 DEVICE NOT TESTED'
