#include "labmate_uart.h"
#include <furi_hal.h>
#include <furi_hal_serial.h>
#include <furi_hal_serial_control.h>
#include <expansion/expansion.h>
#include <string.h>

/* Supported default 8N1 presets; availability checked against SDK HAL. */
static const uint32_t uart_bauds[LABMATE_UART_BAUD_COUNT] = {9600U, 38400U, 115200U};
static const char uart_alphabet[] = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789?=+-_./";

uint32_t labmate_uart_baud(const LabMateUart* uart) {
    return uart_bauds[uart->baud_index % LABMATE_UART_BAUD_COUNT];
}

void labmate_uart_reset(LabMateUart* uart) {
    memset(uart, 0, sizeof(*uart));
    uart->baud_index = 2U; /* 115200, typical MCU debug UART */
    memcpy(uart->tx_text, "AT", 3U);
    labmate_uart_text_reset(&uart->terminal);
}

static void uart_rx_callback(FuriHalSerialHandle* handle, FuriHalSerialRxEvent event, void* ctx) {
    LabMateUart* uart = ctx;
    if(event & FuriHalSerialRxEventData) {
        while(furi_hal_serial_async_rx_available(handle)) {
            uint8_t data = furi_hal_serial_async_rx(handle);
            if(furi_stream_buffer_send(uart->stream, &data, 1U, 0U) != 1U) {
                if(uart->dropped != UINT32_MAX) uart->dropped++;
            }
        }
    }
    if(event & (FuriHalSerialRxEventFrameError | FuriHalSerialRxEventNoiseError |
                FuriHalSerialRxEventOverrunError | FuriHalSerialRxEventParityError)) {
        if(uart->rx_errors != UINT32_MAX) uart->rx_errors++;
    }
}

bool labmate_uart_start(LabMateUart* uart) {
    if(uart->active) return true;
    uart->blocked = false;
    uart->invalid_baud = false;
    uart->stream = furi_stream_buffer_alloc(LABMATE_UART_RX_QUEUE, 1U);
    if(!uart->stream) {
        uart->blocked = true;
        return false;
    }

    uart->expansion = furi_record_open(RECORD_EXPANSION);
    /* Do not disconnect a live expansion module behind the user's back. */
    if(expansion_is_connected(uart->expansion)) {
        uart->blocked = true;
        goto cleanup;
    }
    /* Required by firmware serial control contract; paired with enable. */
    expansion_disable(uart->expansion);
    uart->serial = furi_hal_serial_control_acquire(FuriHalSerialIdUsart);
    if(!uart->serial) {
        uart->blocked = true;
        goto restore_expansion;
    }
    if(!furi_hal_serial_is_baud_rate_supported(uart->serial, labmate_uart_baud(uart))) {
        uart->invalid_baud = true;
        furi_hal_serial_control_release(uart->serial);
        uart->serial = NULL;
        goto restore_expansion;
    }

    furi_hal_serial_init(uart->serial, labmate_uart_baud(uart));
    furi_hal_serial_configure_framing(
        uart->serial, FuriHalSerialDataBits8, FuriHalSerialParityNone, FuriHalSerialStopBits1);
    furi_hal_serial_async_rx_start(uart->serial, uart_rx_callback, uart, true);
    uart->active = true;
    return true;

restore_expansion:
    expansion_enable(uart->expansion);
cleanup:
    furi_record_close(RECORD_EXPANSION);
    uart->expansion = NULL;
    furi_stream_buffer_free(uart->stream);
    uart->stream = NULL;
    return false;
}

void labmate_uart_stop(LabMateUart* uart) {
    if(uart->serial) {
        if(uart->active) {
            furi_hal_serial_async_rx_stop(uart->serial);
            furi_hal_serial_deinit(uart->serial);
        }
        furi_hal_serial_control_release(uart->serial);
        uart->serial = NULL;
    }
    if(uart->expansion) {
        expansion_enable(uart->expansion);
        furi_record_close(RECORD_EXPANSION);
        uart->expansion = NULL;
    }
    if(uart->stream) {
        furi_stream_buffer_free(uart->stream);
        uart->stream = NULL;
    }
    uart->active = false;
}

/* Re-entering the UART screen must not silently reset the selected baud.
 * Reset session RX text/stats, but preserve the peer's matching baud.
 * BACK has already stopped UART; stop again defensively if needed.
 */
void labmate_uart_reenter(LabMateUart* uart) {
    const uint8_t saved_baud_index = uart->baud_index;
    labmate_uart_stop(uart);
    labmate_uart_reset(uart);
    uart->baud_index =
        saved_baud_index < LABMATE_UART_BAUD_COUNT ? saved_baud_index : 2U;
}

void labmate_uart_poll(LabMateUart* uart) {
    if(!uart->active || !uart->stream) return;
    uint8_t batch[64];
    /* Drain up to one full 1024-byte RX queue per app iteration. Keep
     * bounded processing and preserve genuine ISR drop reporting if the
     * peer outruns the UART consumer. UI repaint remains throttled. */
    for(uint8_t round = 0; round < 16U; ++round) {
        size_t n = furi_stream_buffer_receive(uart->stream, batch, sizeof(batch), 0U);
        for(size_t i = 0U; i < n; ++i) {
            labmate_uart_text_push(&uart->terminal, batch[i]);
            if(uart->rx_total != UINT32_MAX) uart->rx_total++;
        }
        if(n < sizeof(batch)) break;
    }
}

void labmate_uart_next_baud(LabMateUart* uart, int8_t dir) {
    if(uart->active || dir == 0) return; /* Never live-reprogram an active RX ISR. */
    if(dir > 0) uart->baud_index = (uart->baud_index + 1U) % LABMATE_UART_BAUD_COUNT;
    else
        uart->baud_index = (uart->baud_index + LABMATE_UART_BAUD_COUNT - 1U) %
                           LABMATE_UART_BAUD_COUNT;

    /* STOP + new baud starts a fresh RX session. Old framing errors
     * must not keep ERR latched after switching to the correct rate.
     * UART RX IRQ is already stopped; preserve edited TX command. */
    uart->rx_total = 0U;
    uart->dropped = 0U;
    uart->rx_errors = 0U;
    uart->blocked = false;
    uart->invalid_baud = false;
    uart->tx_sent = false;
    labmate_uart_text_reset(&uart->terminal);
}

void labmate_uart_edit_cursor(LabMateUart* uart, int8_t dir) {
    if(dir > 0 && uart->tx_cursor + 1U < LABMATE_UART_TX_CAP) {
        uart->tx_cursor++;
        if(uart->tx_text[uart->tx_cursor] == '\0') {
            uart->tx_text[uart->tx_cursor] = 'A';
            uart->tx_text[uart->tx_cursor + 1U] = '\0';
        }
    } else if(dir < 0 && uart->tx_cursor > 0U) {
        uart->tx_cursor--;
    }
}

void labmate_uart_edit_change(LabMateUart* uart, int8_t dir) {
    const size_t n = sizeof(uart_alphabet) - 1U;
    char* ch = &uart->tx_text[uart->tx_cursor];
    size_t index = 0U;
    for(; index < n; ++index) if(uart_alphabet[index] == *ch) break;
    if(index >= n) index = 0U;
    if(dir > 0) index = (index + 1U) % n;
    else if(dir < 0) index = (index + n - 1U) % n;
    *ch = uart_alphabet[index];
}

bool labmate_uart_send(LabMateUart* uart, const uint8_t* payload, size_t length) {
    if(!uart->active || !uart->serial || !payload ||
       length == 0U || length > LABMATE_UART_TX_CAP + 2U) return false;
    furi_hal_serial_tx(uart->serial, payload, length);
    furi_hal_serial_tx_wait_complete(uart->serial);
    return true;
}
