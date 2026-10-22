#!/bin/sh
# Host-only: extracts unmodified Frequency/Pulse/PWM bodies from the real repo.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-ui05d.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
extract() {
  fn="$1";dest="$2"
  awk -v sig="$fn" 'index($0,sig)==1 {copy=1} copy {print; if($0=="}") exit}' \
    "$root/src/labmate_ui_screens.c" > "$tmp/$dest"
  test -s "$tmp/$dest"
}
extract 'static void frequency_format_compact(' frequency_compact.inc
extract 'static void frequency_format_edges(' frequency_edges.inc
extract 'void draw_frequency(' draw_frequency.inc
extract 'void draw_generator(' draw_generator.inc
extract 'static void pulse_ui_format_value(' pulse_format.inc
extract 'static void pulse_ui_metric(' pulse_metric.inc
extract 'static void draw_pulse_stats(' pulse_stats.inc
extract 'void draw_pulse(' draw_pulse.inc
# Source-link ALL shared footer paths used by Frequency/Pulse/PWM.
# The pair footer must be the production implementation; a mock would
# conceal background inversion errors in Pulse STATS HOLD mode.
for spec in \
    'static bool ui_format_key(:pair_validator.inc' \
    'void ui_key(:pair_key.inc' \
    'static void ui_footer_action(:pair_action.inc' \
    'void ui_footer_pair(:pair_footer.inc'
do
  signature=${spec%%:*}
  target=${spec#*:}
  awk -v sig="$signature" 'index($0,sig)==1 {copy=1} copy {print; if($0=="}") exit}' \
    "$root/src/labmate_ui_primitives.c" > "$tmp/$target"
  test -s "$tmp/$target"
done
# Source-link the newly shared footer: these are the actual UI primitive
# function bodies; do not replace them with a lookalike host implementation.
awk -v sig='static bool ui_footer_triple_label_valid(' \
  'index($0,sig)==1 {copy=1} copy {print; if($0=="}") exit}' \
  "$root/src/labmate_ui_primitives.c" > "$tmp/triple_validator.inc"
awk -v sig='void ui_footer_triple(' \
  'index($0,sig)==1 {copy=1} copy {print; if($0=="}") exit}' \
  "$root/src/labmate_ui_primitives.c" > "$tmp/triple_footer.inc"
test -s "$tmp/triple_validator.inc"
test -s "$tmp/triple_footer.inc"
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" -I"$tmp" "$root/tests/test_v20_ui05d_measurement.c" -o "$tmp/ui05d-$cc"
  "$tmp/ui05d-$cc"
done
