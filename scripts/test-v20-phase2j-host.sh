#!/bin/sh
# Pure host C + live source invariants; never accesses Flipper / SD / firmware.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-phase2j.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
irq="$root/src/labmate_pulse_capture.c"
measure="$root/src/labmate_measurements.c"
internal="$root/src/labmate_internal.h"
grep -Fq '#include "labmate_pulse_pair_audit.h"' "$internal"
grep -Fq 'LabMatePulsePairAudit pulse_pair_audit;' "$internal"
grep -Fq 'LabMatePulsePairObservation pulse_pair_last_observation;' "$internal"
test "$(grep -Fc 'labmate_pulse_pair_note(' "$irq")" -eq 1
test "$(grep -Fc 'labmate_pulse_pair_reset(' "$irq")" -eq 1
test "$(grep -Fc 'labmate_pulse_pair_discard_partial(' "$irq")" -eq 1
grep -Fq 'new_high=true;' "$irq"
grep -Fq 'new_low=true;' "$irq"
grep -Fq 'labmate_pulse_pair_copy_locked(' "$measure"
grep -Fq 'app->pulse_pair_last_observation = pair_observation;' "$measure"
grep -Fq 'labmate_pulse_pair_discard_partial(&app->pulse_pair_audit);' "$measure"
# Source static preflight: the IRQ pair note is inside the callback,
# and reset must follow lease/callback success but precede IRQ enable.
awk '/^static void pulse_gpio_callback[(]/ {on=1} /^#endif \/\* matching firmware/ {on=0} on {print}' "$irq" > "$tmp/callback.inc"
grep -Fq 'labmate_pulse_pair_note(' "$tmp/callback.inc"
awk '/^void labmate_pulse_capture_start[(]/ {on=1} on {print}' "$irq" > "$tmp/start.inc"
awk '
  /furi_hal_gpio_try_add_int_callback[(]/ {acquired=NR}
  /labmate_pulse_pair_reset[(]/ {reset=NR}
  /furi_hal_gpio_enable_int_callback[(]/ {enabled=NR}
  END {if(!(acquired>0 && acquired<reset && reset<enabled)) exit 1}
' "$tmp/start.inc"
for cc in gcc clang; do
  command -v "$cc" >/dev/null 2>&1 || { echo "Missing $cc" >&2; exit 2; }
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" "$root/tests/test_v20_phase2j_pulse_pairs.c" -o "$tmp/test-$cc"
  "$tmp/test-$cc"
done
echo "Phase2J source-linked Pulse pair host gate PASS"
