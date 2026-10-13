#include "labmate_input_tools.h"
#include "labmate_uart.h"
#include <string.h>

/* No ISR/canvas/SD handling; only state transitions and deferred TX. */
void labmate_input_uart(LabMateApp* app, InputEvent event, LabMateDeferredWork* work) {
    LabMateUart* uart = &app->uart;
    if(uart->tx_editing) {
        if(event.key == InputKeyBack) {
            uart->tx_editing = false;
        } else if(event.key == InputKeyUp) {
            labmate_uart_edit_change(uart, 1);
        } else if(event.key == InputKeyDown) {
            labmate_uart_edit_change(uart, -1);
        } else if(event.key == InputKeyLeft) {
            labmate_uart_edit_cursor(uart, -1);
        } else if(event.key == InputKeyRight) {
            labmate_uart_edit_cursor(uart, 1);
        } else if(event.key == InputKeyOk && uart->active) {
            size_t length = strlen(uart->tx_text);
            if(length > LABMATE_UART_TX_CAP) length = LABMATE_UART_TX_CAP;
            /* TX is explicit, only valid non-empty payloads are queued. */
            while(length && uart->tx_text[length - 1U] == ' ') length--;
            if(length) {
                memcpy(work->uart_tx_payload, uart->tx_text, length);
                work->uart_tx_payload[length] = '\r';
                work->uart_tx_payload[length + 1U] = '\n';
                work->uart_tx_len = (uint8_t)(length + 2U);
                work->uart_tx_requested = true;
                uart->tx_sent = false;
            }
        }
        return;
    }
    if(event.key == InputKeyBack) {
        labmate_uart_stop(uart);
        app->screen = LabMateScreenMenu;
    } else if(event.key == InputKeyOk) {
        if(uart->active) labmate_uart_stop(uart);
        else (void)labmate_uart_start(uart);
    } else if(event.key == InputKeyLeft) {
        labmate_uart_next_baud(uart, -1);
    } else if(event.key == InputKeyRight) {
        labmate_uart_next_baud(uart, 1);
    } else if(event.key == InputKeyUp) {
        labmate_uart_text_reset(&uart->terminal);
    } else if(event.key == InputKeyDown && uart->active) {
        uart->tx_editing = true;
    }
}
