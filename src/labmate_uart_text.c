#include "labmate_uart_text.h"
#include <string.h>

void labmate_uart_text_reset(LabMateUartText* text) {
    memset(text, 0, sizeof(*text));
}

static void labmate_uart_text_newline(LabMateUartText* text) {
    if(text->cursor_row + 1U < LABMATE_UART_ROWS) {
        text->cursor_row++;
    } else {
        memmove(text->rows[0], text->rows[1],
                (LABMATE_UART_ROWS - 1U) * sizeof(text->rows[0]));
        memset(text->rows[LABMATE_UART_ROWS - 1U], 0, sizeof(text->rows[0]));
    }
    text->cursor_col = 0U;
}

void labmate_uart_text_push(LabMateUartText* text, uint8_t byte) {
    if(byte == '\r') return;
    if(byte == '\n') {
        labmate_uart_text_newline(text);
        return;
    }
    if(text->cursor_col >= LABMATE_UART_COLS) labmate_uart_text_newline(text);
    char ch = (byte >= 32U && byte <= 126U) ? (char)byte : '.';
    text->rows[text->cursor_row][text->cursor_col++] = ch;
    text->rows[text->cursor_row][text->cursor_col] = '\0';
}
