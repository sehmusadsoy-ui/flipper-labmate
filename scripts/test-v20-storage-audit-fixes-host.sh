#!/bin/sh
# Focused software regressions; no FAP build, USB or real storage access.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root" "$tmp" <<'PY'
from pathlib import Path
import sys
root, tmp = map(Path, sys.argv[1:])
source = (root / "src/labmate_history.c").read_text()
include = '#include "labmate_history.h"\n'
assert source.count(include) == 1
(tmp / "history_production.inc").write_text(source.replace(include, "", 1))
menu = (root / "src/labmate_input_menu.c").read_text()
entry = menu.split("case LabMateToolOneWire:", 1)[1].split("break;", 1)[0]
assert "labmate_onewire_hw_reenter(&app->thermometer);" in entry
assert "labmate_onewire_hw_init(" not in entry
print("Current menu uses tested OneWire re-entry helper PASS")
PY
for cc in gcc clang; do
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
        -fsanitize=undefined -fno-omit-frame-pointer \
        -I"$root/tests/onewire_host_stubs" -I"$root/src" \
        "$root/src/labmate_comm_resource.c" "$root/src/labmate_onewire_ds18b20.c" \
        "$root/src/labmate_onewire_hw.c" "$root/tests/test_onewire_hw.c" \
        -o "$tmp/onewire-$cc"
    "$tmp/onewire-$cc"
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
        -fsanitize=undefined -fno-omit-frame-pointer -I"$root/src" -I"$tmp" \
        "$root/src/labmate_logger_codec.c" "$root/tests/test_v20_history_storage.c" \
        -o "$tmp/history-$cc"
    "$tmp/history-$cc"
done
echo "Storage audit software-fix regressions PASS (GCC+Clang/UBSan; hardware untested)"
