#!/bin/sh
# Historical filename; canonical CURRENT acceptance plus explicit retirement.
# No always-green diagnostic exit: current failure status is propagated.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if sh "$root/scripts/test-v20-level-witness-host.sh"; then
    echo 'NO-GO: retired LevelWitness unexpectedly reported PASS' >&2
    exit 1
else
    code=$?
    test "$code" -eq 77 || exit "$code"
fi
if sh "$root/scripts/test-v20-e11-current-software-host.sh"; then
    echo 'INVENTORY: CURRENT SUPPORTED ACCEPTANCE PASS; RETIRED ENTRYPOINTS=1 (exit77, NOT PASS)'
    echo 'Original 2026-11-06 red logs and assertion mapping remain the historical evidence.'
else
    code=$?
    echo "INVENTORY: CURRENT ACCEPTANCE FAIL exit=$code; retired exclusions are not a waiver" >&2
    exit "$code"
fi
