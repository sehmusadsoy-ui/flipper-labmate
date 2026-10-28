#!/bin/sh
# UI-03 migrated to the current E11 source-linked OneWire and UART
# renderers. Shared gate also checks I2C; no serial/device operations.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sh "$root/scripts/test-v20-e11-comm-current-host.sh"
