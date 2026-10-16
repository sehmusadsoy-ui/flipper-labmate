#!/usr/bin/env python3
"""Run the patched production CC1101 free() against actual lease/fault states.

The native void radio free callback must never release a live IRQ/DMA
context after STOP denied or a sticky owner fault. RX stage and later
combined RX/TX stage use the same original production-C function body.
This host regression is NOT a physical radio coexistence test.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile

STUB = r"""
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#define TAG "CC1101"
static int errors, bus_deinits, pin_resets;
#define FURI_LOG_E(...) (++errors)
enum { SpiDefault = 1, SpiExtra = 2, GpioModeAnalog = 3 };
typedef struct { int id; } GpioPin;
static const GpioPin gpio_ext_pc3 = {3};
static const GpioPin gpio_ext_pa4 = {4};
typedef struct {
    bool amp_and_leds;
    void* spi_bus_handle;
} SubGhzDeviceCC1101Ext;
static SubGhzDeviceCC1101Ext* subghz_device_cc1101_ext;
static uint32_t e11_ext_rx_owner, e11_ext_tx_owner;
static bool e11_ext_rx_fault, e11_ext_tx_fault;
static struct { int spi_nrf24_handle; } momentum_settings;
static void furi_hal_spi_bus_handle_deinit(void* handle) {
    assert(handle == (void*)0x10);
    bus_deinits++;
}
static void furi_hal_gpio_init_simple(const GpioPin* pin, int mode) {
    assert((pin == &gpio_ext_pc3 || pin == &gpio_ext_pa4) &&
           mode == GpioModeAnalog);
    pin_resets++;
}
"""

RUN = r"""
static void setup_case(void) {
    subghz_device_cc1101_ext = calloc(1, sizeof(*subghz_device_cc1101_ext));
    assert(subghz_device_cc1101_ext);
    subghz_device_cc1101_ext->spi_bus_handle = (void*)0x10;
    momentum_settings.spi_nrf24_handle = SpiDefault;
    e11_ext_rx_owner = e11_ext_tx_owner = 0;
    e11_ext_rx_fault = e11_ext_tx_fault = false;
    errors = bus_deinits = pin_resets = 0;
}
int main(void) {
    /* FREE is idempotent if the external radio has not been allocated. */
    subghz_device_cc1101_ext_free();
    assert(!bus_deinits && !pin_resets);
    for(int mode = 0; mode < (WITH_TX ? 5 : 3); mode++) {
        setup_case();
        if(mode == 1) e11_ext_rx_owner = 247;
        if(mode == 2) e11_ext_rx_fault = true;
        if(mode == 3) e11_ext_tx_owner = 812;
        if(mode == 4) e11_ext_tx_fault = true;
        SubGhzDeviceCC1101Ext* original = subghz_device_cc1101_ext;
        subghz_device_cc1101_ext_free();
        if(mode) {
            /* Denied free must preserve object and all foreign resources. */
            assert(subghz_device_cc1101_ext == original);
            assert(errors == 1 && !bus_deinits && !pin_resets);
            e11_ext_rx_owner = e11_ext_tx_owner = 0;
            e11_ext_rx_fault = e11_ext_tx_fault = false;
            subghz_device_cc1101_ext_free();
        }
        assert(!subghz_device_cc1101_ext);
        assert(bus_deinits == 1 && pin_resets == 1);
        subghz_device_cc1101_ext_free(); /* duplicate exit no-op */
        assert(bus_deinits == 1 && pin_resets == 1);
    }
    puts("E11 original native CC1101 RX/TX free guard HOST PASS");
    return 0;
}
"""

def main():
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    root = p.parse_args().root.resolve()
    source = (root / "applications/drivers/subghz/cc1101_ext/cc1101_ext.c").read_text()
    start = source.index("void subghz_device_cc1101_ext_free(void) {")
    stop = source.index("void subghz_device_cc1101_ext_set_async_mirror_pin(", start)
    genuine = source[start:stop]
    assert "if(!subghz_device_cc1101_ext) return;" in genuine
    assert "e11_ext_rx_owner || e11_ext_rx_fault" in genuine
    with_tx = "/* E11 native external CC1101 TX TIM17/DMA2 V2 owner. */" in source
    if with_tx:
        assert "e11_ext_tx_owner || e11_ext_tx_fault" in genuine
    with tempfile.TemporaryDirectory(prefix="e11_ext_radio_free_") as temporary:
        d = Path(temporary)
        path = d / "native.c"
        path.write_text(
            STUB + "\n#define WITH_TX " + str(int(with_tx)) + "\n" +
            genuine + "\n" + RUN, encoding="utf-8"
        )
        executable = d / "native"
        subprocess.run(
            ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
             str(path), "-o", str(executable)], check=True
        )
        subprocess.run([str(executable)], check=True)
    print("E11 native external CC1101 exact-object free on BUSY/fault PASS (host).")
    print("Actual RF hardware, unknown third-party plugins remain unverified.")

if __name__ == "__main__":
    main()
