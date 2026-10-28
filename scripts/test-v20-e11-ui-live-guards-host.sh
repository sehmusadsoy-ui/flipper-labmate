#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
    command -v "$cc" >/dev/null 2>&1 || { echo "MISSING $cc" >&2; exit 2; }
    "$cc" -std=c11 -Wall -Wextra -Werror -pedantic -I"$root/src" \
        "$root/tests/test_v20_e11_ui_live_guards.c" -o "$tmp/live-$cc"
    "$tmp/live-$cc"
done
