#include "labmate_uart_text.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>

int main(void) {
    LabMateUartText x;
    labmate_uart_text_reset(&x);
    const char* t = "OK\r\nHI\nYES\nNEXT";
    for(size_t i=0; t[i]; ++i) labmate_uart_text_push(&x, (uint8_t)t[i]);
    assert(strcmp(x.rows[0], "HI") == 0);
    assert(strcmp(x.rows[1], "YES") == 0);
    assert(strcmp(x.rows[2], "NEXT") == 0);
    labmate_uart_text_reset(&x);
    for(size_t i=0; i<LABMATE_UART_COLS; ++i) labmate_uart_text_push(&x, 'a');
    labmate_uart_text_push(&x, 'z');
    assert(strlen(x.rows[0]) == LABMATE_UART_COLS);
    assert(strcmp(x.rows[1], "z") == 0);
    labmate_uart_text_push(&x, 0x00);
    assert(strcmp(x.rows[1], "z.") == 0);
    puts("UART text bounded ASCII, newline, scroll and binary PASS");
    return 0;
}
