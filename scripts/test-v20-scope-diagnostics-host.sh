#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
      -fsanitize=address,undefined -fno-omit-frame-pointer \
      -I"$root/src" "$root/tests/test_v20_scope_diagnostics_current.c" \
      "$root/src/labmate_doctor_symptoms.c" \
      "$root/src/labmate_scope_period_stats.c" \
      "$root/src/labmate_scope_compare.c" \
      -o "$tmp/diagnostics-$cc"
    "$tmp/diagnostics-$cc"
done
echo "E11 CURRENT SCOPE METRICS/SYMPTOMS PASS | historical MAD output RETIRED; DEVICE UNPROVEN"
