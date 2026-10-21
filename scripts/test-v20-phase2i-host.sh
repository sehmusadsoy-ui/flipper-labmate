#!/bin/sh
# Phase 2I: source-linked PB3/TIM2 successful publication accounting.
# All actions are local read-only C tests; NO firmware/device/SD writes.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-phase2i.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
source="$root/src/labmate_measurements.c"
start="$root/src/labmate_frequency_capture.c"
internal="$root/src/labmate_internal.h"
grep -Fq '#include "labmate_high_gate_audit.h"' "$internal"
grep -Fq 'LabMateHighGateAudit frequency_high_gate_audit;' "$internal"
test "$(grep -Fc 'labmate_high_gate_audit_record(' "$source")" -eq 1
test "$(grep -Fc 'labmate_high_gate_audit_reset(' "$start")" -eq 1
grep -Fq 'if(gate == LabMateHighGatePublish) {' "$source"
grep -Fq '&app->frequency_high_gate_audit, gate,' "$source"
grep -Fq 'app->frequency_valid = false;' "$source"
# Verify that native high-start resets ONLY AFTER configure succeeds and
# BEFORE the real hardware counter is enabled. No reinitialization in redraw.
awk '/^void labmate_frequency_high_start[(]/ {on=1} /^void labmate_frequency_low_stop[(]/ {on=0} on {print}' "$start" > "$tmp/start.inc"
grep -Fq 'if(!labmate_frequency_tim2_configure())' "$tmp/start.inc"
grep -Fq 'labmate_high_gate_audit_reset(&app->frequency_high_gate_audit);' "$tmp/start.inc"
grep -Fq 'labmate_frequency_tim2_enable();' "$tmp/start.inc"
awk '
  /if\(!labmate_frequency_tim2_configure\(\)\)/ {acquire=NR}
  /labmate_high_gate_audit_reset\(&app->frequency_high_gate_audit\);/ {reset=NR}
  /labmate_frequency_tim2_enable\(\);/ {enable=NR}
  END {if(!(acquire>0 && acquire<reset && reset<enable)) exit 1}
' "$tmp/start.inc"
awk '
  /if\(gate == LabMateHighGatePublish\)/ {publish=NR}
  /labmate_high_gate_audit_record\(/ {audit=NR}
  /app->frequency_millihz = sample_millihz;/ {if(!value)value=NR}
  END {if(!(publish>0 && publish<audit && audit<value)) exit 1}
' "$source"
for cc in gcc clang; do
  command -v "$cc" >/dev/null 2>&1 || { echo "Missing compiler $cc" >&2; exit 2; }
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" "$root/src/labmate_frequency_gate.c" \
    "$root/tests/test_v20_phase2i_high_gate_audit.c" -o "$tmp/high-$cc"
  "$tmp/high-$cc"
done
echo "Phase2I SOURCE LINKED HOST PASS: successful native TIM2 publishes only"
