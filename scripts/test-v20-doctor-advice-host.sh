#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
     -fsanitize=address,undefined -fno-omit-frame-pointer -I"$root/src" \
     "$root/tests/test_v20_doctor_advice.c" \
     "$root/src/labmate_doctor_advice.c" -o "$tmp/advice-$cc"
  "$tmp/advice-$cc"
done
echo "V20 DOCTOR ADVICE PASS GCC+Clang (NO E11/DEVICE CLAIM)"
