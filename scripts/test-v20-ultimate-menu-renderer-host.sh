#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root" "$tmp" <<'PY'
from pathlib import Path
import re,sys
root,dest=map(Path,sys.argv[1:])
groups={
 'src/labmate_ui_screens.c':['labmate_menu_icon_for_tool','labmate_menu_icon_for_group',
  'labmate_group_name','labmate_tool_name','labmate_tool_short_name','draw_menu'],
 'src/ui_kit.c':['ui_kit_rect','ui_kit_ease','ui_kit_lerp','ui_kit_text',
  'ui_kit_center_text','ui_kit_brand','ui_kit_carousel_card','ui_kit_page_dots',
  'ui_kit_pill','ui_kit_back_title','ui_kit_list_row'],
}
for path,names in groups.items():
 source=(root/path).read_text(); bodies=[]
 for name in names:
  matches=list(re.finditer(r'(?m)^(?:static\s+)?(?:void|bool|UiKitIcon|int16_t|uint16_t|const char\*)\s+'+name+r'\s*\(',source))
  assert len(matches)==1,(path,name,len(matches))
  m=matches[0]; brace=source.index('{',m.end());depth=0
  for end in range(brace,len(source)):
   if source[end]=='{':depth+=1
   elif source[end]=='}':
    depth-=1
    if depth==0:break
  else:raise AssertionError(name)
  body=source[m.start():end+1]
  for forbidden in ('furi_hal_','storage_file_','furi_delay','labmate_capture_start('):
   assert forbidden not in body,(name,forbidden)
  bodies.append(body)
 (dest/('menu.inc' if 'screens' in path else 'menu_chrome.inc')).write_text('\n'.join(bodies)+'\n')
PY
for cc in gcc clang; do
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
      -fsanitize=address,undefined -fno-omit-frame-pointer \
      -I"$root/tests/pixel_stubs" -I"$root/src" -I"$tmp" \
      "$root/tests/test_v20_menu_current.c" \
      "$root/src/labmate_navigation.c" -o "$tmp/render-$cc"
    "$tmp/render-$cc"
done
echo "E11 CURRENT SOURCE-LINKED MENU RENDER PASS GCC+Clang | DEVICE RASTER NOT TESTED"
