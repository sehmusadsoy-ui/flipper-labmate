#!/bin/sh
# LabMate E11 historical UI fixture DISCOVERY. Never firmware/device/SD.
# This script is intentionally NOT a release gate: old expectations may fail.
set -u
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
bad=0
passed=0
for name in ui02 ui03 ui04 ui05 ui05b ui05d ui06 ui06c; do
    path="$root/scripts/test-v20-$name-host.sh"
    printf '\n=== LEGACY DIAGNOSTIC: %s ===\n' "$name"
    if sh "$path" >"$tmp/$name.log" 2>&1; then
        printf 'OLD FIXTURE %s: EXIT=0 (not automatically current UI acceptance)\n' "$name"
        passed=$((passed+1))
    else
        code=$?
        printf 'OLD FIXTURE %s: EXIT=%s (expected stale-geometry risk)\n' "$name" "$code"
        tail -n 17 "$tmp/$name.log"
        bad=$((bad+1))
    fi
done
printf '\nLEGACY FIXTURE INVENTORY: passed=%s failed=%s total=8\n' "$passed" "$bad"
printf '%s\n' 'IMPORTANT: passing obsolete expectations does not equal new pixel UI coverage.'
# Collect failures as test-red evidence; CI should flag until triaged.
test "$bad" -eq 0
