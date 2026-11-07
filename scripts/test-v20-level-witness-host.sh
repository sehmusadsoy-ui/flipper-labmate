#!/bin/sh
# RETIRED feature, removed by approved E11 baseline 880beac. Exit 77 is
# deliberately NOT PASS; old fixture and original red logs remain evidence.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python3 - "$root/src" <<'PY'
from pathlib import Path
import re,sys
root=Path(sys.argv[1])
assert not (root/'labmate_level_witness.c').exists()
assert not (root/'labmate_level_witness.h').exists()
for p in root.iterdir():
 if p.suffix in ('.c','.h'):
  assert not re.search(r'\b(?:LabMateLevelWitness|labmate_level_(?:begin|observe|finish|assess|invalidate))\b',p.read_text()),p
print('RETIRED / NOT ACCEPTANCE: GPIO polling LevelWitness was removed in 880beac.')
print('UNMAPPED: sampled H/L, transition, poll-gap, pin/clock and release-veto assertions.')
print('Current GPIO trace is presentation-only; it is not a replacement for those assertions.')
PY
exit 77
