#pragma once
#include <stdint.h>
void labmate_mock_critical_enter(void);
void labmate_mock_critical_exit(void);
#define FURI_CRITICAL_ENTER() labmate_mock_critical_enter()
#define FURI_CRITICAL_EXIT() labmate_mock_critical_exit()
