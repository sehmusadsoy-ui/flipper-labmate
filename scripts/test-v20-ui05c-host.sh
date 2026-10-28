#!/bin/sh
# Extract verbatim production Counter helpers and draw_counter, host only.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root/src/labmate_ui_screens.c" "$tmp" <<'PY'
from pathlib import Path
import sys
source=Path(sys.argv[1]).read_text()
out=Path(sys.argv[2])
specs=(
 ("static void labmate_counter_ui_count(", "counter_count.inc"),
 ("static void labmate_counter_ui_time(", "counter_time.inc"),
 ("void draw_counter(", "draw_counter.inc"),
)
for token,filename in specs:
    assert source.count(token)==1,token
    start=source.index(token)
    first=source.index("{",start)
    level=0
    for pos in range(first,len(source)):
        if source[pos]=="{":level+=1
        if source[pos]=="}":
            level-=1
            if level==0:break
    else: raise AssertionError("unbalanced "+token)
    out.joinpath(filename).write_text(source[start:pos+1]+"\n")
print("E11 EXACT COUNTER PRODUCTION BODY EXTRACTION PASS")
PY
for cc in gcc clang; do
    command -v "$cc" >/dev/null 2>&1 || exit 2
    "$cc" -std=c11 -O1 -Wall -Wextra -Werror -pedantic \
      -fsanitize=undefined -fno-omit-frame-pointer \
      -I"$root/tests/pixel_stubs" -I"$root/src" -I"$tmp" \
      "$root/tests/test_v20_ui05c_counter.c" \
      "$root/src/labmate_counter_math.c" -o "$tmp/counter-$cc"
    "$tmp/counter-$cc"
done
echo "E11 COUNTER SCREEN HOST GCC+Clang PASS | REAL E11 DEVICE NOT TESTED"
