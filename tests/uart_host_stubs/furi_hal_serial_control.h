#pragma once
#include <furi_hal_serial_types.h>

FuriHalSerialHandle* furi_hal_serial_control_acquire(FuriHalSerialId serial_id);
void furi_hal_serial_control_release(FuriHalSerialHandle* handle);
