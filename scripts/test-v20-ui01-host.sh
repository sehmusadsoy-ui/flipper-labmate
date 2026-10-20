#!/bin/sh
# Host-only UI-01 smoke/regression tests; never touches Flipper, SDK or SD.
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo_root"

tmp_dir=$(mktemp -d "${TMPDIR:-/tmp}/labmate-ui01.XXXXXXXX")
trap 'rm -rf -- "$tmp_dir"' EXIT HUP INT TERM

for compiler in gcc clang; do
    if ! command -v "$compiler" >/dev/null 2>&1; then
        echo "UI-01: missing compiler: $compiler" >&2
        exit 2
    fi

    echo "UI-01 [$compiler] pinned navigation + Scope geometry"
    "$compiler" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
        -fsanitize=address,undefined -fno-omit-frame-pointer \
        -Itests/host_stubs -Isrc \
        tests/test_v20_ui_geometry.c src/labmate_navigation.c \
        -o "$tmp_dir/geometry-$compiler"
    "$tmp_dir/geometry-$compiler"

    echo "UI-01 [$compiler] historical navigation fixture"
    "$compiler" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
        -fsanitize=address,undefined -fno-omit-frame-pointer \
        -Isrc -x c tests/test_navigation.c.inc -x none \
        src/labmate_navigation.c -o "$tmp_dir/navigation-$compiler"
    "$tmp_dir/navigation-$compiler"

    echo "UI-01 [$compiler] v1.9 Scope navigation regression"
    "$compiler" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
        -fsanitize=address,undefined -fno-omit-frame-pointer \
        -Isrc tests/test_labmate_scope_navigation.c src/labmate_navigation.c \
        -o "$tmp_dir/scope-navigation-$compiler"
    "$tmp_dir/scope-navigation-$compiler"
done

echo "UI-01 HOST SMOKE PASS (3 cases x 2 compilers); full UI coverage NOT claimed"
