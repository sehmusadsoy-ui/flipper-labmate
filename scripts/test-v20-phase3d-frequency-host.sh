#!/bin/sh
# Phase 3D-A: PURE frequency source admission policy; SDK/FAP/device not tested.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-phase3d.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
        -fsanitize=address,undefined -fno-omit-frame-pointer \
        -I"$root/src" \
        "$root/tests/test_v20_phase3d_frequency_policy.c" \
        "$root/src/labmate_doctor_frequency_policy.c" \
        "$root/src/labmate_frequency_gate.c" \
        -o "$tmp/frequency-$cc"
    "$tmp/frequency-$cc"
done
echo 'PHASE3D FREQUENCY POLICY HOST PASS: GCC+Clang; NO NATIVE LINK/DEVICE CLAIM'
