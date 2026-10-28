#!/bin/sh
# Exact-body GCC/Clang regression — source-linked display primitives ONLY.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root/src/ui_kit.c" "$root/src/ui_kit.h" "$tmp/uikit_step1_exact.inc" <<'PY'
import re,sys
from pathlib import Path
s=Path(sys.argv[1]).read_text()
header=Path(sys.argv[2]).read_text()
for required in ("UiKitInstrumentWaiting","UiKitInstrumentMatch",
                 "UiKitInstrumentOff","ui_kit_stat_row_unit",
                 "ui_kit_mini_trace","ui_kit_scope_page_dots",
                 "ui_kit_next_cue","UI_KIT_STAT_ROW_SELECT"):
    assert required in header,required
names=(
"ui_kit_rect","ui_kit_compact_key_width","ui_kit_key_hint_compact",
"ui_kit_instrument_state_name","ui_kit_state_chip_width",
"ui_kit_instrument_disc","ui_kit_instrument_glyph",
"ui_kit_state_chip_draw","ui_kit_state_chip_compact",
"ui_kit_pixel_header","ui_kit_stat_row","ui_kit_stat_row_unit",
"ui_kit_pulse_line_dotted","ui_kit_mini_trace",
"ui_kit_scope_page_dots","ui_kit_next_cue")
pieces=[]
for n in names:
    matches=list(re.finditer(r"(?m)^(?:static\s+)?(?:const\s+char\s*\*|bool|void|uint8_t|uint16_t)\s*\*?\s*"+n+r"\(",s))
    assert len(matches)==1,(n,len(matches))
    start=matches[0].start()
    op=s.index("{",matches[0].end())
    depth=0
    for i in range(op,len(s)):
        if s[i]=="{":depth+=1
        if s[i]=="}":
            depth-=1
            if depth==0:break
    else:raise AssertionError(n+" missing brace")
    pieces.append(s[start:i+1])
Path(sys.argv[3]).write_text("\n\n".join(pieces)+"\n")
print("STEP1 UI KIT EXACT SOURCE BODY EXTRACT PASS:",len(pieces))
PY
for cc in gcc clang; do
    command -v "$cc" >/dev/null 2>&1 || { echo "missing compiler $cc" >&2; exit 2; }
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
      -fsanitize=undefined -fno-omit-frame-pointer \
      -I"$root/tests/pixel_stubs" -I"$root/src" -I"$tmp" \
      "$root/tests/test_v20_button_scope_uikit_step1.c" \
      -o "$tmp/step1-$cc"
    "$tmp/step1-$cc"
done
echo "STEP1 E11 PIXEL PRIMITIVES HOST GCC+Clang PASS; NATIVE/DEVICE SEPARATE"
