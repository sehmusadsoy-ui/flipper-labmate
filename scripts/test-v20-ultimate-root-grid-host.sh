#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
        -fsanitize=address,undefined -fno-omit-frame-pointer \
        -I"$root/src" "$root/tests/test_v20_ultimate_root_grid.c" \
        "$root/src/labmate_navigation.c" -o "$tmp/menu-$cc"
    "$tmp/menu-$cc"
done
echo "ULTIMATE ROOT UI HOST PASS GCC+Clang; DEVICE NOT TESTED"
