#include "labmate_onewire_hw.h"
#include <furi.h>
#include <furi_hal.h>
#include <furi_hal_resources.h>
#include <one_wire/one_wire_host.h>
#include <string.h>

/* External PA4: chosen to avoid shared PB14 iButton/RFID pin.
 * Does not require USB/OTG 5V or firmware power service.
 */
#define LABMATE_1W_ROM_SKIP 0xCCU
#define LABMATE_1W_CONVERT 0x44U
#define LABMATE_1W_READ_SCRATCHPAD 0xBEU
#define LABMATE_1W_CONVERT_WAIT_MS 800U

void labmate_onewire_hw_init(LabMateOneWireHw* s) {
    if(s) {
        memset(s, 0, sizeof(*s));
        s->status = LabMateOneWireHwIdle;
    }
}

static void labmate_onewire_hw_release(LabMateOneWireHw* s) {
    if(s->host) {
        onewire_host_stop(s->host);
        onewire_host_free(s->host);
        s->host = NULL;
    }
    if(s->owner) {
        (void)labmate_comm_local_release(s->owner, LabMateCommOneWirePa4);
        s->owner = NULL;
    }
}

bool labmate_onewire_hw_start(
    LabMateOneWireHw* s, LabMateCommOwner* owner, LabMateCommBusy busy) {
    if(!s || !owner || s->host || s->owner) return false;
    if(!labmate_comm_local_claim(owner, LabMateCommOneWirePa4, busy)) {
        s->status = LabMateOneWireHwBusy;
        return false;
    }
    s->owner = owner;
    s->host = onewire_host_alloc(&gpio_ext_pa4);
    if(!s->host) {
        s->status = LabMateOneWireHwBusy;
        labmate_onewire_hw_release(s);
        return false;
    }

    s->has_temperature = false;
    s->temperature_tenths = 0;
    s->resolution_bits = 0U;
    s->decode_status = LabMateOneWireDecodeInvalidInput;
    onewire_host_start(s->host);
    bool presence;
    /* Momentum's 1-Wire host calls are timing-sensitive; critical sections
     * protect only the short bus transaction, never the 800ms wait. */
    FURI_CRITICAL_ENTER();
    presence = onewire_host_reset(s->host);
    if(presence) {
        onewire_host_write(s->host, LABMATE_1W_ROM_SKIP);
        onewire_host_write(s->host, LABMATE_1W_CONVERT);
    }
    FURI_CRITICAL_EXIT();
    if(!presence) {
        s->status = LabMateOneWireHwNoSensor;
        labmate_onewire_hw_release(s);
        return false;
    }

    const uint32_t hz = furi_kernel_get_tick_frequency();
    s->wait_ticks = hz == 0U ? 1U :
        (uint32_t)((LABMATE_1W_CONVERT_WAIT_MS * (uint64_t)hz + 999U) / 1000U);
    if(s->wait_ticks == 0U) s->wait_ticks = 1U;
    s->start_tick = furi_get_tick();
    s->status = LabMateOneWireHwConverting;
    return true;
}

void labmate_onewire_hw_poll(LabMateOneWireHw* s) {
    if(!s || !s->host || s->status != LabMateOneWireHwConverting) return;
    if((uint32_t)(furi_get_tick() - s->start_tick) < s->wait_ticks) return;

    uint8_t bytes[LABMATE_ONEWIRE_SCRATCHPAD_SIZE] = {0};
    bool presence;
    FURI_CRITICAL_ENTER();
    presence = onewire_host_reset(s->host);
    if(presence) {
        onewire_host_write(s->host, LABMATE_1W_ROM_SKIP);
        onewire_host_write(s->host, LABMATE_1W_READ_SCRATCHPAD);
        onewire_host_read_bytes(s->host, bytes, sizeof(bytes));
    }
    FURI_CRITICAL_EXIT();

    LabMateOneWireTemperature temp = {0};
    /* One-time direct read after successful reset, externally powered
     * conversion request and full conservative conversion wait.
     * A CRC-valid +85C power-on candidate is withheld from readings. */
    s->decode_status = presence ?
        labmate_onewire_ds18b20_decode(bytes, sizeof(bytes), true, &temp) :
        LabMateOneWireDecodeInvalidInput;

    if(!presence) s->status = LabMateOneWireHwNoSensor;
    else if(s->decode_status != LabMateOneWireDecodeOk)
        s->status = LabMateOneWireHwDataError;
    else if(temp.power_on_candidate)
        s->status = LabMateOneWireHwPowerCheck;
    else {
        s->temperature_tenths =
            labmate_onewire_celsius_tenths(temp.celsius_sixteenths);
        s->resolution_bits = temp.resolution_bits;
        s->has_temperature = true;
        s->status = LabMateOneWireHwMeasured;
    }
    labmate_onewire_hw_release(s);
}

void labmate_onewire_hw_stop(LabMateOneWireHw* s) {
    if(!s) return;
    labmate_onewire_hw_release(s);
    if(s->status == LabMateOneWireHwConverting)
        s->status = LabMateOneWireHwStopped;
}
