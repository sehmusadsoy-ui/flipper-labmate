/* Compile actual src/labmate_uart.c with fake HAL/Expansion implementations.
 * This is a HOST contract test, NOT a claim of a real serial-owner conflict
 * or physical overrun on a Flipper. FAP builds never include this file.
 */
#include "labmate_uart.h"
#include <furi_hal_serial.h>
#include <furi_hal_serial_control.h>
#include <expansion/expansion.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>

struct FuriStreamBuffer {
    uint8_t bytes[LABMATE_UART_RX_QUEUE];
    size_t count;
    size_t capacity;
};
struct FuriHalSerialHandle { int marker; };
struct Expansion { int marker; };

static struct FuriStreamBuffer mock_stream;
static struct FuriHalSerialHandle mock_uart_handle;
static struct Expansion mock_expansion;

static bool mock_expansion_connected = false;
static bool mock_uart_foreign_owner = false;
static bool mock_uart_labmate_owner = false;
static bool mock_baud_supported = true;
static bool mock_uart_initialized = false;
static unsigned mock_expansion_disables = 0;
static unsigned mock_expansion_enables = 0;
static unsigned mock_record_opens = 0;
static unsigned mock_record_closes = 0;
static unsigned mock_serial_acquires = 0;
static unsigned mock_serial_releases = 0;
static unsigned mock_stream_allocs = 0;
static unsigned mock_stream_frees = 0;
static unsigned mock_tx_count = 0;
static uint32_t mock_init_baud = 0;
static uint8_t mock_tx_data[32];
static size_t mock_tx_len = 0;

static FuriHalSerialRxCallback mock_rx_callback = NULL;
static void* mock_rx_context = NULL;
static uint8_t mock_wire_bytes[400];
static size_t mock_wire_len = 0;
static size_t mock_wire_read = 0;

FuriStreamBuffer* furi_stream_buffer_alloc(size_t capacity, size_t trigger_level) {
    assert(trigger_level == 1U);
    assert(capacity == LABMATE_UART_RX_QUEUE);
    assert(mock_stream_allocs == mock_stream_frees);
    mock_stream.count = 0U;
    mock_stream.capacity = capacity;
    mock_stream_allocs++;
    return &mock_stream;
}
void furi_stream_buffer_free(FuriStreamBuffer* stream) {
    assert(stream == &mock_stream);
    assert(mock_stream_allocs == mock_stream_frees + 1U);
    mock_stream_frees++;
}
size_t furi_stream_buffer_send(
    FuriStreamBuffer* stream, const void* data, size_t size, uint32_t timeout) {
    assert(stream == &mock_stream);
    assert(timeout == 0U);
    assert(size == 1U);
    if(stream->count == stream->capacity) return 0U;
    stream->bytes[stream->count++] = *(const uint8_t*)data;
    return 1U;
}
size_t furi_stream_buffer_receive(
    FuriStreamBuffer* stream, void* output, size_t size, uint32_t timeout) {
    assert(stream == &mock_stream && timeout == 0U);
    const size_t n = size < stream->count ? size : stream->count;
    memcpy(output, stream->bytes, n);
    memmove(stream->bytes, stream->bytes + n, stream->count - n);
    stream->count -= n;
    return n;
}
void* furi_record_open(const char* name) {
    assert(strcmp(name, RECORD_EXPANSION) == 0);
    mock_record_opens++;
    return &mock_expansion;
}
void furi_record_close(const char* name) {
    assert(strcmp(name, RECORD_EXPANSION) == 0);
    mock_record_closes++;
}
bool expansion_is_connected(Expansion* expansion) {
    assert(expansion == &mock_expansion);
    return mock_expansion_connected;
}
void expansion_disable(Expansion* expansion) {
    assert(expansion == &mock_expansion && !mock_expansion_connected);
    mock_expansion_disables++;
}
void expansion_enable(Expansion* expansion) {
    assert(expansion == &mock_expansion);
    mock_expansion_enables++;
}
FuriHalSerialHandle* furi_hal_serial_control_acquire(FuriHalSerialId serial_id) {
    assert(serial_id == FuriHalSerialIdUsart);
    mock_serial_acquires++;
    if(mock_uart_foreign_owner || mock_uart_labmate_owner) return NULL;
    mock_uart_labmate_owner = true;
    return &mock_uart_handle;
}
void furi_hal_serial_control_release(FuriHalSerialHandle* handle) {
    assert(handle == &mock_uart_handle);
    assert(mock_uart_labmate_owner && !mock_uart_foreign_owner);
    mock_uart_labmate_owner = false;
    mock_serial_releases++;
}
bool furi_hal_serial_is_baud_rate_supported(FuriHalSerialHandle* h, uint32_t baud) {
    assert(h == &mock_uart_handle);
    assert(baud == 9600U || baud == 38400U || baud == 115200U);
    return mock_baud_supported;
}
void furi_hal_serial_init(FuriHalSerialHandle* h, uint32_t baud) {
    assert(h == &mock_uart_handle && mock_uart_labmate_owner);
    mock_uart_initialized = true;
    mock_init_baud = baud;
}
void furi_hal_serial_configure_framing(
    FuriHalSerialHandle* h, FuriHalSerialDataBits data_bits,
    FuriHalSerialParity parity, FuriHalSerialStopBits stop_bits) {
    assert(h == &mock_uart_handle && mock_uart_initialized);
    assert(data_bits == FuriHalSerialDataBits8);
    assert(parity == FuriHalSerialParityNone);
    assert(stop_bits == FuriHalSerialStopBits1);
}
void furi_hal_serial_async_rx_start(
    FuriHalSerialHandle* h, FuriHalSerialRxCallback callback,
    void* context, bool use_dma) {
    assert(h == &mock_uart_handle && mock_uart_initialized);
    assert(use_dma && callback != NULL && context != NULL);
    mock_rx_callback = callback;
    mock_rx_context = context;
}
void furi_hal_serial_async_rx_stop(FuriHalSerialHandle* h) {
    assert(h == &mock_uart_handle);
    assert(mock_rx_callback != NULL);
    mock_rx_callback = NULL;
    mock_rx_context = NULL;
}
size_t furi_hal_serial_async_rx_available(FuriHalSerialHandle* h) {
    assert(h == &mock_uart_handle);
    return mock_wire_len - mock_wire_read;
}
uint8_t furi_hal_serial_async_rx(FuriHalSerialHandle* h) {
    assert(h == &mock_uart_handle && mock_wire_read < mock_wire_len);
    return mock_wire_bytes[mock_wire_read++];
}
void furi_hal_serial_tx(FuriHalSerialHandle* h, const uint8_t* data, size_t n) {
    assert(h == &mock_uart_handle && mock_uart_initialized);
    assert(n <= sizeof(mock_tx_data));
    memcpy(mock_tx_data, data, n);
    mock_tx_len = n;
    mock_tx_count++;
}
void furi_hal_serial_tx_wait_complete(FuriHalSerialHandle* h) {
    assert(h == &mock_uart_handle && mock_uart_initialized);
}
void furi_hal_serial_deinit(FuriHalSerialHandle* h) {
    assert(h == &mock_uart_handle && mock_uart_initialized);
    mock_uart_initialized = false;
}

static void emit_data(const uint8_t* data, size_t n, FuriHalSerialRxEvent event) {
    assert(mock_rx_callback != NULL);
    assert(n <= sizeof(mock_wire_bytes));
    if(n) memcpy(mock_wire_bytes, data, n);
    mock_wire_len = n;
    mock_wire_read = 0U;
    mock_rx_callback(&mock_uart_handle, event, mock_rx_context);
    assert(mock_wire_read == mock_wire_len);
}

int main(void) {
    LabMateUart uart;
    labmate_uart_reset(&uart);
    assert(labmate_uart_baud(&uart) == 115200U);
    assert(!uart.active && !uart.blocked && uart.serial == NULL);

    /* BUSY path 1: connected firmware expansion owns the port.
       App must not disable it or acquire/release a foreign serial handle. */
    mock_expansion_connected = true;
    assert(!labmate_uart_start(&uart));
    assert(uart.blocked && !uart.active && uart.stream == NULL);
    assert(mock_serial_acquires == 0U && mock_serial_releases == 0U);
    assert(mock_expansion_disables == 0U && mock_expansion_enables == 0U);
    mock_expansion_connected = false;

    /* BUSY path 2: another HAL client already owns USART.
       No foreign handle can be deinitialized or released. */
    mock_uart_foreign_owner = true;
    assert(!labmate_uart_start(&uart));
    assert(uart.blocked && uart.serial == NULL && uart.stream == NULL);
    assert(mock_serial_acquires == 1U && mock_serial_releases == 0U);
    assert(mock_expansion_disables == 1U && mock_expansion_enables == 1U);
    assert(mock_uart_foreign_owner);
    mock_uart_foreign_owner = false;

    labmate_uart_next_baud(&uart, 1);
    assert(labmate_uart_baud(&uart) == 9600U);
    assert(labmate_uart_start(&uart));
    assert(uart.active && !uart.blocked);
    assert(mock_init_baud == 9600U && mock_rx_callback != NULL);

    const uint8_t message[] = "ESP32_READY\r\n";
    emit_data(message, sizeof(message) - 1U, FuriHalSerialRxEventData);
    labmate_uart_poll(&uart);
    assert(uart.rx_total == sizeof(message) - 1U);
    assert(strcmp(uart.terminal.rows[0], "ESP32_READY") == 0);
    assert(uart.dropped == 0U && uart.rx_errors == 0U);

    const uint8_t command[] = "AT\r\n";
    assert(labmate_uart_send(&uart, command, sizeof(command) - 1U));
    assert(mock_tx_count == 1U && mock_tx_len == sizeof(command) - 1U);
    assert(memcmp(mock_tx_data, command, mock_tx_len) == 0);

    /* A 320-byte burst used to overflow the 256-byte queue; with
       1024-byte headroom all bytes must be buffered without drops. */
    assert(LABMATE_UART_RX_QUEUE == 1024U);
    uint8_t burst[320U];
    memset(burst, 'X', sizeof(burst));
    emit_data(burst, sizeof(burst), FuriHalSerialRxEventData);
    assert(uart.dropped == 0U && uart.rx_errors == 0U);
    assert(mock_stream.count == sizeof(burst));

    /* Saturation stays truthful: 3x320 + 128 = 1088 bytes without
       polling. Exactly 64 genuine over-capacity bytes must DROP. */
    emit_data(burst, sizeof(burst), FuriHalSerialRxEventData);
    emit_data(burst, sizeof(burst), FuriHalSerialRxEventData);
    assert(mock_stream.count == 960U && uart.dropped == 0U);
    emit_data(burst, 128U, FuriHalSerialRxEventData);
    assert(mock_stream.count == LABMATE_UART_RX_QUEUE);
    assert(uart.dropped == 64U && uart.rx_errors == 0U);
    assert(uart.rx_total == sizeof(message) - 1U); /* poll not run yet */
    labmate_uart_poll(&uart);
    assert(uart.rx_total == sizeof(message) - 1U + LABMATE_UART_RX_QUEUE);
    assert(mock_stream.count == 0U);

    /* Error events must not be counted as byte drops. */
    emit_data(NULL, 0U, FuriHalSerialRxEventFrameError | FuriHalSerialRxEventNoiseError);
    assert(uart.rx_errors == 1U && uart.dropped == 64U);

    labmate_uart_stop(&uart);
    assert(!uart.active && uart.serial == NULL && uart.stream == NULL);
    assert(!mock_uart_initialized && mock_rx_callback == NULL);
    assert(mock_serial_releases == 1U);
    assert(mock_expansion_disables == mock_expansion_enables);
    assert(!labmate_uart_send(&uart, command, sizeof(command) - 1U));
    labmate_uart_stop(&uart); /* double STOP is safe */
    assert(mock_serial_releases == 1U);

    /* Re-entry stays STOP and keeps 9600, clearing latched error/drop. */
    labmate_uart_reenter(&uart);
    assert(labmate_uart_baud(&uart) == 9600U);
    assert(!uart.active && uart.dropped == 0U && uart.rx_errors == 0U);
    assert(uart.rx_total == 0U);
    assert(labmate_uart_start(&uart));
    assert(mock_init_baud == 9600U);
    labmate_uart_stop(&uart);

    /* Same-screen mismatch recovery: STOP + baud change must clear
     * stale errors, old text and RX stats without modifying TX text.
     * An attempt to change baud while RUN must leave state untouched. */
    assert(labmate_uart_start(&uart));
    emit_data(message, sizeof(message) - 1U, FuriHalSerialRxEventData);
    labmate_uart_poll(&uart);
    emit_data(burst, sizeof(burst), FuriHalSerialRxEventData);
    emit_data(burst, sizeof(burst), FuriHalSerialRxEventData);
    emit_data(burst, sizeof(burst), FuriHalSerialRxEventData);
    emit_data(burst, 128U, FuriHalSerialRxEventData);
    emit_data(NULL, 0U, FuriHalSerialRxEventFrameError);
    assert(uart.rx_total == sizeof(message) - 1U);
    assert(uart.dropped == 64U && uart.rx_errors == 1U);
    assert(strcmp(uart.terminal.rows[0], "ESP32_READY") == 0);
    labmate_uart_next_baud(&uart, 1);
    assert(labmate_uart_baud(&uart) == 9600U);
    assert(uart.rx_errors == 1U && uart.dropped == 64U);
    labmate_uart_stop(&uart);
    labmate_uart_next_baud(&uart, 0);
    assert(labmate_uart_baud(&uart) == 9600U);
    assert(uart.rx_errors == 1U && uart.dropped == 64U);
    labmate_uart_next_baud(&uart, 1);
    assert(labmate_uart_baud(&uart) == 38400U);
    assert(uart.rx_total == 0U && uart.dropped == 0U && uart.rx_errors == 0U);
    assert(uart.terminal.cursor_row == 0U && uart.terminal.cursor_col == 0U);
    assert(uart.terminal.rows[0][0] == '\0');
    assert(strcmp(uart.tx_text, "AT") == 0);
    assert(!uart.blocked && !uart.invalid_baud);
    assert(labmate_uart_start(&uart));
    assert(mock_init_baud == 38400U);
    emit_data(message, sizeof(message) - 1U, FuriHalSerialRxEventData);
    labmate_uart_poll(&uart);
    assert(uart.rx_total == sizeof(message) - 1U);
    assert(uart.dropped == 0U && uart.rx_errors == 0U);
    assert(strcmp(uart.terminal.rows[0], "ESP32_READY") == 0);
    labmate_uart_stop(&uart);

    /* Unsupported rate is a separate BAUD status, with clean release. */
    mock_baud_supported = false;
    assert(!labmate_uart_start(&uart));
    assert(uart.invalid_baud && !uart.blocked && !uart.active);
    assert(uart.serial == NULL && uart.stream == NULL);
    mock_baud_supported = true;

    assert(mock_record_opens == mock_record_closes);
    assert(mock_stream_allocs == mock_stream_frees);
    assert(!mock_uart_labmate_owner && !mock_uart_foreign_owner);
    assert(mock_expansion_disables == mock_expansion_enables);
    puts("UART host HAL: ownership BUSY, RX queue DROP, ERR, STOP, re-entry PASS");
    return 0;
}
