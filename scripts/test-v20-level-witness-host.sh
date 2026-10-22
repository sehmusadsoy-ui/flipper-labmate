#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
      -fsanitize=address,undefined -fno-omit-frame-pointer \
      -I"$root/src" "$root/tests/test_v20_level_witness.c" \
      "$root/src/labmate_level_witness.c" -o "$tmp/level-$cc"
    "$tmp/level-$cc"
done
echo "V20 LEVEL SAMPLED OBSERVATION HOST PASS GCC+Clang | NOT STUCK-FAULT CERTIFICATION"
