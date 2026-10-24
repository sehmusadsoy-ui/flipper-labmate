#!/bin/sh
# Phase 2L: one-command complete v2.0 host gate.
# No FAP deployment, firmware flashing, USB, COM, GPIO or SD operations.
# Run from a COMPLETE v2.0 source checkout with GCC and Clang available.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
for tool in gcc clang awk mktemp; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "PHASE2L NO-GO: missing host prerequisite $tool" >&2
        exit 2
    }
done
cd "$root"
test -f application.fam || { echo "PHASE2L NO-GO: incomplete checkout" >&2; exit 2; }
test -f src/labmate_measurements.c || exit 2
test -f src/labmate_capture_session.c || exit 2
count=0
for suite in \
    ui01 \
    ui02 \
    ui03 \
    ui04 \
    ui05 \
    ui05b \
    ui05c \
    ui05d \
    ui05e \
    ui06 \
    ui06c \
    snapshot \
    phase2b \
    phase2c \
    phase2d \
    phase2e \
    phase2f \
    phase2g \
    phase2h \
    phase2i \
    phase2j \
    phase2k
do
    runner="$root/scripts/test-v20-$suite-host.sh"
    test -s "$runner" || { echo "PHASE2L NO-GO: absent $runner" >&2; exit 2; }
    printf '\nPHASE2L RUN: %s\n' "$suite"
    sh "$runner" || { printf 'PHASE2L FAIL: %s\n' "$suite" >&2; exit 1; }
    count=$((count+1))
done
test "$count" -eq 22
printf '\nPHASE2L HOST SUITE PASS: %s suites, GCC+Clang (each runner owns its checks)\n' "$count"
printf '%s\n' 'HOST ONLY | E11 SDK/FAP: NOT TESTED HERE | DEVICE_WRITES: ZERO'
