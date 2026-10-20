#!/bin/sh
# Host-only COMM UI renderer geometry test; never touches firmware/device/SD.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-ui02.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM

# Preserve the production renderer function bodies verbatim; substitute only
# firmware-side type definitions and shared Canvas functions with test stubs.
for name in i2c onewire; do
    file="$root/src/labmate_${name}_ui.c"
    if ! grep -q "^void draw_${name}(" "$file"; then
        echo "UI-02: renderer signature missing: $file" >&2
        exit 2
    fi
    awk "/^void draw_${name}\(/,0" "$file" > "$tmp/labmate_${name}_ui_body.inc"
    test -s "$tmp/labmate_${name}_ui_body.inc"
done

for cc in gcc clang; do
    command -v "$cc" >/dev/null 2>&1 || {
        echo "UI-02: required compiler absent: $cc" >&2; exit 2;
    }
    echo "UI-02 [$cc] I2C + 1-Wire renderer geometry"
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
        -fsanitize=address,undefined -fno-omit-frame-pointer \
        -I"$tmp" "$root/tests/test_v20_comm_render.c" -o "$tmp/ui02-$cc"
    "$tmp/ui02-$cc"
done
printf '%s\n' 'UI-02 HOST PASS: 16 renderer states per compiler (GCC + Clang)'
