#pragma once
#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>
#include <furi_hal_serial_types.h>

typedef void (*FuriHalSerialRxCallback)(
    FuriHalSerialHandle* handle, FuriHalSerialRxEvent event, void* context);

bool furi_hal_serial_is_baud_rate_supported(FuriHalSerialHandle* handle, uint32_t baud);
void furi_hal_serial_init(FuriHalSerialHandle* handle, uint32_t baud);
void furi_hal_serial_configure_framing(
    FuriHalSerialHandle* handle, FuriHalSerialDataBits data_bits,
    FuriHalSerialParity parity, FuriHalSerialStopBits stop_bits);
void furi_hal_serial_async_rx_start(
    FuriHalSerialHandle* handle, FuriHalSerialRxCallback callback,
    void* context, bool use_dma);
void furi_hal_serial_async_rx_stop(FuriHalSerialHandle* handle);
size_t furi_hal_serial_async_rx_available(FuriHalSerialHandle* handle);
uint8_t furi_hal_serial_async_rx(FuriHalSerialHandle* handle);
void furi_hal_serial_tx(FuriHalSerialHandle* handle, const uint8_t* data, size_t len);
void furi_hal_serial_tx_wait_complete(FuriHalSerialHandle* handle);
void furi_hal_serial_deinit(FuriHalSerialHandle* handle);
