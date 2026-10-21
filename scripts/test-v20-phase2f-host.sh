#!/bin/sh
# Phase 2F: host-only source extraction, no Flipper hardware or SD writes.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-phase2f.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
src="$root/src/labmate_measurements.c"
awk '/^static bool labmate_frequency_low_take_period[(]/ {capture=1} capture {print; if($0=="}") exit}' \
  "$src" > "$tmp/take_period.inc"
test -s "$tmp/take_period.inc"
# Ensure tested helper is actually used by the LIVE LOW/PC1 measurement path.
grep -Fq 'if(labmate_frequency_low_take_period(app, &period_cycles))' "$src"
for cc in gcc clang; do
  command -v "$cc" >/dev/null 2>&1 || { echo "Missing $cc" >&2; exit 2; }
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$tmp" "$root/tests/test_v20_phase2f_low_mailbox.c" -o "$tmp/low-$cc"
  "$tmp/low-$cc"
done
