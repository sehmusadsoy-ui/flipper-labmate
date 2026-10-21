#!/bin/sh
# Pure host-only v2.0 Phase 3A diagnostic gate: never contacts a Flipper.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
for tool in gcc clang mktemp; do command -v "$tool" >/dev/null 2>&1 || { echo "PHASE3A NO-GO: missing $tool" >&2; exit 2; }; done
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT HUP INT TERM
for cc in gcc clang; do
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
       -fsanitize=address,undefined -fno-omit-frame-pointer \
       -I"$root/src" \
       "$root/src/labmate_snapshot.c" "$root/src/labmate_doctor.c" \
       "$root/tests/test_v20_doctor.c" -o "$work/doctor-$cc"
    "$work/doctor-$cc"
done
printf 'PHASE3A HOST ONLY PASS: GCC+Clang; SDK/Flipper/FAP NOT TESTED\n'
