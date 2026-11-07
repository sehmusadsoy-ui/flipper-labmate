#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 - "$root" "$tmp" <<'PY'
from pathlib import Path
import sys
root,tmp=map(Path,sys.argv[1:])
# Keep COMPLETE production function bodies; replace only firmware app/HAL
# includes with a typed test shim. Codecs/storage adapters compile unchanged.
for name in ("labmate_logger_storage", "labmate_deferred"):
    text=(root/"src"/(name+".c")).read_text()
    lines=[]
    for line in text.splitlines(keepends=True):
        if line.startswith('#include "') and line.split('"')[1] not in (
            "labmate_logger_codec.h", "labmate_storage_paths.h", "labmate_profile_storage.h", "labmate_ui_prefs_storage.h"):
            continue
        lines.append(line)
    (tmp/(name+".c")).write_text('#include "persistence_app.h"\n'+''.join(lines))
PY
for cc in gcc clang; do
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=undefined \
        -fno-omit-frame-pointer -I"$root/tests/persistence_stubs" -I"$root/src" \
        "$root/src/labmate_profiles.c" "$root/src/labmate_profile_storage.c" \
        "$root/src/labmate_ui_prefs.c" "$root/src/labmate_ui_prefs_storage.c" \
        "$root/src/labmate_resource_policy.c" "$root/src/labmate_logger_codec.c" \
        "$root/src/labmate_dashboard_store.c" "$root/src/labmate_snapshot.c" \
        "$tmp/labmate_logger_storage.c" "$tmp/labmate_deferred.c" \
        "$root/tests/test_v20_persistence_storage.c" -o "$tmp/persistence-$cc"
    "$tmp/persistence-$cc"
done
echo "Persistence software integration PASS (GCC+Clang/UBSan; real SD durability untested)"
