#!/bin/sh
# Native host only; never writes Flipper, firmware or SD.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer -I"$root/src" \
    "$root/tests/test_v20_signal_stats.c" \
    "$root/src/labmate_signal_stats.c" "$root/src/labmate_snapshot.c" \
    -o "$tmp/stats-$cc"
  "$tmp/stats-$cc"
done
echo "V20 STATS HOST PASS GCC+Clang (NOT E11 FAP/DEVICE)"
