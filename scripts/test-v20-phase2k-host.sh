#!/bin/sh
# Phase 2K: pure lease-release truth table + real STOP call-site contracts.
# Read-only: NEVER flashes firmware or touches Flipper GPIO / microSD.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmp=$(mktemp -d "${TMPDIR:-/tmp}/labmate-phase2k.XXXXXXXX")
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM
low="$root/src/labmate_frequency_capture.c"
pulse="$root/src/labmate_pulse_capture.c"
session="$root/src/labmate_capture_session.c"
button="$root/src/labmate_button_capture.c"
counter="$root/src/labmate_event_counter.c"
test -f "$root/src/labmate_capture_release_gate.h"
grep -Fq 'bool labmate_frequency_low_lease_pending(void)' "$low"
grep -Fq 'bool labmate_pulse_lease_pending(void)' "$pulse"
grep -Fq 'labmate_capture_release_proven(&release)' "$session"
grep -Fq '.frequency_low_lease_pending = labmate_frequency_low_lease_pending()' "$session"
grep -Fq '.frequency_high_lease_pending = labmate_frequency_tim2_lease_pending()' "$session"
grep -Fq '.pulse_lease_pending = labmate_pulse_lease_pending()' "$session"
grep -Fq '.release_fault = app->capture_release_fault' "$session"
grep -Fq '.button_lease_pending = labmate_button_lease_pending()' "$session"
grep -Fq 'bool labmate_button_lease_pending(void)' "$button"
# Verify ownership remains until the firmware release outcome is known.
awk '/^void labmate_frequency_low_stop[(]/ {on=1} /^bool labmate_frequency_low_lease_pending[(]/ {on=0} on {print}' "$low" > "$tmp/low.inc"
awk '/^void labmate_pulse_capture_stop[(]/ {on=1} /^bool labmate_pulse_lease_pending[(]/ {on=0} on {print}' "$pulse" > "$tmp/pulse.inc"
awk '/^void labmate_frequency_high_stop[(]/ {on=1} /^void labmate_frequency_high_start[(]/ {on=0} on {print}' "$low" > "$tmp/high.inc"
awk '/^void labmate_capture_stop_all[(]/ {on=1} on {print; if($0=="}") exit}' "$session" > "$tmp/all.inc"
for path in "$tmp/low.inc" "$tmp/pulse.inc"; do
  awk '
    /if\(furi_hal_resource_lease_release\(/ {release=NR}
    /app->capture_owner = labmate_capture_owner_after_stop\(/ {owner=NR}
    END {if(!(release>0 && owner>release)) exit 1}
  ' "$path"
done
grep -Fq 'if(!lease_pending && app->capture_owner == LabMateCaptureFrequencyHigh)' "$tmp/high.inc"
# Exact function bodies, not a reimplementation of GPIO/TIM2 teardown:
awk '/^void labmate_frequency_high_stop[(]/ {on=1} on {print; if($0=="}") exit}' "$low" > "$tmp/high_stop.inc"
awk '/^void labmate_frequency_low_stop[(]/ {on=1} on {print; if($0=="}") exit}' "$low" > "$tmp/low_stop.inc"
awk '/^void labmate_pulse_capture_stop[(]/ {on=1} on {print; if($0=="}") exit}' "$pulse" > "$tmp/pulse_stop.inc"
awk '/^void labmate_event_counter_stop[(]/ {on=1} on {print; if($0=="}") exit}' "$counter" > "$tmp/counter_stop.inc"
awk '/^void labmate_button_capture_stop[(]/ {on=1} on {print; if($0=="}") exit}' "$button" > "$tmp/button_stop.inc"
awk '/^void labmate_capture_stop_all[(]/ {on=1} on {print; if($0=="}") exit}' "$session" > "$tmp/stop_all.inc"
for part in "$tmp/high_stop.inc" "$tmp/low_stop.inc" "$tmp/pulse_stop.inc" "$tmp/counter_stop.inc" "$tmp/button_stop.inc" "$tmp/stop_all.inc"; do
  test -s "$part"
done
grep -Fq 'if(!lease_pending && healthy && !app->capture_release_fault &&' "$tmp/counter_stop.inc"
awk '
  /if\(labmate_capture_release_proven\(&release\)\)/ {gate=NR}
  /app->capture_owner = LabMateCaptureNone;/ {free=NR}
  END {if(!(gate>0 && free>gate)) exit 1}
' "$tmp/all.inc"
for cc in gcc clang; do
  command -v "$cc" >/dev/null 2>&1 || { echo "Missing $cc" >&2; exit 2; }
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" "$root/tests/test_v20_phase2k_release.c" -o "$tmp/release-$cc"
  "$tmp/release-$cc"
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$tmp" "$root/tests/test_v20_phase2k_native_stop.c" -o "$tmp/native-$cc"
  "$tmp/native-$cc"
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" -I"$tmp" "$root/tests/test_v20_phase2k_button_counter.c" \
    "$root/src/labmate_dashboard_store.c" "$root/src/labmate_snapshot.c" \
    -o "$tmp/button-counter-$cc"
  "$tmp/button-counter-$cc"
  "$cc" -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
    -fsanitize=address,undefined -fno-omit-frame-pointer \
    -I"$root/src" -I"$tmp" "$root/tests/test_v20_phase2k_stop_all.c" -o "$tmp/stop-all-$cc"
  "$tmp/stop-all-$cc"
done
printf '%s\n' 'Phase2K source-linked STOP native-lease gate PASS (host only)'
