#!/usr/bin/env bash
# One-shot HOST + E11 FAP REVIEW on the exact current GitHub source checkout.
# No USB/device/FAP installation, Stable merge/tag or firmware flashing.
set -Eeuo pipefail
APP="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="${LABMATE_E11_WORK:-$HOME/labmate-v20-ultimate-github-e11-review}"
LOG="${LABMATE_REVIEW_LOG:-${WORK}.log}"

if [ -e "$WORK" ] || [ -L "$WORK" ] || [ -e "$LOG" ] || [ -L "$LOG" ]; then
    echo 'NO-GO: output workspace/log exists; no overwrite permitted.' >&2
    exit 2
fi
if git -C "$APP" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    ROOT="$(git -C "$APP" rev-parse --show-toplevel)"
    test "$ROOT" = "$APP" || { echo 'NO-GO: wrong Git repository root' >&2; exit 2; }
    BRANCH="$(git -C "$APP" branch --show-current)"
    test "$BRANCH" = 'dev/v2.0-signal-doctor' || {
        echo "NO-GO: expected dev/v2.0-signal-doctor branch, got $BRANCH" >&2
        exit 2
    }
    # An untracked src/test/script can affect a globbed build despite a clean
    # tracked diff. Preserve it and fail closed; never delete user files.
    STATUS="$(git -C "$APP" status --porcelain --untracked-files=normal)" || {
        echo 'NO-GO: Git status inspection failed; source provenance unknown' >&2
        exit 2
    }
    test -z "$STATUS" || {
        echo 'NO-GO: tracked or untracked changes; review requires a clean checkout' >&2
        exit 2
    }
    printf 'REVIEW SOURCE GIT: %s\n' "$(git -C "$APP" rev-parse HEAD)"
else
    echo 'NOTICE: exported GitHub source without .git; per-file hashes only.'
fi
printf 'REVIEW LOG: %s\n' "$LOG"
if LABMATE_E11_WORK="$WORK" bash "$APP/scripts/build-v20-ultimate-e11-review.sh" >"$LOG" 2>&1; then
    :
else
    echo 'NO-GO: host/source/SDK review did not pass; last 80 log lines:' >&2
    tail -n 80 "$LOG" >&2
    exit 1
fi
FAP="$WORK/LabMate-Ultimate-v2.0DEV-E11-REVIEW.fap"
PROVENANCE="$WORK/ULTIMATE_REVIEW_PROVENANCE.txt"
test -s "$FAP" && test -s "$PROVENANCE" || {
    echo 'NO-GO: review output/provenance missing' >&2
    exit 1
}
# Verify copy matches the compiled E11 SDK artifact byte for byte.
cmp "$FAP" "$WORK/momentum-src/build/f7-firmware-C/.extapps/labmate.fap"
grep -Fq 'V20 ULTIMATE E11 HOST+FAP REVIEW: PASS | NO DEVICE WRITES' "$LOG"
echo 'V20 ULTIMATE FULL HOST + NATIVE E11 REVIEW: PASS'
stat -c 'FAP BYTES: %s' "$FAP"
sha256sum "$FAP"
md5sum "$FAP"
cat "$PROVENANCE"
echo 'DEVICE WRITES: ZERO | NO FLASH | NO INSTALL'
