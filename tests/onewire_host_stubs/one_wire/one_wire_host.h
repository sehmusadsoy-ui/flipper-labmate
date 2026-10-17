#pragma once
#include <stdbool.h>
#include <stdint.h>
typedef struct GpioPin { uint8_t marker; } GpioPin;
typedef struct OneWireHost OneWireHost;
OneWireHost* onewire_host_alloc(const GpioPin* gpio_pin);
void onewire_host_free(OneWireHost* host);
void onewire_host_start(OneWireHost* host);
void onewire_host_stop(OneWireHost* host);
bool onewire_host_reset(OneWireHost* host);
void onewire_host_write(OneWireHost* host, uint8_t data);
void onewire_host_read_bytes(OneWireHost* host, uint8_t* bytes, uint16_t count);
