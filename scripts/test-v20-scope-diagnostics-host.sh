#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
      -fsanitize=address,undefined -fno-omit-frame-pointer \
      -I"$root/src" "$root/tests/test_v20_scope_diagnostics.c" \
      "$root/src/labmate_scope_diagnostics.c" \
      "$root/src/labmate_scope_compare.c" \
      -o "$tmp/diagnostics-$cc"
    "$tmp/diagnostics-$cc"
done
echo "V20 SCOPE DIAGNOSTICS HOST PASS GCC+Clang | NOT DEVICE PROVEN"
