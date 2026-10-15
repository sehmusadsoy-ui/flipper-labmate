#pragma once
#include "labmate_comm_resource.h"
#include "labmate_onewire_ds18b20.h"
#include <stdbool.h>
#include <stdint.h>

/* Real Flipper OneWireHost, PA4 external GPIO, 3.3V VDD-powered sensor ONLY.
 * Single-thread-owned; caller must serialize against other LabMate tools.
 * Start is explicitly user-triggered, never automatic on screen entry.
 * No power_enable_otg, no PB14/iButton and no parasite-power support.
 */
typedef struct OneWireHost OneWireHost;

typedef enum {
    LabMateOneWireHwIdle = 0,
    LabMateOneWireHwConverting,
    LabMateOneWireHwMeasured,
    LabMateOneWireHwNoSensor,
    LabMateOneWireHwBusy,
    LabMateOneWireHwDataError,
    LabMateOneWireHwPowerCheck,
    LabMateOneWireHwStopped,
} LabMateOneWireHwStatus;

typedef struct {
    OneWireHost* host;
    LabMateCommOwner* owner;
    uint32_t firmware_lease_handle; /* PA4 pin claimed before OneWireHost alloc */
    bool firmware_release_fault; /* sticky failed release, never retry or reset */
    LabMateOneWireHwStatus status;
    LabMateOneWireDecodeStatus decode_status;
    uint32_t start_tick;
    uint32_t wait_ticks;
    int16_t temperature_tenths;
    uint8_t resolution_bits;
    bool has_temperature;
} LabMateOneWireHw;

/* Initialize with no active session only. */
void labmate_onewire_hw_init(LabMateOneWireHw* state);
/* First validate local owner/pin exclusions, then reset and convert on PA4. */
bool labmate_onewire_hw_start(
    LabMateOneWireHw* state, LabMateCommOwner* owner, LabMateCommBusy busy);
/* Nonblocking 800ms conversion interval; transaction itself uses bounded
 * OneWireHost reset/read, modeled on official Momentum thermometer example.
 */
void labmate_onewire_hw_poll(LabMateOneWireHw* state);
/* Immediate GPIO cleanup, no wait for sensor conversion. */
void labmate_onewire_hw_stop(LabMateOneWireHw* state);
