#!/bin/sh
# UI-only CI gate. No firmware, device, USB or filesystem outside temp.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
python3 "$root/scripts/audit-v20-e11-ui-completion.py"
python3 "$root/scripts/test-v20-pixel-ui-batch2-source.py"
python3 "$root/scripts/test-v20-pixel-ui-batch3-source.py"
for cc in gcc clang; do
    command -v "$cc" >/dev/null 2>&1 || { echo "MISSING $cc" >&2; exit 2; }
    "$cc" -std=c11 -O1 -Wall -Wextra -Werror -pedantic \
        -I"$root/tests/pixel_stubs" -I"$root/src" \
        "$root/tests/test_v20_e11_pixel_header.c" -o "$tmp/header-$cc"
    "$tmp/header-$cc"
done
sh "$root/scripts/test-v20-e11-ui-live-guards-host.sh"
sh "$root/scripts/test-v20-ui01-host.sh"
sh "$root/scripts/test-v20-ultimate-root-grid-host.sh"
sh "$root/scripts/test-v20-ui05c-host.sh"
sh "$root/scripts/test-v20-ui05e-host.sh"
sh "$root/scripts/test-v20-phase3a-doctor-host.sh"
sh "$root/scripts/test-v20-phase3b-doctor-panel-host.sh"
sh "$root/scripts/test-v20-phase3c-pulse-host.sh"
sh "$root/scripts/test-v20-phase3d-frequency-host.sh"
sh "$root/scripts/test-v20-phase3d-frequency-wiring-host.sh"
echo "E11 PIXEL UI HOST GATE PASS | NATIVE E11/DEVICE STILL PENDING"
