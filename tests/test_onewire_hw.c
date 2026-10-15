/* Native harness exercises the REAL PA4 hardware-driver source with a
 * deterministic fake OneWireHost. NOT evidence of a connected sensor. */
#include "labmate_onewire_hw.h"
#include <one_wire/one_wire_host.h>
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

struct OneWireHost { bool started; };
const GpioPin gpio_ext_pa4 = {0xA4U};
static struct OneWireHost fake_host;
static uint32_t tick_now;
static uint32_t allocs, starts, stops, frees, resets, reads, writes;
static uint8_t sent[8], scratch[9];
static bool present_start, present_read;
static bool firmware_lease_available=true, firmware_release_succeeds=true;
static bool pin_leased;
static unsigned fw_claims, fw_releases;
uint32_t furi_hal_resource_lease_try_acquire(uint32_t mask) {
    assert(mask == (1U << 11));
    fw_claims++;
    if(!firmware_lease_available) return 0U;
    assert(!pin_leased);
    pin_leased=true;
    return 777U;
}
bool furi_hal_resource_lease_release(uint32_t handle, uint32_t mask) {
    assert(handle==777U && mask==(1U<<11));
    assert(!fake_host.started); /* host STOP before pin-lease release */
    fw_releases++;
    if(!firmware_release_succeeds) return false;
    pin_leased=false;
    return true;
}


uint32_t furi_get_tick(void) { return tick_now; }
uint32_t furi_kernel_get_tick_frequency(void) { return 1000U; }
OneWireHost* onewire_host_alloc(const GpioPin* pin) {
    assert(pin == &gpio_ext_pa4);
#ifndef TEST_NO_LEASE
    assert(pin_leased && "OneWireHost must not allocate before firmware lease");
#endif
    allocs++;
    return &fake_host;
}
void onewire_host_free(OneWireHost* h) {
    assert(h == &fake_host && !fake_host.started);
    frees++;
}
void onewire_host_start(OneWireHost* h) {
    assert(h == &fake_host && !fake_host.started);
    fake_host.started = true;
    starts++;
}
void onewire_host_stop(OneWireHost* h) {
    assert(h == &fake_host && fake_host.started);
    fake_host.started = false;
    stops++;
}
bool onewire_host_reset(OneWireHost* h) {
    assert(h == &fake_host && fake_host.started);
    return (resets++ == 0U) ? present_start : present_read;
}
void onewire_host_write(OneWireHost* h, uint8_t data) {
    assert(h == &fake_host && fake_host.started && writes < 8U);
    sent[writes++] = data;
}
void onewire_host_read_bytes(OneWireHost* h, uint8_t* data, uint16_t count) {
    assert(h == &fake_host && fake_host.started && count == 9U);
    reads++;
    memcpy(data, scratch, 9U);
}

static void fixture(void) {
    assert(!fake_host.started && !pin_leased);
    firmware_lease_available=true;
    firmware_release_succeeds=true;
    fw_claims=fw_releases=0U;
    tick_now=0U;
    allocs=starts=stops=frees=resets=reads=writes=0U;
    present_start=present_read=true;
    memset(sent,0,sizeof(sent));
    /* DS18B20 +25.0625 C / 12-bit supported configuration. */
    const uint8_t raw[8]={0x91U,0x01U,0x4BU,0x46U,0x7FU,0xFFU,0x0CU,0x10U};
    memcpy(scratch,raw,8U);
    scratch[8]=labmate_onewire_crc8(scratch,8U);
}

int main(void) {
    LabMateCommOwner owner=LabMateCommNone;
    LabMateCommBusy clear={0};
    LabMateOneWireHw s;
    labmate_onewire_hw_init(&s);

#ifdef TEST_NO_LEASE
    fixture();
    assert(!labmate_onewire_hw_start(&s,&owner,clear));
    assert(s.status==LabMateOneWireHwBusy && owner==LabMateCommNone);
    assert(allocs==0U && starts==0U && stops==0U && frees==0U);
    assert(fw_claims==0U && fw_releases==0U);
    labmate_onewire_hw_stop(&s);
    assert(allocs==0U && !pin_leased);
    puts("1-Wire old-SDK FAIL-CLOSED PASS: zero host/PA4 writes.");
    return 0;
#else
    fixture();
    firmware_lease_available=false;
    assert(!labmate_onewire_hw_start(&s,&owner,clear));
    assert(s.status==LabMateOneWireHwBusy && owner==LabMateCommNone);
    assert(fw_claims==1U && fw_releases==0U);
    assert(allocs==0U && starts==0U && !pin_leased);

    fixture();
    present_start=false;
    assert(!labmate_onewire_hw_start(&s,&owner,clear));
    assert(s.status==LabMateOneWireHwNoSensor);
    assert(owner==LabMateCommNone && allocs==1 && starts==1 && stops==1 && frees==1);
    assert(reads==0 && writes==0 && !s.has_temperature);

    fixture();
    labmate_onewire_hw_init(&s);
    assert(labmate_onewire_hw_start(&s,&owner,clear));
    assert(s.status==LabMateOneWireHwConverting && owner==LabMateCommOneWirePa4);
    assert(starts==1 && resets==1 && sent[0]==0xCCU && sent[1]==0x44U);
    tick_now=799U;
    labmate_onewire_hw_poll(&s);
    assert(reads==0 && owner==LabMateCommOneWirePa4);
    tick_now=800U;
    labmate_onewire_hw_poll(&s);
    assert(s.status==LabMateOneWireHwMeasured && s.has_temperature);
    assert(s.temperature_tenths==251 && s.resolution_bits==12U);
    assert(reads==1 && sent[2]==0xCCU && sent[3]==0xBEU);
    assert(owner==LabMateCommNone && stops==1 && frees==1);
    labmate_onewire_hw_stop(&s);
    assert(stops==1 && frees==1 && s.status==LabMateOneWireHwMeasured);

    fixture();
    labmate_onewire_hw_init(&s);
    assert(labmate_onewire_hw_start(&s,&owner,clear));
    tick_now=50U;
    labmate_onewire_hw_stop(&s);
    assert(s.status==LabMateOneWireHwStopped && owner==LabMateCommNone);
    tick_now=1000U;
    labmate_onewire_hw_poll(&s);
    assert(!reads && stops==1 && frees==1 && !s.has_temperature);

    fixture();
    labmate_onewire_hw_init(&s);
    LabMateCommBusy busy={.pwm_active=true};
    assert(!labmate_onewire_hw_start(&s,&owner,busy));
    assert(s.status==LabMateOneWireHwBusy && allocs==0 && owner==LabMateCommNone);
    assert(labmate_onewire_hw_start(&s,&owner,clear));
    assert(!labmate_onewire_hw_start(&s,&owner,clear));
    labmate_onewire_hw_stop(&s);
    assert(stops==1 && frees==1);

    fixture();
    labmate_onewire_hw_init(&s);
    assert(labmate_onewire_hw_start(&s,&owner,clear));
    scratch[8]^=0x80U;
    tick_now=900U;
    labmate_onewire_hw_poll(&s);
    assert(s.status==LabMateOneWireHwDataError && !s.has_temperature);
    assert(owner==LabMateCommNone && stops==1 && frees==1);

    fixture();
    labmate_onewire_hw_init(&s);
    assert(labmate_onewire_hw_start(&s,&owner,clear));
    scratch[0]=0x50U;
    scratch[1]=0x05U; /* +85 C power-on candidate: withhold as reading */
    scratch[8]=labmate_onewire_crc8(scratch,8U);
    tick_now=800U;
    labmate_onewire_hw_poll(&s);
    assert(s.status==LabMateOneWireHwPowerCheck && !s.has_temperature);
    assert(owner==LabMateCommNone && stops==1 && frees==1);

    fixture();
    labmate_onewire_hw_init(&s);
    tick_now=UINT32_MAX-99U;
    assert(labmate_onewire_hw_start(&s,&owner,clear));
    tick_now=699U; /* 800 ticks later across 32-bit overflow */
    labmate_onewire_hw_poll(&s);
    assert(s.status==LabMateOneWireHwConverting && !reads);
    tick_now=700U;
    labmate_onewire_hw_poll(&s);
    assert(s.status==LabMateOneWireHwMeasured && s.has_temperature);
    assert(owner==LabMateCommNone && stops==1 && frees==1);

    fixture();
    labmate_onewire_hw_init(&s);
    assert(labmate_onewire_hw_start(&s,&owner,clear));
    firmware_release_succeeds=false;
    labmate_onewire_hw_stop(&s);
    assert(s.firmware_release_fault && s.firmware_lease_handle==777U);
    assert(s.status==LabMateOneWireHwBusy && !s.has_temperature);
    assert(owner==LabMateCommOneWirePa4 && s.owner==&owner);
    assert(!fake_host.started && fw_releases==1U && pin_leased);
    unsigned alloc_before=allocs;
    assert(!labmate_onewire_hw_start(&s,&owner,clear));
    labmate_onewire_hw_stop(&s);
    assert(allocs==alloc_before && fw_releases==1U);

    puts("Direct PA4 OneWireHost driver native START/STOP/CRC/85C/BUSY/wrap PASS (FAKE HAL)");
    puts("PA4 firmware claim rejection, owner retention, failed-release safety PASS.");
    return 0;
#endif
}
