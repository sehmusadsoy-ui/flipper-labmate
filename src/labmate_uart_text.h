#pragma once
#include <stdint.h>
#include <stddef.h>
#define LABMATE_UART_ROWS 3U
#define LABMATE_UART_COLS 19U

/* Pure, bounded terminal display buffer; suitable for host tests. */
typedef struct {
    char rows[LABMATE_UART_ROWS][LABMATE_UART_COLS + 1U];
    uint8_t cursor_row;
    uint8_t cursor_col;
} LabMateUartText;
void labmate_uart_text_reset(LabMateUartText* text);
void labmate_uart_text_push(LabMateUartText* text, uint8_t byte);
