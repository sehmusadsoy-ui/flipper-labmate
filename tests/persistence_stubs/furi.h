#pragma once
#include <stdbool.h>
#include <stdint.h>
#define RECORD_STORAGE "storage"
#define FuriWaitForever UINT32_MAX
void* furi_record_open(const char* name);
void furi_record_close(const char* name);
void furi_mutex_acquire(void* mutex, uint32_t timeout);
void furi_mutex_release(void* mutex);
uint32_t furi_get_tick(void);
uint32_t furi_kernel_get_tick_frequency(void);
