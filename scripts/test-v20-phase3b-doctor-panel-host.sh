#!/bin/sh
# Phase3B: pure app-thread presentation/reference policy; never touches hardware.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-phase3b.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
for cc in gcc clang; do
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
      -fsanitize=address,undefined -fno-omit-frame-pointer \
      -I"$root/src" \
      "$root/tests/test_v20_phase3b_panel.c" \
      "$root/src/labmate_doctor_panel.c" \
      "$root/src/labmate_doctor.c" \
      "$root/src/labmate_snapshot.c" \
      "$root/src/labmate_dashboard_store.c" \
      -o "$tmp/panel-$cc"
    "$tmp/panel-$cc"
    "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
      -fsanitize=address,undefined -fno-omit-frame-pointer \
      -I"$root/src" \
      "$root/tests/test_v20_doctor_layout.c" \
      "$root/src/labmate_doctor_panel.c" \
      "$root/src/labmate_doctor.c" \
      "$root/src/labmate_snapshot.c" \
      "$root/src/labmate_dashboard_store.c" \
      -o "$tmp/layout-$cc"
    "$tmp/layout-$cc"
done
printf '%s\n' 'PHASE3B PANEL + DOCTOR 128x64 GEOMETRY HOST PASS: GCC+Clang, NO SDK/DEVICE CLAIM'
