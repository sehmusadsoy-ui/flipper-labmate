#pragma once
/* Shared physical GPIO lookup and exclusive-capture acquisition gate.
 * This is internal to LabMate. The caller controls IRQ detach ordering.
 */
#include <furi_hal_resources.h>
#include "labmate_internal.h"

extern const GpioPin* const labmate_gpio_pins[GPIO_COUNT];
bool labmate_capture_can_start(LabMateApp* app, LabMateCaptureOwner requested);
