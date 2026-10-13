#pragma once
#include <furi.h>
#include <furi_hal_serial_types.h>
#include <stdbool.h>
#include <stdint.h>
#include "labmate_uart_text.h"

typedef struct Expansion Expansion;

/* UART owns GPIO header 13 TX / 14 RX, USART. No GPIO monitor pin
 * or PA7/TIM1 or PB3/TIM2 ownership is transferred to this module.
 * RX interrupt feeds a bounded stream, never touches Canvas or SD.
 */
#define LABMATE_UART_RX_QUEUE 256U
#define LABMATE_UART_TX_CAP 12U
#define LABMATE_UART_BAUD_COUNT 3U
typedef struct {
    FuriHalSerialHandle* serial;
    FuriStreamBuffer* stream;
    Expansion* expansion;
    bool active;
    bool blocked;
    bool invalid_baud;
    volatile uint32_t dropped;
    volatile uint32_t rx_errors;
    uint32_t rx_total;
    uint32_t tx_total;
    bool tx_sent;
    uint8_t baud_index;
    bool tx_editing;
    char tx_text[LABMATE_UART_TX_CAP + 1U];
    uint8_t tx_cursor;
    LabMateUartText terminal;
} LabMateUart;

void labmate_uart_reset(LabMateUart* uart);
/* Preserve baud across menu re-entry; clears per-session counters/text and stays STOP. */
void labmate_uart_reenter(LabMateUart* uart);
bool labmate_uart_start(LabMateUart* uart);
void labmate_uart_stop(LabMateUart* uart);
void labmate_uart_poll(LabMateUart* uart);
void labmate_uart_next_baud(LabMateUart* uart, int8_t dir);
uint32_t labmate_uart_baud(const LabMateUart* uart);
void labmate_uart_edit_change(LabMateUart* uart, int8_t dir);
void labmate_uart_edit_cursor(LabMateUart* uart, int8_t dir);
bool labmate_uart_send(LabMateUart* uart, const uint8_t* payload, size_t length);
