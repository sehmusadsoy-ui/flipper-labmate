#!/bin/sh
# Final source-side pre-device acceptance; never install/flash/create a FAP.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
command -v python3 >/dev/null 2>&1 || exit 2
for cc in gcc clang; do command -v "$cc" >/dev/null 2>&1 || exit 2; done

# First re-run ALL valid earlier regression suites, including UI source
# pixel host test, Button 4096, Counter 4608 and GPIO 1280 per compiler.
sh "$root/scripts/audit-v20-e11-predevice.sh"
python3 "$root/scripts/audit-v20-e11-ui-integration.py"

# Original C-level A/B generation/save and stable persisted navigation IDs,
# not custom copies. These tests are independent from pixel renderer mocks.
for cc in gcc clang; do
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
        -fsanitize=undefined -fno-omit-frame-pointer -I"$root/src" \
        "$root/tests/test_labmate_scope_pair.c" \
        "$root/src/labmate_scope_pair.c" \
        "$root/src/labmate_scope_compare.c" \
        -o "$tmp/pair-$cc"
    "$tmp/pair-$cc"
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
        -fsanitize=undefined -fno-omit-frame-pointer -I"$root/src" \
        "$root/tests/test_labmate_scope_navigation.c" \
        "$root/src/labmate_navigation.c" \
        -o "$tmp/nav-$cc"
    "$tmp/nav-$cc"
done
echo "E11 FINAL UI PRE-DEVICE ACCEPTANCE HOST PASS (GCC+CLANG)"
echo "NO DEVICE/FAP/STABLE WRITE; two excluded old UI runners remain unmigrated."
