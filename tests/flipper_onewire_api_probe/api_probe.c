/* INERT compile/link proof only. No real GPIO selection, alloc/start,
 * wire reset/read/write, power control or sensor conversion is executed.
 */
#include <one_wire/one_wire_host.h>
#include <one_wire/maxim_crc.h>
#include <furi_hal_gpio.h>
#include <stdint.h>
#include <stdbool.h>

typedef struct {
    OneWireHost* (*alloc)(const GpioPin*);
    void (*free_host)(OneWireHost*);
    void (*start)(OneWireHost*);
    void (*stop)(OneWireHost*);
    bool (*reset)(OneWireHost*);
    void (*write)(OneWireHost*, uint8_t);
    void (*read_bytes)(OneWireHost*, uint8_t*, uint16_t);
    uint8_t (*crc8)(const uint8_t*, uint8_t, uint8_t);
} LabMateOneWireAbi;

static const LabMateOneWireAbi imported = {
    .alloc = onewire_host_alloc,
    .free_host = onewire_host_free,
    .start = onewire_host_start,
    .stop = onewire_host_stop,
    .reset = onewire_host_reset,
    .write = onewire_host_write,
    .read_bytes = onewire_host_read_bytes,
    .crc8 = maxim_crc8,
};
static const LabMateOneWireAbi* volatile abi_witness;

int32_t labmate_onewire_api_probe_app(void* ctx) {
    (void)ctx;
    abi_witness = &imported; /* Force FAP symbol imports/linkage. */
    return 0;               /* No imported function is ever called. */
}
