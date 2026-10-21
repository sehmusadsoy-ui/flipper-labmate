#!/bin/sh
# Phase 2H read-only PC1 mailbox frame and quality gate. No Flipper writes.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-phase2h.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
# Confirm the live code copies the complete audit while IRQs are excluded.
src="$root/src/labmate_measurements.c"
grep -Fq 'labmate_low_mailbox_consume_locked(' "$src"
grep -Fq '&app->frequency_low_mailbox_audit,' "$src"
grep -Fq 'app->frequency_low_last_observation = observation;' "$src"
grep -Fq 'LabMateLowMailboxObservation frequency_low_last_observation;' "$root/src/labmate_internal.h"
grep -Fq 'app->frequency_low_last_observation = (LabMateLowMailboxObservation){0};' "$root/src/labmate_frequency_capture.c"
sh "$root/scripts/test-v20-phase2g-host.sh"
for cc in gcc clang; do
  command -v "$cc" >/dev/null 2>&1 || { echo "Missing $cc" >&2; exit 2; }
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" "$root/src/labmate_snapshot.c" \
    "$root/src/labmate_snapshot_bridge.c" \
    "$root/tests/test_v20_phase2h_loss_quality.c" -o "$tmp/loss-$cc"
  "$tmp/loss-$cc"
done
