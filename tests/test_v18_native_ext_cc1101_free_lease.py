#!/usr/bin/env python3
"""Execute original pinned CC1101 alloc/free C, including RX/TX sticky owners.

The legacy void free must not destroy a live IRQ/DMA callback's context.
A fresh allocation must fail closed while retained/faulted, not assert.
Run first after RX patch and again after TX patch in paired workflows.
No hardware/radio PASS is inferred.
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
static int errors, spi_inits, spi_deinits, pin_resets, pin_writes, checks, alloc_calls;
static bool fail_alloc;
#define FURI_LOG_E(...) (++errors)
enum {
    SpiDefault = 1, SpiExtra = 2, GpioModeAnalog = 3,
    GpioModeOutputPushPull = 4,
    SubGhzDeviceCC1101ExtStateInit = 5,
    SubGhzDeviceCC1101ExtRegulationTxRx = 6
};
typedef struct {int id;} GpioPin;
static const GpioPin gpio_ext_pc3 = {3}, gpio_ext_pa4 = {4}, gpio_ext_pb2 = {2};
#define SUBGHZ_DEVICE_CC1101_EXT_TX_GPIO (&gpio_ext_pb2)
#define SUBGHZ_DEVICE_CC1101_EXT_E07_AMP_GPIO (&gpio_ext_pc3)
#define SUBGHZ_DEVICE_CC1101_CONFIG_VER 1
typedef struct {
    int ver;
    bool amp_and_leds, extended_range, bypass_region;
} SubGhzDeviceConf;
typedef struct {
    int state, regulation;
    bool amp_and_leds, extended_range, bypass_region;
    const GpioPin* async_mirror_pin;
    const GpioPin* g0_pin;
    void* spi_bus_handle;
    struct {uint32_t capture_delta_duration;} async_rx;
} SubGhzDeviceCC1101Ext;
static SubGhzDeviceCC1101Ext* subghz_device_cc1101_ext;
static uint32_t e11_ext_rx_owner, e11_ext_tx_owner;
static bool e11_ext_rx_fault, e11_ext_tx_fault;
static struct {int spi_cc1101_handle, spi_nrf24_handle;} momentum_settings;
static int external_bus, extra_bus;
#define furi_hal_spi_bus_handle_external external_bus
#define furi_hal_spi_bus_handle_external_extra extra_bus
static void* test_malloc(size_t bytes) {
    alloc_calls++;
    return fail_alloc ? NULL : calloc(1, bytes);
}
#define malloc test_malloc
static void furi_hal_spi_bus_handle_init(void* handle) {
    assert(handle == &external_bus || handle == &extra_bus);
    spi_inits++;
}
static void furi_hal_spi_bus_handle_deinit(void* handle) {
    assert(handle == &external_bus || handle == &extra_bus);
    spi_deinits++;
}
static void furi_hal_gpio_init_simple(const GpioPin* pin, int mode) {
    assert(pin == &gpio_ext_pc3 || pin == &gpio_ext_pa4);
    assert(mode == GpioModeAnalog || mode == GpioModeOutputPushPull);
    pin_resets++;
}
static void furi_hal_gpio_write(const GpioPin* pin, bool value) {
    (void)value;
    assert(pin == &gpio_ext_pc3 || pin == &gpio_ext_pa4);
    pin_writes++;
}
static bool subghz_device_cc1101_ext_check_init(void) {
    checks++;
    return true;
}
"""

RUN = r"""
static void clear_counts(void) {
    errors=spi_inits=spi_deinits=pin_resets=pin_writes=checks=alloc_calls=0;
}
static void clear_leases(void) {
    e11_ext_rx_owner=e11_ext_tx_owner=0U;
    e11_ext_rx_fault=e11_ext_tx_fault=false;
}
int main(void) {
    momentum_settings.spi_cc1101_handle=SpiDefault;
    momentum_settings.spi_nrf24_handle=SpiDefault;
    clear_counts();
    subghz_device_cc1101_ext_free();
    assert(!spi_deinits && !pin_resets);
    fail_alloc=true;
    assert(!subghz_device_cc1101_ext_alloc(NULL));
    assert(!subghz_device_cc1101_ext && !checks && !spi_inits && !pin_writes);
    fail_alloc=false;
    clear_counts();
    e11_ext_rx_owner=247;
    assert(!subghz_device_cc1101_ext_alloc(NULL));
    assert(!alloc_calls && !spi_inits && !pin_resets);
    clear_leases();
    e11_ext_rx_fault=true;
    assert(!subghz_device_cc1101_ext_alloc(NULL));
    assert(!alloc_calls && !spi_inits && !pin_resets);
    clear_leases();
    if(WITH_TX) {
        e11_ext_tx_owner=812;
        assert(!subghz_device_cc1101_ext_alloc(NULL));
        assert(!alloc_calls && !spi_inits && !pin_resets);
        clear_leases();
        e11_ext_tx_fault=true;
        assert(!subghz_device_cc1101_ext_alloc(NULL));
        assert(!alloc_calls && !spi_inits && !pin_resets);
        clear_leases();
    }
    for(int mode=0; mode<(WITH_TX?5:3); mode++) {
        clear_leases();
        clear_counts();
        assert(subghz_device_cc1101_ext_alloc(NULL));
        assert(spi_inits==1 && checks==1 && alloc_calls==1);
        SubGhzDeviceCC1101Ext* previous=subghz_device_cc1101_ext;
        assert(!subghz_device_cc1101_ext_alloc(NULL)); /* no double alloc */
        assert(subghz_device_cc1101_ext==previous && alloc_calls==1);
        if(mode==1) e11_ext_rx_owner=247;
        if(mode==2) e11_ext_rx_fault=true;
        if(mode==3) e11_ext_tx_owner=812;
        if(mode==4) e11_ext_tx_fault=true;
        subghz_device_cc1101_ext_free();
        if(mode) {
            assert(subghz_device_cc1101_ext==previous);
            assert(errors==1 && !spi_deinits && !pin_resets);
            assert(!subghz_device_cc1101_ext_alloc(NULL));
            assert(alloc_calls==1 && spi_inits==1);
            clear_leases(); /* harness-only forced state; NEVER production recovery */
            subghz_device_cc1101_ext_free();
        }
        assert(!subghz_device_cc1101_ext);
        assert(spi_deinits==1 && pin_resets==1);
        subghz_device_cc1101_ext_free(); /* idempotent */
        assert(spi_deinits==1 && pin_resets==1);
    }
    puts("E11 original CC1101 alloc/free, RX/TX sticky lifecycle HOST PASS");
    return 0;
}
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    root = parser.parse_args().root.resolve()
    src = (root / "applications/drivers/subghz/cc1101_ext/cc1101_ext.c").read_text()
    begin = src.index("bool subghz_device_cc1101_ext_alloc(SubGhzDeviceConf* conf) {")
    end = src.index("void subghz_device_cc1101_ext_set_async_mirror_pin(", begin)
    genuine = src[begin:end]
    assert "if(subghz_device_cc1101_ext || e11_ext_rx_owner || e11_ext_rx_fault" in genuine
    assert "if(!subghz_device_cc1101_ext) return false;" in genuine
    assert "if(!subghz_device_cc1101_ext) return;" in genuine
    with_tx = "/* E11 native external CC1101 TX TIM17/DMA2 V2 owner. */" in src
    if with_tx:
        assert "e11_ext_tx_owner || e11_ext_tx_fault" in genuine
    with tempfile.TemporaryDirectory(prefix="e11_cc1101_lifecycle_") as tmp:
        directory = Path(tmp)
        native = directory / "native.c"
        native.write_text(
            STUB + "\n#define WITH_TX " + str(int(with_tx)) + "\n" +
            genuine + "\n" + RUN,
            encoding="utf-8"
        )
        exe = directory / "native"
        subprocess.run(
            ["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
             str(native), "-o", str(exe)], check=True
        )
        subprocess.run([str(exe)], check=True)
    print("Pinned original-C CC1101 alloc/free host gate PASS; hardware remains pending.")

if __name__ == "__main__":
    main()
