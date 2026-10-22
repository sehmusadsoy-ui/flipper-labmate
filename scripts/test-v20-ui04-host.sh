#!/bin/sh
# Host-only; builds verbatim RECORDS draw function bodies, not firmware.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-ui04.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
source="$root/src/labmate_ui_screens.c"
for name in profiles history history_detail; do
    # Source function closes at column zero. Stop after that top-level brace,
    # not at the next public draw function (About sits between the first two).
    awk -v signature="void draw_${name}(" '
      index($0,signature)==1 {copy=1}
      copy {print; if($0=="}") exit}
    ' "$source" > "$tmp/records_${name}_body.inc"
    test -s "$tmp/records_${name}_body.inc"
done
# Compile the EXACT real shared footer along with the extracted History
# Detail renderer. Its formatter is source-linked; do not use a permissive
# geometry-only lookalike.
for spec in 'static bool ui_format_key(:ui_format_key.inc' 'void ui_footer_info(:ui_footer_info.inc'; do
    signature=${spec%%:*}
    filename=${spec#*:}
    awk -v sig="$signature" 'index($0,sig)==1 {copy=1} copy {print; if($0=="}") exit}' \
        "$root/src/labmate_ui_primitives.c" > "$tmp/$filename"
    test -s "$tmp/$filename"
done
for cc in gcc clang; do
    command -v "$cc" >/dev/null 2>&1 || { echo "missing compiler: $cc" >&2; exit 2; }
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined \
      -fno-omit-frame-pointer -I"$tmp" \
      "$root/tests/test_v20_ui04_records.c" -o "$tmp/ui04-$cc"
    "$tmp/ui04-$cc"
done
