#!/bin/sh
# E11 UI06: compile the real CURRENT quiet pair/triple footer implementation.
# Old UI06 test expected removed inverse-band and ui_footer_info semantics.
# Pure host C11 gcc+clang+UBSan; no firmware, SD, device or FAP writes.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root/src/labmate_ui_primitives.c" "$tmp" <<'PY'
from pathlib import Path
import re,sys
s=Path(sys.argv[1]).read_text();out=Path(sys.argv[2])
names=["ui_format_key","ui_key","ui_footer_action","ui_footer_pair",
       "ui_footer_triple_label_valid","ui_footer_triple"]
for name in names:
    match=list(re.finditer(r"(?m)^(?:static )?(?:void|bool)\s+"+name+r"\s*\(",s))
    assert len(match)==1,(name,len(match))
    start=match[0].start();brace=s.index("{",match[0].end());depth=0
    for end in range(brace,len(s)):
        if s[end]=="{":depth+=1
        elif s[end]=="}":
            depth-=1
            if depth==0:break
    else:raise AssertionError(name)
    body=s[start:end+1]
    for bad in ("canvas_draw_box(","storage_file_","furi_hal_","canvas_set_color(canvas, ColorWhite)"):
        assert bad not in body,(name,bad)
    (out/(name+".inc")).write_text(body+"\n")
print("E11 UI06 current pair/triple production footer bodies extracted")
PY
for cc in gcc clang; do
  command -v "$cc" >/dev/null 2>&1 || exit 2
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
      -fsanitize=undefined -fno-omit-frame-pointer \
      -I"$root/tests/pixel_stubs" -I"$root/src" -I"$tmp" \
      "$root/tests/test_v20_ui06_current.c" -o "$tmp/ui06-$cc"
  "$tmp/ui06-$cc"
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
      -fsanitize=undefined -fno-omit-frame-pointer -I"$root/src" \
      "$root/tests/test_v20_ui06_layout.c" -o "$tmp/layout-$cc"
  "$tmp/layout-$cc"
done
# Shared Frequency/Pulse/PWM renderers are linked to this layout gate.
sh "$root/scripts/test-v20-ui05d-host.sh"
echo "E11 UI06 CURRENT FOOTER/LAYOUT HOST PASS | PHYSICAL PIXELS UNTESTED"
