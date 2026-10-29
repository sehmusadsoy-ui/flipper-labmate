#!/bin/sh
# UI-02 migrated to the current E11 source-linked I2C and OneWire
# renderers. Shared gate also checks UART; never touches bus/device.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sh "$root/scripts/test-v20-e11-comm-current-host.sh"
