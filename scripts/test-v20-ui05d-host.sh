#!/bin/sh
# UI05D E11: exact current Frequency/Pulse/PWM production renderers, host only.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root" "$tmp" <<'PY'
import re,sys
from pathlib import Path
root,dest=map(Path,sys.argv[1:])
sources={
 "screen":(root/"src/labmate_ui_screens.c").read_text(),
 "kit":(root/"src/ui_kit.c").read_text(),
}
names={
 "screen":["frequency_format_compact","frequency_format_tiny","frequency_hero_text",
           "draw_frequency","draw_generator","pulse_ui_format_value",
           "draw_pulse_stats","draw_pulse"],
 "kit":["ui_kit_rect","ui_kit_text","ui_kit_center_text","ui_kit_back_title",
        "ui_kit_pulse_line","ui_kit_sparkline"],
}
for source,functions in names.items():
    for name in functions:
        m=list(re.finditer(r"(?m)^(?:static )?(?:void|bool)\s+"+name+r"\s*\(",sources[source]))
        assert len(m)==1,(source,name,len(m))
        start=m[0].start(); brace=sources[source].find("{",m[0].end())
        assert brace>=0
        level=0
        for end in range(brace,len(sources[source])):
            if sources[source][end]=="{": level+=1
            elif sources[source][end]=="}":
                level-=1
                if level==0:break
        else:raise AssertionError(("unterminated",name))
        body=sources[source][start:end+1]
        for unsafe in ("furi_hal_gpio_","furi_hal_pwm_","storage_file_",
                       "labmate_generator_start(","labmate_capture_start("):
            assert unsafe not in body,(name,unsafe)
        (dest/(name+".inc")).write_text(body+"\n")
print("E11 UI05D exact production UI bodies extracted (14)")
PY
for cc in gcc clang; do
    command -v "$cc" >/dev/null 2>&1 || exit 2
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
      -fsanitize=undefined -fno-omit-frame-pointer \
      -I"$root/tests/pixel_stubs" -I"$root/src" -I"$tmp" \
      "$root/tests/test_v20_ui05d_pixel.c" -o "$tmp/ui05d-$cc"
    "$tmp/ui05d-$cc"
done
echo "E11 UI05D CURRENT PIXEL RENDER GCC+CLANG HOST PASS | DEVICE UNTESTED"
