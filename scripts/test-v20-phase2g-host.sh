#!/bin/sh
# PC1/EXTI publication accounting. Read-only source audit + pure C host test.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-phase2g.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
source="$root/src/labmate_frequency_capture.c"
internal="$root/src/labmate_internal.h"
grep -Fq 'LabMateLowMailboxAudit frequency_low_mailbox_audit;' "$internal"
test "$(grep -Fc 'labmate_low_mailbox_publish(' "$source")" -eq 2
test "$(grep -Fc 'labmate_low_mailbox_reset(&app->frequency_low_mailbox_audit);' "$source")" -eq 1
grep -Fq '&app->frequency_low_mailbox_audit, app->frequency_irq_new_period);' "$source"
# Preserve and re-run the real app-thread PC1 atomic mailbox regression.
sh "$root/scripts/test-v20-phase2f-host.sh"
for cc in gcc clang; do
  command -v "$cc" >/dev/null 2>&1 || { echo "Missing $cc" >&2; exit 2; }
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" "$root/tests/test_v20_phase2g_low_audit.c" -o "$tmp/phase2g-$cc"
  "$tmp/phase2g-$cc"
done
