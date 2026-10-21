#!/bin/sh
# Real Scope metrics pure C only, no HAL/device writes
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer -I"$root/src" \
    "$root/tests/test_v20_scope_period_stats.c" \
    "$root/src/labmate_scope_period_stats.c" -o "$tmp/spread-$cc"
  "$tmp/spread-$cc"
done
echo "V20 SCOPE PERIOD STATISTICS HOST PASS GCC+Clang | NO DEVICE TEST"
